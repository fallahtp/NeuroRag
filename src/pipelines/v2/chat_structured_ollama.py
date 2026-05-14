from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
import re

import ollama
from langchain_community.retrievers import BM25Retriever

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

# Make the v2 package directory, the v3 directory and src/ importable
# regardless of the current working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v3"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/
from load_structured_documents import load_structured_documents
from build_structured_index import split_documents
from rerank import rerank_documents
from vector_store import load_dense_index
from observability import traced
from config import settings


INDEX_DIR = settings.v2_index_dir

EMBEDDING_MODEL = settings.embedding_model
OLLAMA_MODEL = settings.v2_ollama_model

TOP_K_FETCH = settings.top_k_fetch
TOP_K_FINAL = settings.top_k_final
MAX_CHUNKS_PER_PAPER = settings.max_chunks_per_paper
RRF_K = settings.rrf_k
RERANK_POOL_SIZE = settings.rerank_pool_size

SUPPORTED_PIPELINES = ("v2_hybrid", "v3_reranked")

MAX_SNIPPET_CHARS = 1200
MAX_EVIDENCE_SENTENCES_PER_CHUNK = 3
MIN_SENTENCE_LEN = 25

SYSTEM_INSTRUCTION = """You are NeuroRag v2, a neuroscience and NEURON/Python research assistant.

Rules:
- Answer using ONLY the retrieved context.
- Do NOT invent facts, values, sections, titles, authors, page numbers, DOI, journals, or bibliography entries.
- Do NOT generate a reference list or bibliography.
- Cite sources ONLY with bracket IDs already provided in the context, such as [1], [2].
- For measurement or value questions, copy exact values/ranges only if they are explicitly present in the retrieved evidence.
- If the retrieved context is insufficient, say exactly:
"I do not have enough evidence in the retrieved context to answer confidently."

Your output MUST follow this exact structure:

Answer:
<your answer>

Evidence summary:
<1-3 short sentences grounded in the retrieved context>

Source IDs:
[1], [2]

If only one source is used, output for example:
Source IDs:
[3]

Do not output anything other than these three sections.
"""


def create_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9_+-]{3,}", text.lower()))


def retrieval_key(doc) -> tuple:
    meta = doc.metadata
    return (
        meta.get("paper_id"),
        meta.get("section_id"),
        meta.get("section_title"),
        clean_text(doc.page_content[:250]),
    )


def strip_prefixed_metadata(text: str) -> str:
    lines = text.splitlines()
    cleaned = []
    skipping_prefix = True

    for line in lines:
        stripped = line.strip()
        if skipping_prefix and (
            stripped.startswith("Title:")
            or stripped.startswith("Year:")
            or stripped.startswith("Section title:")
            or stripped.startswith("Section type:")
            or stripped.startswith("Keywords:")
        ):
            continue

        if skipping_prefix and stripped == "":
            continue

        skipping_prefix = False
        cleaned.append(line)

    return clean_text("\n".join(cleaned))


def split_into_sentences(text: str) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    sentences = [clean_text(p) for p in parts if clean_text(p)]
    return sentences


def query_wants_numeric_evidence(query: str) -> bool:
    q = query.lower()
    triggers = [
        "diameter",
        "diameters",
        "size",
        "sizes",
        "length",
        "width",
        "height",
        "thickness",
        "value",
        "values",
        "mean",
        "average",
        "range",
        "how much",
        "how many",
        "what is the diameter",
        "what are the diameters",
        "what is the value",
        "measure",
        "measurement",
        "measurements",
    ]
    return any(t in q for t in triggers)


def sentence_score(sentence: str, query: str, section_title: str = "") -> float:
    s_terms = tokenize(sentence)
    q_terms = tokenize(query)
    title_terms = tokenize(section_title)

    score = 0.0
    score += 1.0 * len(q_terms & s_terms)
    score += 0.5 * len(q_terms & title_terms)

    q_lower = query.lower()
    s_lower = sentence.lower()
    title_lower = section_title.lower()

    if query_wants_numeric_evidence(query):
        if re.search(r"\b\d+([.,]\d+)?\b", sentence):
            score += 2.0
        if any(unit in s_lower for unit in ["µm", "um", "mm", "nm", "ms", "hz", "%"]):
            score += 1.0
        if any(word in s_lower for word in ["diameter", "mean", "average", "range", "length", "value"]):
            score += 1.0

    if "diameter" in q_lower and "diameter" in s_lower:
        score += 2.0
    if "hcn" in q_lower and "hcn" in s_lower:
        score += 2.0
    if "regulat" in q_lower and any(w in s_lower for w in ["regulat", "modulat", "control", "cAMP", "cyclic nucleotide"]):
        score += 1.5
    if "stimulation" in q_lower and "stimulation" in s_lower:
        score += 1.5

    if "diameter" in title_lower or "diameters" in title_lower:
        score += 1.0
    if "results" in title_lower:
        score += 0.3

    return score


def select_evidence_sentences(question: str, doc, max_sentences: int = MAX_EVIDENCE_SENTENCES_PER_CHUNK) -> str:
    section_title = doc.metadata.get("section_title", "")
    raw_text = strip_prefixed_metadata(doc.page_content)
    sentences = split_into_sentences(raw_text)

    candidates = []
    for idx, sentence in enumerate(sentences):
        if len(sentence) < MIN_SENTENCE_LEN:
            continue
        score = sentence_score(sentence, question, section_title)
        candidates.append((idx, score, sentence))

    if not candidates:
        return raw_text[:MAX_SNIPPET_CHARS]

    # Keep only useful sentences
    candidates = [c for c in candidates if c[1] > 0]
    if not candidates:
        return raw_text[:MAX_SNIPPET_CHARS]

    # Pick best scoring, then restore original order for readability
    candidates.sort(key=lambda x: x[1], reverse=True)
    top = candidates[:max_sentences]
    top.sort(key=lambda x: x[0])

    selected = " ".join(sentence for _, _, sentence in top)
    selected = clean_text(selected)

    return selected[:MAX_SNIPPET_CHARS] if selected else raw_text[:MAX_SNIPPET_CHARS]


def load_dense_db():
    return load_dense_index(create_embeddings(), INDEX_DIR)


def build_bm25_retriever():
    docs = load_structured_documents()
    chunks = split_documents(docs)
    retriever = BM25Retriever.from_documents(chunks)
    retriever.k = TOP_K_FETCH
    return retriever


def dense_search(db, query: str):
    return db.similarity_search_with_score(query, k=TOP_K_FETCH)


def bm25_search(retriever, query: str):
    docs = retriever.invoke(query)
    return docs[:TOP_K_FETCH]


def fuse_results(dense_results, bm25_docs):
    score_map: dict[tuple, float] = {}
    doc_map: dict[tuple, object] = {}
    dense_rank_map: dict[tuple, int] = {}
    dense_score_map: dict[tuple, float] = {}
    bm25_rank_map: dict[tuple, int] = {}

    for rank, (doc, dense_score) in enumerate(dense_results, start=1):
        key = retrieval_key(doc)
        doc_map[key] = doc
        dense_rank_map[key] = rank
        dense_score_map[key] = dense_score
        score_map[key] = score_map.get(key, 0.0) + 1.0 / (RRF_K + rank)

    for rank, doc in enumerate(bm25_docs, start=1):
        key = retrieval_key(doc)
        doc_map[key] = doc
        bm25_rank_map[key] = rank
        score_map[key] = score_map.get(key, 0.0) + 1.0 / (RRF_K + rank)

    fused = []
    for key, fused_score in score_map.items():
        fused.append(
            {
                "doc": doc_map[key],
                "fused_score": fused_score,
                "dense_rank": dense_rank_map.get(key),
                "dense_score": dense_score_map.get(key),
                "bm25_rank": bm25_rank_map.get(key),
            }
        )

    fused.sort(key=lambda x: x["fused_score"], reverse=True)
    return fused


def select_final_results(fused_results):
    filtered = []
    seen = set()
    per_paper_counts = Counter()

    for item in fused_results:
        doc = item["doc"]
        key = retrieval_key(doc)

        if key in seen:
            continue
        seen.add(key)

        paper_id = doc.metadata.get("paper_id", "unknown")
        if per_paper_counts[paper_id] >= MAX_CHUNKS_PER_PAPER:
            continue

        per_paper_counts[paper_id] += 1
        filtered.append(item)

        if len(filtered) >= TOP_K_FINAL:
            break

    return filtered


def build_retrieval_note(question: str, final_results) -> str:
    if not final_results:
        return "No context was retrieved."

    q_terms = tokenize(question)
    best_overlap = 0

    for item in final_results:
        doc = item["doc"]
        section_title = doc.metadata.get("section_title", "")
        body = select_evidence_sentences(question, doc, max_sentences=2)
        text_terms = tokenize(section_title + " " + body[:600])
        overlap = len(q_terms & text_terms)
        best_overlap = max(best_overlap, overlap)

    if best_overlap <= 1:
        return (
            "Retrieved evidence appears weak or only loosely related to the question. "
            "If the context does not support the answer, say that there is not enough evidence."
        )

    return "Retrieved evidence appears usable. Stay grounded in the provided context only."


def build_context(question: str, final_results) -> str:
    blocks = []

    for i, item in enumerate(final_results, start=1):
        doc = item["doc"]
        meta = doc.metadata

        title = meta.get("title", "")
        year = meta.get("year", "")
        category = meta.get("category", "")
        section_title = meta.get("section_title", "")
        section_type = meta.get("section_type", "")
        chunk_id = meta.get("chunk_id", "")

        tag = (
            f"[{i}] "
            f"{title or meta.get('paper_id', 'unknown')} "
            f"({year}) | {category} | "
            f"{section_title} | {section_type} | chunk {chunk_id}"
        )

        evidence = select_evidence_sentences(question, doc)
        blocks.append(f"{tag}\n{evidence}")

    return "\n\n".join(blocks)


def build_prompt(question: str, context: str, retrieval_note: str) -> str:
    return (
        f"{SYSTEM_INSTRUCTION}\n\n"
        f"Question:\n{question}\n\n"
        f"Retrieval note:\n{retrieval_note}\n\n"
        f"Context:\n{context}\n"
    )


@traced
def ask_ollama(prompt: str) -> str:
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]


def extract_valid_source_ids(text: str, max_id: int) -> list[int]:
    found = re.findall(r"\[(\d+)\]", text)
    ids = []
    seen = set()

    for s in found:
        n = int(s)
        if 1 <= n <= max_id and n not in seen:
            seen.add(n)
            ids.append(n)

    return ids


def normalize_answer_output(answer: str, max_source_id: int) -> str:
    text = answer.strip()

    text = re.sub(
        r"(?is)\n\s*(sources?|references?|bibliography|citations?)\s*:.*$",
        "",
        text,
    ).strip()

    valid_ids = extract_valid_source_ids(text, max_source_id)

    answer_match = re.search(
        r"(?is)answer\s*:\s*(.*?)(?:\n\s*evidence summary\s*:|\Z)",
        text,
    )
    evidence_match = re.search(
        r"(?is)evidence summary\s*:\s*(.*?)(?:\n\s*source ids\s*:|\Z)",
        text,
    )

    answer_text = answer_match.group(1).strip() if answer_match else text
    evidence_text = evidence_match.group(1).strip() if evidence_match else ""

    answer_text = re.sub(r"(?m)^\s*(source ids?|sources?)\s*:.*$", "", answer_text).strip()
    evidence_text = re.sub(r"(?m)^\s*(source ids?|sources?)\s*:.*$", "", evidence_text).strip()

    if not evidence_text:
        evidence_text = "Grounded in the retrieved context only."

    if valid_ids:
        source_line = ", ".join(f"[{n}]" for n in valid_ids)
    else:
        source_line = "none"

    return (
        f"Answer:\n{answer_text}\n\n"
        f"Evidence summary:\n{evidence_text}\n\n"
        f"Source IDs:\n{source_line}"
    )


def print_sources(final_results):
    print("\nSOURCES METADATA:")
    for i, item in enumerate(final_results, start=1):
        doc = item["doc"]
        meta = doc.metadata
        print(
            f"[{i}] "
            f"{meta.get('paper_id', '')} | "
            f"{meta.get('year', '')} | "
            f"{meta.get('section_title', '')} | "
            f"{meta.get('section_type', '')} | "
            f"chunk={meta.get('chunk_id', '')} | "
            f"dense_rank={item.get('dense_rank')} | "
            f"bm25_rank={item.get('bm25_rank')} | "
            f"fused_score={item.get('fused_score'):.6f}"
        )


@traced
def run_query(question, dense_db, bm25_retriever, pipeline: str = "v2_hybrid") -> dict:
    """Run the structured retrieval + generation pipeline for one question.

    Pipelines:
        v2_hybrid:   dense + BM25 -> RRF fusion -> per-paper diversity cap
        v3_reranked: as above, but the top ``RERANK_POOL_SIZE`` fused
                     candidates are rescored by the cross-encoder before
                     the diversity cap is applied.

    Returns a dict with the normalized ``answer``, the ``final_results``
    retrieved chunks, the ``context`` block, the ``prompt`` and the
    ``raw_answer`` model output. ``final_results`` is empty when nothing
    was retrieved.
    """
    if pipeline not in SUPPORTED_PIPELINES:
        raise ValueError(
            f"Unknown pipeline: {pipeline!r}. Expected one of {SUPPORTED_PIPELINES}."
        )

    dense_results = dense_search(dense_db, question)
    bm25_docs = bm25_search(bm25_retriever, question)
    fused = fuse_results(dense_results, bm25_docs)

    if pipeline == "v3_reranked":
        pool = fused[:RERANK_POOL_SIZE]
        candidate_docs = [item["doc"] for item in pool]
        reranked_pairs = rerank_documents(question, candidate_docs, top_k=len(candidate_docs))
        ranked_items = [{"doc": doc, "rerank_score": score} for doc, score in reranked_pairs]
        final_results = select_final_results(ranked_items)
    else:  # v2_hybrid
        final_results = select_final_results(fused)

    if not final_results:
        return {
            "pipeline": pipeline,
            "final_results": [],
            "context": "",
            "prompt": "",
            "raw_answer": "",
            "answer": "",
        }

    context = build_context(question, final_results)
    retrieval_note = build_retrieval_note(question, final_results)
    prompt = build_prompt(question, context, retrieval_note)
    raw_answer = ask_ollama(prompt)
    answer = normalize_answer_output(raw_answer, len(final_results))

    return {
        "pipeline": pipeline,
        "final_results": final_results,
        "context": context,
        "prompt": prompt,
        "raw_answer": raw_answer,
        "answer": answer,
    }


if __name__ == "__main__":
    dense_db = load_dense_db()
    bm25_retriever = build_bm25_retriever()

    while True:
        question = input("\nAsk: ").strip()
        if not question or question.lower() in {"exit", "quit"}:
            break

        result = run_query(question, dense_db, bm25_retriever, pipeline="v2_hybrid")

        if not result["final_results"]:
            print("\nNo documents were retrieved from the index.")
            continue

        print("\n" + result["answer"])
        print_sources(result["final_results"])