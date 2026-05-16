"""Tests for hybrid-retrieval fusion and the per-paper diversity cap."""

from chat_structured_ollama import (
    MAX_CHUNKS_PER_PAPER,
    RRF_K,
    TOP_K_FINAL,
    fuse_results,
    retrieval_key,
    select_final_results,
)


class FakeDoc:
    """Minimal stand-in for a LangChain Document for retrieval-logic tests."""

    def __init__(self, paper_id, section_id, content, section_title="Section"):
        self.metadata = {
            "paper_id": paper_id,
            "section_id": section_id,
            "section_title": section_title,
        }
        self.page_content = content


def test_fuse_results_ranks_documents_found_by_both_retrievers_first():
    in_both = FakeDoc("p1", "s1", "alpha")
    dense_only = FakeDoc("p2", "s2", "beta")
    bm25_only = FakeDoc("p3", "s3", "gamma")

    dense_results = [(in_both, 0.1), (dense_only, 0.2)]
    bm25_docs = [in_both, bm25_only]

    fused = fuse_results(dense_results, bm25_docs)

    assert retrieval_key(fused[0]["doc"]) == retrieval_key(in_both)
    assert len(fused) == 3


def test_fuse_results_uses_reciprocal_rank_fusion_score():
    doc = FakeDoc("p1", "s1", "x")
    fused = fuse_results([(doc, 0.5)], [])
    # Rank 1 in dense results only -> 1 / (RRF_K + 1)
    assert abs(fused[0]["fused_score"] - 1.0 / (RRF_K + 1)) < 1e-9


def test_select_final_results_caps_chunks_per_paper():
    items = [{"doc": FakeDoc("p1", f"s{i}", f"c{i}")} for i in range(5)]
    selected = select_final_results(items)
    assert len(selected) == MAX_CHUNKS_PER_PAPER


def test_select_final_results_deduplicates_identical_chunks():
    doc = FakeDoc("p1", "s1", "same content")
    selected = select_final_results([{"doc": doc}, {"doc": doc}])
    assert len(selected) == 1


def test_select_final_results_respects_top_k_final():
    items = [{"doc": FakeDoc(f"p{i}", "s1", f"c{i}")} for i in range(TOP_K_FINAL + 4)]
    selected = select_final_results(items)
    assert len(selected) == TOP_K_FINAL
