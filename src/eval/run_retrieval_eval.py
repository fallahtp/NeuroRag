from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings


BASE_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = BASE_DIR / "src"
V2_DIR = SRC_DIR / "v2"

for path in (SRC_DIR, V2_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from load_structured_documents import load_structured_documents  # noqa: E402
from build_structured_index import split_documents  # noqa: E402


BENCHMARK_PATH = BASE_DIR / "benchmarks" / "retrieval_eval_questions.jsonl"
RESULTS_DIR = BASE_DIR / "results"

V1_INDEX_DIR = BASE_DIR / "storage" / "faiss_index"
V2_INDEX_DIR = BASE_DIR / "storage" / "faiss_index_v2_structured"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

DEFAULT_TOP_K = 5
DEFAULT_FETCH_K = 12
RRF_K = 60
MAX_CHUNKS_PER_PAPER = 2


@dataclass
class EvalQuestion:
    id: str
    question: str
    expected_paper_ids: list[str]
    expected_section_keywords: list[str] = field(default_factory=list)
    notes: str = ""

    def has_section_expectation(self) -> bool:
        return bool(self.expected_section_keywords)


def normalize_space(text: str) -> str:
    text = text.replace("\x00", " ")
    return re.sub(r"\s+", " ", text).strip()


def create_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def retrieval_key(doc) -> tuple:
    meta = doc.metadata
    return (
        meta.get("paper_id", ""),
        meta.get("section_id", ""),
        meta.get("section_title", ""),
        normalize_space(doc.page_content[:250]),
    )


def dedup_docs(docs: list) -> list:
    seen = set()
    unique_docs = []

    for doc in docs:
        key = retrieval_key(doc)
        if key in seen:
            continue
        seen.add(key)
        unique_docs.append(doc)

    return unique_docs


def doc_to_row(rank: int, doc) -> dict:
    meta = doc.metadata

    return {
        "rank": rank,
        "paper_id": meta.get("paper_id", ""),
        "title": meta.get("title", meta.get("filename", "")),
        "year": str(meta.get("year", "")),
        "category": meta.get("category", ""),
        "section_id": meta.get("section_id", ""),
        "section_title": meta.get("section_title", ""),
        "section_type": meta.get("section_type", ""),
        "preview": normalize_space(doc.page_content)[:280],
    }


def load_questions(path: Path) -> list[EvalQuestion]:
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")

    questions: list[EvalQuestion] = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue

            data = json.loads(line)

            question = EvalQuestion(
                id=data["id"],
                question=data["question"],
                expected_paper_ids=data["expected_paper_ids"],
                expected_section_keywords=data.get("expected_section_keywords", []),
                notes=data.get("notes", ""),
            )

            if not question.expected_paper_ids:
                raise ValueError(f"{path}:{line_no} has no expected_paper_ids")

            questions.append(question)

    if not questions:
        raise ValueError(f"No benchmark questions found in: {path}")

    return questions


def load_faiss_db(index_dir: Path):
    if not index_dir.exists():
        return None

    return FAISS.load_local(
        str(index_dir),
        create_embeddings(),
        allow_dangerous_deserialization=True,
    )


def build_v2_bm25_retriever():
    docs = load_structured_documents()
    chunks = split_documents(docs)
    retriever = BM25Retriever.from_documents(chunks)
    retriever.k = DEFAULT_FETCH_K
    return retriever


def v1_dense_retrieve(db, query: str, top_k: int, fetch_k: int) -> list[dict]:
    docs = db.similarity_search(query, k=max(top_k, fetch_k))
    docs = dedup_docs(docs)[:top_k]
    return [doc_to_row(i, doc) for i, doc in enumerate(docs, start=1)]


def v2_dense_retrieve(db, query: str, top_k: int, fetch_k: int) -> list[dict]:
    docs = db.similarity_search(query, k=max(top_k, fetch_k))
    docs = dedup_docs(docs)[:top_k]
    return [doc_to_row(i, doc) for i, doc in enumerate(docs, start=1)]


def fuse_rrf(dense_docs: list, bm25_docs: list) -> list:
    score_map: dict[tuple, float] = {}
    doc_map: dict[tuple, object] = {}

    for rank, doc in enumerate(dense_docs, start=1):
        key = retrieval_key(doc)
        doc_map[key] = doc
        score_map[key] = score_map.get(key, 0.0) + 1.0 / (RRF_K + rank)

    for rank, doc in enumerate(bm25_docs, start=1):
        key = retrieval_key(doc)
        doc_map[key] = doc
        score_map[key] = score_map.get(key, 0.0) + 1.0 / (RRF_K + rank)

    fused = [(doc_map[key], score) for key, score in score_map.items()]
    fused.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in fused]


def select_diverse_docs(docs: list, top_k: int) -> list:
    selected = []
    seen = set()
    per_paper_counts: dict[str, int] = {}

    for doc in docs:
        key = retrieval_key(doc)
        if key in seen:
            continue
        seen.add(key)

        paper_id = doc.metadata.get("paper_id", "unknown")
        count = per_paper_counts.get(paper_id, 0)
        if count >= MAX_CHUNKS_PER_PAPER:
            continue

        per_paper_counts[paper_id] = count + 1
        selected.append(doc)

        if len(selected) >= top_k:
            break

    return selected


def v2_hybrid_retrieve(dense_db, bm25_retriever, query: str, top_k: int, fetch_k: int) -> list[dict]:
    dense_docs = dense_db.similarity_search(query, k=max(top_k, fetch_k))
    bm25_docs = bm25_retriever.invoke(query)[: max(top_k, fetch_k)]

    fused_docs = fuse_rrf(dense_docs, bm25_docs)
    final_docs = select_diverse_docs(fused_docs, top_k)

    return [doc_to_row(i, doc) for i, doc in enumerate(final_docs, start=1)]


def paper_match(row: dict, question: EvalQuestion) -> bool:
    expected = {pid.lower() for pid in question.expected_paper_ids}
    return row["paper_id"].lower() in expected


def section_match(row: dict, question: EvalQuestion) -> bool:
    if not question.has_section_expectation():
        return False

    if not paper_match(row, question):
        return False

    searchable = f"{row.get('section_title', '')} {row.get('preview', '')}".lower()
    return any(keyword.lower() in searchable for keyword in question.expected_section_keywords)


def first_matching_rank(rows: list[dict], matcher: Callable[[dict], bool]) -> int | None:
    for row in rows:
        if matcher(row):
            return row["rank"]
    return None


def reciprocal_rank(rank: int | None) -> float:
    return 0.0 if rank is None else 1.0 / rank


def evaluate_pipeline(name: str, retrieve_fn: Callable[[str, int, int], list[dict]], questions: list[EvalQuestion], top_k: int, fetch_k: int) -> tuple[dict, list[dict]]:
    per_question = []

    for question in questions:
        rows = retrieve_fn(question.question, top_k, fetch_k)

        paper_rank = first_matching_rank(rows, lambda row: paper_match(row, question))
        section_rank = first_matching_rank(rows, lambda row: section_match(row, question))

        per_question.append(
            {
                "id": question.id,
                "question": question.question,
                "expected_paper_ids": question.expected_paper_ids,
                "expected_section_keywords": question.expected_section_keywords,
                "paper_rank": paper_rank,
                "section_rank": section_rank,
                "top_results": rows,
            }
        )

    total = len(per_question)
    section_subset = [item for item in per_question if item["expected_section_keywords"]]

    summary = {
        "pipeline": name,
        "questions": total,
        "paper_hit_at_1": sum(1 for item in per_question if item["paper_rank"] is not None and item["paper_rank"] <= 1) / total,
        "paper_hit_at_3": sum(1 for item in per_question if item["paper_rank"] is not None and item["paper_rank"] <= 3) / total,
        "paper_hit_at_5": sum(1 for item in per_question if item["paper_rank"] is not None and item["paper_rank"] <= 5) / total,
        "paper_mrr": sum(reciprocal_rank(item["paper_rank"]) for item in per_question) / total,
        "section_questions": len(section_subset),
        "section_hit_at_3": None,
        "section_hit_at_5": None,
    }

    if section_subset:
        summary["section_hit_at_3"] = sum(
            1 for item in section_subset if item["section_rank"] is not None and item["section_rank"] <= 3
        ) / len(section_subset)
        summary["section_hit_at_5"] = sum(
            1 for item in section_subset if item["section_rank"] is not None and item["section_rank"] <= 5
        ) / len(section_subset)

    return summary, per_question


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def score(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}"


def print_summary(summary_by_pipeline: dict[str, dict]) -> None:
    print("\nSummary")
    print("-" * 92)
    print(
        f"{'pipeline':<12} {'q':>3} {'hit@1':>8} {'hit@3':>8} {'hit@5':>8} "
        f"{'mrr':>8} {'sec@3':>8} {'sec@5':>8}"
    )

    for pipeline_name, summary in summary_by_pipeline.items():
        print(
            f"{pipeline_name:<12} "
            f"{summary['questions']:>3} "
            f"{pct(summary['paper_hit_at_1']):>8} "
            f"{pct(summary['paper_hit_at_3']):>8} "
            f"{pct(summary['paper_hit_at_5']):>8} "
            f"{score(summary['paper_mrr']):>8} "
            f"{pct(summary['section_hit_at_3']):>8} "
            f"{pct(summary['section_hit_at_5']):>8}"
        )


def build_markdown_report(benchmark_path: Path, summary_by_pipeline: dict[str, dict], per_query_by_pipeline: dict[str, list[dict]]) -> str:
    pipelines = list(summary_by_pipeline.keys())
    lines = [
        "# NeuroRag Retrieval Evaluation",
        "",
        f"Benchmark file: `{benchmark_path.as_posix()}`",
        "",
        "## Summary",
        "",
        "| Pipeline | Questions | Paper Hit@1 | Paper Hit@3 | Paper Hit@5 | Paper MRR | Section Questions | Section Hit@3 | Section Hit@5 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for pipeline_name in pipelines:
        summary = summary_by_pipeline[pipeline_name]
        lines.append(
            f"| {pipeline_name} | {summary['questions']} | {pct(summary['paper_hit_at_1'])} | "
            f"{pct(summary['paper_hit_at_3'])} | {pct(summary['paper_hit_at_5'])} | "
            f"{score(summary['paper_mrr'])} | {summary['section_questions']} | "
            f"{pct(summary['section_hit_at_3'])} | {pct(summary['section_hit_at_5'])} |"
        )

    lines.extend(
        [
            "",
            "## Per-Question Paper Match Rank",
            "",
            "| Question ID | Question | " + " | ".join(pipelines) + " |",
            "|---|---|" + "|".join("---:" for _ in pipelines) + "|",
        ]
    )

    first_pipeline_items = per_query_by_pipeline[pipelines[0]]
    per_pipeline_maps = {
        pipeline: {item["id"]: item for item in items}
        for pipeline, items in per_query_by_pipeline.items()
    }

    for item in first_pipeline_items:
        qid = item["id"]
        question_text = item["question"].replace("|", "\\|")
        ranks = []
        for pipeline in pipelines:
            rank = per_pipeline_maps[pipeline][qid]["paper_rank"]
            ranks.append(str(rank) if rank is not None else "miss")
        lines.append(f"| {qid} | {question_text} | " + " | ".join(ranks) + " |")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=str, default=str(BENCHMARK_PATH))
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--fetch-k", type=int, default=DEFAULT_FETCH_K)
    args = parser.parse_args()

    benchmark_path = Path(args.benchmark)
    questions = load_questions(benchmark_path)

    summary_by_pipeline: dict[str, dict] = {}
    per_query_by_pipeline: dict[str, list[dict]] = {}

    v1_db = load_faiss_db(V1_INDEX_DIR)
    v2_db = load_faiss_db(V2_INDEX_DIR)

    if v1_db is None:
        print(f"[WARN] Skipping v1_dense because index is missing: {V1_INDEX_DIR}")
    else:
        summary, per_query = evaluate_pipeline(
            "v1_dense",
            lambda query, top_k, fetch_k: v1_dense_retrieve(v1_db, query, top_k, fetch_k),
            questions,
            args.top_k,
            args.fetch_k,
        )
        summary_by_pipeline["v1_dense"] = summary
        per_query_by_pipeline["v1_dense"] = per_query

    if v2_db is None:
        print(f"[WARN] Skipping v2_dense and v2_hybrid because index is missing: {V2_INDEX_DIR}")
    else:
        summary, per_query = evaluate_pipeline(
            "v2_dense",
            lambda query, top_k, fetch_k: v2_dense_retrieve(v2_db, query, top_k, fetch_k),
            questions,
            args.top_k,
            args.fetch_k,
        )
        summary_by_pipeline["v2_dense"] = summary
        per_query_by_pipeline["v2_dense"] = per_query

        try:
            bm25_retriever = build_v2_bm25_retriever()
        except Exception as exc:
            print(f"[WARN] Skipping v2_hybrid because BM25 setup failed: {exc}")
        else:
            summary, per_query = evaluate_pipeline(
                "v2_hybrid",
                lambda query, top_k, fetch_k: v2_hybrid_retrieve(v2_db, bm25_retriever, query, top_k, fetch_k),
                questions,
                args.top_k,
                args.fetch_k,
            )
            summary_by_pipeline["v2_hybrid"] = summary
            per_query_by_pipeline["v2_hybrid"] = per_query

    if not summary_by_pipeline:
        raise RuntimeError("No pipelines were evaluated. Build at least one index first.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    json_path = RESULTS_DIR / "retrieval_eval_summary.json"
    md_path = RESULTS_DIR / "retrieval_eval_summary.md"

    payload = {
        "benchmark_path": str(benchmark_path),
        "summary_by_pipeline": summary_by_pipeline,
        "per_query_by_pipeline": per_query_by_pipeline,
    }

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(
        build_markdown_report(benchmark_path, summary_by_pipeline, per_query_by_pipeline),
        encoding="utf-8",
    )

    print_summary(summary_by_pipeline)
    print(f"\nSaved JSON summary: {json_path}")
    print(f"Saved Markdown report: {md_path}")


if __name__ == "__main__":
    main()
