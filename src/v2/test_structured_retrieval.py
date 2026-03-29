from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from langchain_community.vectorstores import FAISS

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings


BASE_DIR = Path(__file__).resolve().parent.parent.parent
INDEX_DIR = BASE_DIR / "storage" / "faiss_index_v2_structured"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

TOP_K_FETCH = 16
TOP_K_FINAL = 6
MAX_CHUNKS_PER_PAPER = 2

DEFAULT_QUERY = "what is the diameter of spiral ganglion neurons?"


def create_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def token_set(text: str) -> set[str]:
    return set(tokenize(text))


def retrieval_key(doc) -> tuple:
    meta = doc.metadata
    return (
        meta.get("paper_id"),
        meta.get("section_id"),
        meta.get("section_title"),
        clean_text(doc.page_content[:250]),
    )


def query_focus_terms(query: str) -> set[str]:
    terms = token_set(query)

    extra = set()
    if "diameter" in terms or "diameters" in terms:
        extra.update({"diameter", "diameters", "morphometry", "process", "type", "cell", "cells"})
    if "spiral" in terms or "ganglion" in terms:
        extra.update({"spiral", "ganglion", "sgn", "neuron", "neurons"})
    if "hcn" in terms:
        extra.update({"hcn", "channel", "channels", "regulation", "conductance"})

    return terms | extra


def rerank_score(query: str, doc, base_score: float) -> float:
    """
    Higher is better.
    FAISS similarity_search_with_score often returns lower score = better distance,
    so we convert it to a negative base and add heuristic boosts.
    """
    meta = doc.metadata
    section_title = clean_text(meta.get("section_title", ""))
    section_type = (meta.get("section_type", "") or "").lower()
    title = clean_text(meta.get("title", ""))
    text = clean_text(doc.page_content[:1200])

    q_terms = query_focus_terms(query)
    title_terms = token_set(title)
    section_terms = token_set(section_title)
    text_terms = token_set(text)

    score = -float(base_score)

    # overlap boosts
    score += 0.35 * len(q_terms & text_terms)
    score += 0.70 * len(q_terms & section_terms)
    score += 0.20 * len(q_terms & title_terms)

    # targeted section-type boosts
    if section_type == "results":
        score += 1.2
    elif section_type == "methods":
        score += 0.8
    elif section_type == "section":
        score += 0.6
    elif section_type == "introduction":
        score += 0.15
    elif section_type == "abstract":
        score -= 0.1
    elif section_type == "body_opening":
        score -= 0.35

    # special query-aware boosts
    query_lower = query.lower()
    combined = f"{section_title} {text}".lower()

    if "diameter" in query_lower:
        if "diameter" in combined or "diameters" in combined:
            score += 2.2
        if "type i process diameters" in combined:
            score += 3.0
        if "morphometry" in combined:
            score += 0.8

    if "hcn" in query_lower:
        if "hcn" in combined:
            score += 2.0
        if "channel" in combined or "channels" in combined:
            score += 0.8

    if "extracellular stimulation" in query_lower or "stimulation" in query_lower:
        if "extracellular stimulation" in combined:
            score += 2.0
        if section_type == "methods":
            score += 0.8

    # mild penalty for overly generic untitled chunks
    if section_title.lower().startswith("untitled section"):
        score -= 0.2

    return score


def retrieve_documents(db, query: str):
    raw_results = db.similarity_search_with_score(query, k=TOP_K_FETCH)

    reranked = []
    for doc, base_score in raw_results:
        score = rerank_score(query, doc, base_score)
        reranked.append((doc, base_score, score))

    reranked.sort(key=lambda x: x[2], reverse=True)

    filtered = []
    seen = set()
    per_paper_counts = Counter()

    for doc, base_score, final_score in reranked:
        key = retrieval_key(doc)
        if key in seen:
            continue
        seen.add(key)

        paper_id = doc.metadata.get("paper_id", "unknown")
        if per_paper_counts[paper_id] >= MAX_CHUNKS_PER_PAPER:
            continue

        per_paper_counts[paper_id] += 1
        filtered.append((doc, base_score, final_score))

        if len(filtered) >= TOP_K_FINAL:
            break

    return raw_results, reranked, filtered


def print_result(i: int, doc, base_score: float, final_score: float):
    meta = doc.metadata

    print("\n" + "=" * 110)
    print(
        f"RESULT {i} | "
        f"{meta.get('paper_id', '')} | "
        f"{meta.get('year', '')} | "
        f"{meta.get('category', '')}"
    )
    print(
        f"title: {meta.get('title', '')}\n"
        f"section_title: {meta.get('section_title', '')}\n"
        f"section_type: {meta.get('section_type', '')}\n"
        f"unit_type: {meta.get('unit_type', '')}\n"
        f"chunk_id: {meta.get('chunk_id', '')}\n"
        f"base_score: {base_score:.4f}\n"
        f"rerank_score: {final_score:.4f}"
    )

    keywords = meta.get("keywords", "")
    if keywords:
        print(f"keywords: {keywords}")

    print("\n" + clean_text(doc.page_content)[:1200])


if __name__ == "__main__":
    db = FAISS.load_local(
        str(INDEX_DIR),
        create_embeddings(),
        allow_dangerous_deserialization=True,
    )

    query = input(f"Query [{DEFAULT_QUERY}]: ").strip() or DEFAULT_QUERY

    raw_results, reranked, filtered = retrieve_documents(db, query)

    print(f"\nQuery: {query}")
    print(f"Raw retrieved: {len(raw_results)}")
    print(f"Reranked candidates: {len(reranked)}")
    print(f"After dedup/diversity filtering: {len(filtered)}")

    unique_papers = {doc.metadata.get("paper_id") for doc, _, _ in filtered}
    unique_sections = {
        (doc.metadata.get("paper_id"), doc.metadata.get("section_id"))
        for doc, _, _ in filtered
    }

    print(f"Unique papers in final results: {len(unique_papers)}")
    print(f"Unique sections in final results: {len(unique_sections)}")

    for i, (doc, base_score, final_score) in enumerate(filtered, start=1):
        print_result(i, doc, base_score, final_score)

    paper_counts = Counter(doc.metadata.get("paper_id") for doc, _, _ in filtered)
    print("\nPaper distribution in final results:")
    for paper_id, count in paper_counts.items():
        print(f"- {paper_id}: {count}")