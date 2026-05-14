"""
NeuroRag answer-quality evaluation harness.

For each benchmark question, this script:
  1. Runs a retrieval + generation pipeline end-to-end. Two pipelines
     are supported:
       - v2_hybrid    (default): FAISS dense + BM25 lexical, RRF fusion
       - v3_reranked: v2_hybrid candidates rescored by a cross-encoder
                      before per-paper diversity capping
  2. Scores the generated answer on four axes:
       - fact recall      (did the answer use the key facts?)
       - citation validity (are cited [n] IDs in range?)
       - citation grounding (do cited chunks actually contain the facts?)
       - numeric hallucination (did the model fabricate numbers not in context?)
  3. Writes a per-question JSON detail file and a markdown summary.
     The output filename is auto-generated from model + pipeline + N
     so reruns don't clobber each other.

Run from the project root:
    python src/eval/run_answer_eval.py
    python src/eval/run_answer_eval.py --pipeline v3_reranked
    python src/eval/run_answer_eval.py --model phi3:mini
    python src/eval/run_answer_eval.py --benchmark benchmarks/answer_eval_questions.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------
# Project paths and import bootstrap (mirrors run_retrieval_eval.py)
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = BASE_DIR / "src"
V2_DIR = SRC_DIR / "pipelines" / "v2"
V3_DIR = SRC_DIR / "pipelines" / "v3"

for path in (SRC_DIR, V2_DIR, V3_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

# These imports come from your existing v2 pipeline. We are *reusing*
# the production retrieval + generation pipeline so the eval measures
# the real system, not a reimplementation of it.
import ollama  # noqa: E402
from langchain_community.retrievers import BM25Retriever  # noqa: E402
from langchain_community.vectorstores import FAISS  # noqa: E402

try:
    from langchain_huggingface import HuggingFaceEmbeddings  # noqa: E402
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings  # noqa: E402

from load_structured_documents import load_structured_documents  # noqa: E402
from build_structured_index import split_documents  # noqa: E402

# v3 pipeline: cross-encoder reranker. Imported here so it's loaded once
# (with its lazy-singleton CrossEncoder) when this module is imported.
from rerank import rerank_documents  # noqa: E402

# We import everything we need from the chat pipeline, so we evaluate
# the *exact* production prompt and evidence selection.
from chat_structured_ollama import (  # noqa: E402
    INDEX_DIR,
    EMBEDDING_MODEL,
    OLLAMA_MODEL,
    TOP_K_FETCH,
    bm25_search,
    build_context,
    build_prompt,
    build_retrieval_note,
    dense_search,
    fuse_results,
    normalize_answer_output,
    select_final_results,
)


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

BENCHMARK_PATH = BASE_DIR / "benchmarks" / "answer_eval_questions.jsonl"
RESULTS_DIR = BASE_DIR / "results"

# Supported retrieval pipelines. Default mirrors what the answer eval has
# always done; v3_reranked adds a cross-encoder on top.
SUPPORTED_PIPELINES = ("v2_hybrid", "v3_reranked")
DEFAULT_PIPELINE = "v2_hybrid"

# Number of fused candidates fed to the cross-encoder. Matches
# run_retrieval_eval.py so the v3 retrieval behaviour is identical
# across the two harnesses.
RERANK_POOL_SIZE = 16

# A number is "hallucinated" only if it carries a unit and doesn't
# appear in the retrieved context. Units we care about for neuroscience.
NUMERIC_UNITS = [
    "µm", "um", "nm", "mm", "cm",
    "ms", "s", "hz", "khz",
    "mv", "pa", "na",
    "%", "°c",
]

# Numbers below this threshold (without units) are too common to flag —
# things like "1", "2", "3" appear in any text. A bare number flags only
# when the answer claims it as a measurement.
MIN_HALLUCINATION_NUM_LEN = 3  # require at least 3 chars: "1.5", "10", "100"


@dataclass
class EvalQuestion:
    id: str
    question: str
    expected_paper_ids: list[str]
    expected_section_keywords: list[str] = field(default_factory=list)
    expected_facts: list[str] = field(default_factory=list)
    notes: str = ""


# ---------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------

def normalize_for_match(text: str) -> str:
    """
    Lowercase, collapse whitespace, normalize unicode dashes and the
    µm vs um distinction. We deliberately do NOT strip punctuation,
    because '1.32' and '132' must stay distinct.
    """
    text = text.lower()
    text = text.replace("µ", "u")     # µm -> um
    text = text.replace("–", "-")     # en dash
    text = text.replace("—", "-")     # em dash
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_numbers_with_units(text: str) -> list[str]:
    """
    Find numeric values that look like measurements: a number followed
    (within a few characters) by a known unit. Returns the matched
    substrings, normalized.

    Why this matters: in scientific QA, the dangerous hallucinations are
    fabricated *numbers* — e.g. claiming the diameter is "1.5 µm" when
    the paper says 1.32 µm. Plain prose hallucinations are easier for a
    domain expert to catch by eye. Number+unit fabrications are not.
    """
    text = normalize_for_match(text)

    units_alt = "|".join(re.escape(u) for u in NUMERIC_UNITS)
    # Pattern: a decimal number, optional whitespace/dash, then a unit.
    # The (?:\s*-\s*\d+(?:\.\d+)?)? lets us also match ranges like "1-4 ms".
    pattern = re.compile(
        rf"(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)\s*({units_alt})\b"
    )

    matches = []
    for num, unit in pattern.findall(text):
        matches.append(f"{num.strip()} {unit}".strip())
    return matches


# ---------------------------------------------------------------------
# Benchmark loading
# ---------------------------------------------------------------------

def load_questions(path: Path) -> list[EvalQuestion]:
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")

    questions: list[EvalQuestion] = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc

            questions.append(EvalQuestion(
                id=data["id"],
                question=data["question"],
                expected_paper_ids=data.get("expected_paper_ids", []),
                expected_section_keywords=data.get("expected_section_keywords", []),
                expected_facts=data.get("expected_facts", []),
                notes=data.get("notes", ""),
            ))

    return questions


# ---------------------------------------------------------------------
# Retriever + generator setup (reuses v2 production code)
# ---------------------------------------------------------------------

def create_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


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


def run_pipeline(
    question: str,
    dense_db,
    bm25_retriever,
    model_name: str,
    pipeline: str = DEFAULT_PIPELINE,
) -> dict:
    """
    Runs the full retrieval + generation pipeline for one question and
    returns everything we need for scoring: the final answer, the
    retrieved chunks, the prompt, and the raw model output.

    Pipelines:
        v2_hybrid:    fuse_results -> select_final_results
        v3_reranked:  fuse_results -> rerank_documents -> select_final_results

    For v3_reranked, the cross-encoder sees the top RERANK_POOL_SIZE fused
    candidates *before* per-paper diversity capping. This way the
    reranker can reorder duplicate chunks from the same paper, and the
    diversity cap then picks the best K from the reranked order.
    """
    if pipeline not in SUPPORTED_PIPELINES:
        raise ValueError(
            f"Unknown pipeline: {pipeline!r}. "
            f"Expected one of {SUPPORTED_PIPELINES}."
        )

    dense_results = dense_search(dense_db, question)
    bm25_docs = bm25_search(bm25_retriever, question)
    fused = fuse_results(dense_results, bm25_docs)

    if pipeline == "v3_reranked":
        # Take the top fused candidates and rescore them with the
        # cross-encoder. We pass top_k=len(pool) to get the full pool
        # back in rerank order; select_final_results then handles the
        # per-paper diversity cap.
        pool = fused[:RERANK_POOL_SIZE]
        candidate_docs = [item["doc"] for item in pool]
        reranked_pairs = rerank_documents(
            question, candidate_docs, top_k=len(candidate_docs)
        )
        # Re-wrap into the dict shape select_final_results expects.
        # Preserving rerank_score lets us surface it in the per-question
        # JSON for transparency/debugging.
        ranked_items = [
            {"doc": doc, "rerank_score": score}
            for doc, score in reranked_pairs
        ]
        final_results = select_final_results(ranked_items)
    else:  # v2_hybrid
        final_results = select_final_results(fused)

    if not final_results:
        return {
            "final_results": [],
            "context": "",
            "prompt": "",
            "raw_answer": "",
            "answer": "",
        }

    context = build_context(question, final_results)
    note = build_retrieval_note(question, final_results)
    prompt = build_prompt(question, context, note)

    response = ollama.chat(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_answer = response["message"]["content"]
    answer = normalize_answer_output(raw_answer, len(final_results))

    return {
        "final_results": final_results,
        "context": context,
        "prompt": prompt,
        "raw_answer": raw_answer,
        "answer": answer,
    }


# ---------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------

def score_fact_recall(answer: str, expected_facts: list[str]) -> dict:
    """
    What fraction of expected facts appear (as substrings, after
    normalization) in the answer? Returns the score and a per-fact
    breakdown so we can diagnose failures.
    """
    if not expected_facts:
        return {"score": None, "matched": [], "missed": [], "total": 0}

    norm_answer = normalize_for_match(answer)
    matched, missed = [], []

    for fact in expected_facts:
        if normalize_for_match(fact) in norm_answer:
            matched.append(fact)
        else:
            missed.append(fact)

    return {
        "score": len(matched) / len(expected_facts),
        "matched": matched,
        "missed": missed,
        "total": len(expected_facts),
    }


def extract_cited_ids(answer: str) -> list[int]:
    """Pull all [n] tokens out of the answer."""
    return [int(m) for m in re.findall(r"\[(\d+)\]", answer)]


def score_citation_validity(answer: str, num_sources: int) -> dict:
    """
    Are the cited [n] IDs actually in range? If the model writes [7]
    when only 6 sources were retrieved, that's a hallucinated citation.
    """
    cited = extract_cited_ids(answer)

    if not cited:
        return {"score": 0.0, "cited": [], "valid": [], "invalid": [], "any_cited": False}

    valid = [n for n in cited if 1 <= n <= num_sources]
    invalid = [n for n in cited if not (1 <= n <= num_sources)]

    return {
        "score": len(valid) / len(cited),
        "cited": cited,
        "valid": valid,
        "invalid": invalid,
        "any_cited": True,
    }


def score_citation_grounding(
    answer: str,
    final_results: list,
    expected_facts: list[str],
) -> dict:
    """
    For each cited [n], does the corresponding retrieved chunk actually
    contain at least one of the expected facts? This catches the case
    where the model grabs a citation number but the chunk it points to
    has nothing to do with the claim.

    Notes:
      - We only check this when there are expected_facts to anchor on.
      - We require *one* fact match per cited chunk; this is a soft
        signal, not a strict per-claim grounding test.
    """
    if not expected_facts:
        return {"score": None, "checked": 0, "grounded": 0}

    cited = [n for n in extract_cited_ids(answer) if 1 <= n <= len(final_results)]
    if not cited:
        return {"score": 0.0, "checked": 0, "grounded": 0}

    norm_facts = [normalize_for_match(f) for f in expected_facts]
    grounded = 0

    for n in set(cited):
        item = final_results[n - 1]
        chunk_text = normalize_for_match(item["doc"].page_content)
        if any(f in chunk_text for f in norm_facts):
            grounded += 1

    return {
        "score": grounded / len(set(cited)),
        "checked": len(set(cited)),
        "grounded": grounded,
    }


def score_numeric_hallucination(answer: str, context: str) -> dict:
    """
    Does the answer contain number+unit values that don't appear
    anywhere in the retrieved context? This is the most important
    safety check for scientific QA.

    Returns the *count* of suspicious values and the values themselves.
    A score of 0 means no hallucinated numbers found (good).
    """
    answer_nums = extract_numbers_with_units(answer)
    context_norm = normalize_for_match(context)

    suspicious = []
    for value in answer_nums:
        # The value is "1.32 um" style. Check both the raw normalized
        # form and a relaxed form without internal whitespace.
        if value in context_norm:
            continue
        relaxed = re.sub(r"\s+", "", value)
        if relaxed in re.sub(r"\s+", "", context_norm):
            continue
        suspicious.append(value)

    return {
        "found_in_answer": answer_nums,
        "suspicious": suspicious,
        "count": len(suspicious),
        # Convenience boolean for aggregating later
        "clean": len(suspicious) == 0,
    }


def score_question(item: EvalQuestion, run_result: dict) -> dict:
    answer = run_result["answer"]
    context = run_result["context"]
    final_results = run_result["final_results"]

    fact_recall = score_fact_recall(answer, item.expected_facts)
    cite_valid = score_citation_validity(answer, len(final_results))
    cite_ground = score_citation_grounding(answer, final_results, item.expected_facts)
    halluc = score_numeric_hallucination(answer, context)

    # Persist the actual retrieved chunks (truncated) so downstream
    # graders — including an LLM judge for grounding — can score this
    # run without re-doing retrieval. Each item is a dict because v2 and
    # v3 produce dict-shaped final_results with different score keys
    # (fused_score for v2_hybrid, rerank_score for v3_reranked).
    retrieved_chunks = []
    for i, r in enumerate(final_results, start=1):
        doc = r["doc"]
        meta = doc.metadata
        retrieved_chunks.append({
            "rank": i,
            "paper_id": meta.get("paper_id", ""),
            "section_title": meta.get("section_title", ""),
            "section_type": meta.get("section_type", ""),
            "preview": doc.page_content[:1000],
            "fused_score": r.get("fused_score"),
            "rerank_score": r.get("rerank_score"),
        })

    return {
        "id": item.id,
        "question": item.question,
        "answer": answer,
        "expected_facts": item.expected_facts,
        "num_retrieved": len(final_results),
        "retrieved_paper_ids": [
            r["doc"].metadata.get("paper_id", "") for r in final_results
        ],
        "retrieved_chunks": retrieved_chunks,
        "fact_recall": fact_recall,
        "citation_validity": cite_valid,
        "citation_grounding": cite_ground,
        "numeric_hallucination": halluc,
    }


# ---------------------------------------------------------------------
# Aggregation + reporting
# ---------------------------------------------------------------------

def mean(values: list[float]) -> float:
    valid = [v for v in values if v is not None]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


def aggregate(results: list[dict], model_name: str, pipeline: str) -> dict:
    n = len(results)
    if n == 0:
        return {"model": model_name, "pipeline": pipeline, "questions": 0}

    fact_recall_scores = [r["fact_recall"]["score"] for r in results]
    cite_valid_scores = [r["citation_validity"]["score"] for r in results]
    cite_ground_scores = [r["citation_grounding"]["score"] for r in results]
    answers_with_citations = sum(
        1 for r in results if r["citation_validity"]["any_cited"]
    )
    clean_answers = sum(1 for r in results if r["numeric_hallucination"]["clean"])
    suspicious_total = sum(
        r["numeric_hallucination"]["count"] for r in results
    )

    return {
        "model": model_name,
        "pipeline": pipeline,
        "questions": n,
        "mean_fact_recall": mean(fact_recall_scores),
        "mean_citation_validity": mean(cite_valid_scores),
        "mean_citation_grounding": mean(cite_ground_scores),
        "answers_with_citations": answers_with_citations,
        "answers_with_citations_pct": answers_with_citations / n,
        "answers_without_numeric_hallucination": clean_answers,
        "answers_without_numeric_hallucination_pct": clean_answers / n,
        "total_suspicious_numbers": suspicious_total,
    }


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def build_markdown_report(
    benchmark_path: Path,
    summary: dict,
    per_question: list[dict],
) -> str:
    lines = [
        "# NeuroRag Answer Evaluation",
        "",
        f"Benchmark file: `{benchmark_path.as_posix()}`",
        f"Model: `{summary['model']}`",
        f"Pipeline: `{summary.get('pipeline', 'unknown')}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Questions | {summary['questions']} |",
        f"| Mean fact recall | {pct(summary['mean_fact_recall'])} |",
        f"| Mean citation validity | {pct(summary['mean_citation_validity'])} |",
        f"| Mean citation grounding | {pct(summary['mean_citation_grounding'])} |",
        f"| Answers with citations | {summary['answers_with_citations']}/{summary['questions']} ({pct(summary['answers_with_citations_pct'])}) |",
        f"| Answers without numeric hallucination | {summary['answers_without_numeric_hallucination']}/{summary['questions']} ({pct(summary['answers_without_numeric_hallucination_pct'])}) |",
        f"| Total suspicious numbers across all answers | {summary['total_suspicious_numbers']} |",
        "",
        "## Per-Question Detail",
        "",
        "| ID | Fact Recall | Cite Valid | Cite Ground | Susp. Nums | Missed Facts |",
        "|---|---:|---:|---:|---:|---|",
    ]

    for r in per_question:
        missed = ", ".join(r["fact_recall"]["missed"]) or "-"
        # Keep the missed-facts cell readable in markdown tables
        if len(missed) > 80:
            missed = missed[:77] + "..."
        missed = missed.replace("|", "\\|")

        fr = r["fact_recall"]["score"]
        cv = r["citation_validity"]["score"]
        cg = r["citation_grounding"]["score"]
        sn = r["numeric_hallucination"]["count"]

        lines.append(
            f"| {r['id']} | {pct(fr)} | {pct(cv)} | {pct(cg)} | {sn} | {missed} |"
        )

    lines.extend(["", "## Failure Cases", ""])

    failures = [
        r for r in per_question
        if (r["fact_recall"]["score"] or 0) < 0.5
        or r["numeric_hallucination"]["count"] > 0
        or (r["citation_validity"]["score"] or 0) < 1.0
    ]

    if not failures:
        lines.append("No clear failure cases detected.")
    else:
        for r in failures:
            lines.extend([
                f"### {r['id']}",
                "",
                f"**Question:** {r['question']}",
                "",
                "**Answer:**",
                "",
                "```",
                r["answer"],
                "```",
                "",
                f"- Fact recall: {pct(r['fact_recall']['score'])} "
                f"(missed: {', '.join(r['fact_recall']['missed']) or 'none'})",
                f"- Citation validity: {pct(r['citation_validity']['score'])}",
                f"- Citation grounding: {pct(r['citation_grounding']['score'])}",
                f"- Suspicious numbers: {r['numeric_hallucination']['suspicious'] or 'none'}",
                "",
            ])

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def _slugify(text: str) -> str:
    """
    Map a model identifier to a filesystem-safe slug.
    'qwen2.5:7b-instruct' -> 'qwen2_5_7b_instruct'
    'phi3:mini'           -> 'phi3_mini'
    """
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return slug or "model"


def _pipeline_slug(pipeline: str) -> str:
    """Compact form for filenames: 'v3_reranked' -> 'v3reranked'."""
    return pipeline.replace("_", "")


def derive_output_basename(model_name: str, pipeline: str, n_questions: int) -> str:
    return (
        f"answer_eval_summary_"
        f"{_slugify(model_name)}_"
        f"{_pipeline_slug(pipeline)}_"
        f"n{n_questions}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=str, default=str(BENCHMARK_PATH))
    parser.add_argument(
        "--model",
        type=str,
        default=OLLAMA_MODEL,
        help="Ollama model name. Default uses what chat_structured_ollama.py uses.",
    )
    parser.add_argument(
        "--pipeline",
        type=str,
        default=DEFAULT_PIPELINE,
        choices=SUPPORTED_PIPELINES,
        help="Retrieval pipeline. v2_hybrid is dense+BM25+RRF; "
             "v3_reranked adds a cross-encoder rerank stage.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit to first N questions (for quick smoke tests). 0 = all.",
    )
    parser.add_argument(
        "--output-basename",
        type=str,
        default="",
        help="Override the auto-generated output filename stem "
             "(without extension). Default is derived from --model + "
             "--pipeline + question count.",
    )
    args = parser.parse_args()

    benchmark_path = Path(args.benchmark)
    questions = load_questions(benchmark_path)

    if args.limit > 0:
        questions = questions[: args.limit]

    print(f"Loaded {len(questions)} questions from {benchmark_path}")
    print(f"Model:    {args.model}")
    print(f"Pipeline: {args.pipeline}")
    print("Building retrievers...")

    dense_db = load_dense_db()
    bm25_retriever = build_bm25_retriever()

    print(f"Running answer eval on {len(questions)} questions...\n")

    per_question = []
    for i, item in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {item.id}")
        try:
            run_result = run_pipeline(
                item.question,
                dense_db,
                bm25_retriever,
                args.model,
                pipeline=args.pipeline,
            )
            scored = score_question(item, run_result)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            scored = {
                "id": item.id,
                "question": item.question,
                "error": str(exc),
                "fact_recall": {"score": 0.0, "matched": [], "missed": item.expected_facts, "total": len(item.expected_facts)},
                "citation_validity": {"score": 0.0, "cited": [], "valid": [], "invalid": [], "any_cited": False},
                "citation_grounding": {"score": 0.0, "checked": 0, "grounded": 0},
                "numeric_hallucination": {"found_in_answer": [], "suspicious": [], "count": 0, "clean": True},
                "answer": "",
                "num_retrieved": 0,
                "retrieved_paper_ids": [],
                "retrieved_chunks": [],
                "expected_facts": item.expected_facts,
            }

        per_question.append(scored)

        fr = scored["fact_recall"]["score"]
        sn = scored["numeric_hallucination"]["count"]
        print(f"  fact_recall={pct(fr)}  suspicious_nums={sn}")

    summary = aggregate(per_question, args.model, args.pipeline)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    basename = args.output_basename or derive_output_basename(
        args.model, args.pipeline, len(questions)
    )
    json_path = RESULTS_DIR / f"{basename}.json"
    md_path = RESULTS_DIR / f"{basename}.md"

    json_path.write_text(
        json.dumps(
            {"summary": summary, "per_question": per_question},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    md_path.write_text(
        build_markdown_report(benchmark_path, summary, per_question),
        encoding="utf-8",
    )

    print("\n=== Summary ===")
    print(f"Pipeline:                {summary['pipeline']}")
    print(f"Mean fact recall:        {pct(summary['mean_fact_recall'])}")
    print(f"Mean citation validity:  {pct(summary['mean_citation_validity'])}")
    print(f"Mean citation grounding: {pct(summary['mean_citation_grounding'])}")
    print(f"Clean answers (no halluc nums): "
          f"{summary['answers_without_numeric_hallucination']}/{summary['questions']}")
    print(f"Total suspicious numbers: {summary['total_suspicious_numbers']}")
    print(f"\nSaved: {json_path}")
    print(f"Saved: {md_path}")


if __name__ == "__main__":
    main()