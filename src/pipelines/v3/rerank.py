from __future__ import annotations

from typing import Iterable

from langchain_core.documents import Document


RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Truncate very long sections before scoring. Cross-encoders have a 512-token
# limit; passing longer text triggers warnings and silently truncates anyway.
MAX_DOC_CHARS_FOR_RERANK = 2000

_reranker_singleton = None


def get_reranker(model_name: str = RERANKER_MODEL):
    """
    Lazy singleton loader for the cross-encoder.

    The model is ~80 MB and takes a couple of seconds to load. Loading it
    once and reusing the instance across queries keeps eval runs fast.
    """
    global _reranker_singleton

    if _reranker_singleton is None:
        # Imported here so projects that never call rerank don't pay the
        # sentence-transformers import cost.
        from sentence_transformers import CrossEncoder

        _reranker_singleton = CrossEncoder(model_name)

    return _reranker_singleton


def _doc_text_for_rerank(doc: Document) -> str:
    """
    Use the same text the dense retriever sees (page_content as stored in
    the FAISS index, including the metadata prefix added by
    enrich_document_text). Truncated to keep the cross-encoder happy.
    """
    text = doc.page_content or ""
    if len(text) > MAX_DOC_CHARS_FOR_RERANK:
        text = text[:MAX_DOC_CHARS_FOR_RERANK]
    return text


def score_documents(query: str, docs: Iterable[Document]) -> list[float]:
    """
    Return cross-encoder relevance scores for each (query, doc) pair, in
    the same order as the input docs. Higher score = more relevant.
    """
    docs = list(docs)
    if not docs:
        return []

    reranker = get_reranker()
    pairs = [(query, _doc_text_for_rerank(doc)) for doc in docs]
    scores = reranker.predict(pairs)

    # CrossEncoder.predict returns a numpy array; cast to plain floats so
    # downstream code (sorting, JSON serialization) doesn't need to know.
    return [float(s) for s in scores]


def rerank_documents(
    query: str,
    docs: Iterable[Document],
    top_k: int,
) -> list[tuple[Document, float]]:
    """
    Score (query, doc) pairs with the cross-encoder and return the top_k
    documents sorted by descending relevance.

    Each returned item is (doc, score) so callers can inspect or surface
    the rerank score alongside other ranking signals.
    """
    docs = list(docs)
    if not docs:
        return []

    scores = score_documents(query, docs)
    scored = list(zip(docs, scores))
    scored.sort(key=lambda item: item[1], reverse=True)

    return scored[:top_k]
