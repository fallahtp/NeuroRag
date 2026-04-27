from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

from load_structured_documents import load_structured_documents
from build_structured_index import split_documents

BASE_DIR = Path(__file__).resolve().parents[3]
INDEX_DIR = BASE_DIR / "storage" / "faiss_index_v2_structured"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

TOP_K_FETCH = 12
TOP_K_FINAL = 6
MAX_CHUNKS_PER_PAPER = 2

# RRF constant; common practical default
RRF_K = 60

DEFAULT_QUERY = "what is the diameter of spiral ganglion neurons?"


def create_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def retrieval_key(doc) -> tuple:
    meta = doc.metadata
    return (
        meta.get("paper_id"),
        meta.get("section_id"),
        meta.get("section_title"),
        clean_text(doc.page_content[:250]),
    )


def load_dense_db():
    return FAISS.load_local(
        str(INDEX_DIR),
        create_embeddings(),
        allow_dangerous_deserialization=True,
    )


def build_bm25_retriever():
    docs = load_structured_documents()
    chunks = split_documents(docs)
    retriever = BM25Retriever.from_documents(chunks)
    retriever.k = TOP_K_FETCH
    return retriever


def dense_search(db, query: str):
    results = db.similarity_search_with_score(query, k=TOP_K_FETCH)
    # lower FAISS score is usually better distance
    return [(doc, score) for doc, score in results]


def bm25_search(retriever, query: str):
    docs = retriever.invoke(query)
    return docs[:TOP_K_FETCH]


def fuse_results(dense_results, bm25_docs):
    """
    Reciprocal Rank Fusion (RRF):
    score(doc) = sum(1 / (k + rank_i))
    """
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


def print_result(i: int, item: dict):
    doc = item["doc"]
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
        f"dense_rank: {item.get('dense_rank')}\n"
        f"dense_score: {item.get('dense_score')}\n"
        f"bm25_rank: {item.get('bm25_rank')}\n"
        f"fused_score: {item.get('fused_score'):.6f}"
    )

    keywords = meta.get("keywords", "")
    if keywords:
        print(f"keywords: {keywords}")

    print("\n" + clean_text(doc.page_content)[:1200])


if __name__ == "__main__":
    dense_db = load_dense_db()
    bm25_retriever = build_bm25_retriever()

    query = input(f"Query [{DEFAULT_QUERY}]: ").strip() or DEFAULT_QUERY

    dense_results = dense_search(dense_db, query)
    bm25_docs = bm25_search(bm25_retriever, query)
    fused_results = fuse_results(dense_results, bm25_docs)
    final_results = select_final_results(fused_results)

    print(f"\nQuery: {query}")
    print(f"Dense candidates: {len(dense_results)}")
    print(f"BM25 candidates: {len(bm25_docs)}")
    print(f"Fused candidates: {len(fused_results)}")
    print(f"After dedup/diversity filtering: {len(final_results)}")

    unique_papers = {item['doc'].metadata.get('paper_id') for item in final_results}
    unique_sections = {
        (
            item["doc"].metadata.get("paper_id"),
            item["doc"].metadata.get("section_id"),
        )
        for item in final_results
    }

    print(f"Unique papers in final results: {len(unique_papers)}")
    print(f"Unique sections in final results: {len(unique_sections)}")

    for i, item in enumerate(final_results, start=1):
        print_result(i, item)

    paper_counts = Counter(item["doc"].metadata.get("paper_id") for item in final_results)
    print("\nPaper distribution in final results:")
    for paper_id, count in paper_counts.items():
        print(f"- {paper_id}: {count}")