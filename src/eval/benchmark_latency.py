"""
NeuroRag latency + cost benchmark.

Measures end-to-end query latency for each retrieval pipeline (v1 baseline,
v2 hybrid, v3 reranked) over the benchmark questions, and produces the kind of
concrete, quotable numbers that sell — e.g. "v3 reranked answers in 3.1 s median,
4.8 s p95" — plus an optional hosted-API cost estimate for the case where Ollama
is swapped for a paid LLM endpoint.

It reuses the *exact* production pipeline entry points that the Streamlit UI
(``app.py``) uses, so it measures the real system, not a reimplementation.

Run from the project root (indexes built + Ollama running, see the README):

    python src/eval/benchmark_latency.py                       # all pipelines, all 63 questions
    python src/eval/benchmark_latency.py --limit 10            # quick smoke test
    python src/eval/benchmark_latency.py --pipelines v2_hybrid,v3_reranked
    python src/eval/benchmark_latency.py --cost-per-1m-input 0.15 --cost-per-1m-output 0.60

Output: results/latency_benchmark_{pipelines}_n{N}.{json,md}

Latency depends on your hardware and the Ollama model, so treat absolute numbers
as machine-specific. The *relative* cost of v1 vs v2 vs v3 on the same machine is
the portable, comparable signal.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------
# Project paths and import bootstrap (mirrors app.py / run_answer_eval.py)
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
for _rel in ("src", "src/pipelines/v1", "src/pipelines/v2", "src/pipelines/v3"):
    _p = str(BASE_DIR / _rel)
    if _p not in sys.path:
        sys.path.insert(0, _p)

BENCHMARK_PATH = BASE_DIR / "benchmarks" / "answer_eval_questions.jsonl"
RESULTS_DIR = BASE_DIR / "results"

PIPELINE_LABELS = {
    "v1": "v1 baseline (flat RAG)",
    "v2_hybrid": "v2 hybrid (dense + BM25 + RRF)",
    "v3_reranked": "v3 reranked (cross-encoder)",
}
DEFAULT_PIPELINES = ("v1", "v2_hybrid", "v3_reranked")


# ---------------------------------------------------------------------
# Token estimation (rough — for the optional hosted-cost projection only)
# ---------------------------------------------------------------------

def _make_token_counter():
    """Return a function str -> approx token count.

    Uses tiktoken if available (accurate for OpenAI-family pricing); otherwise
    falls back to a ~4-chars-per-token heuristic. Either way the cost figure is
    explicitly a rough projection, not a measured bill.
    """
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return lambda text: len(enc.encode(text or ""))
    except Exception:  # noqa: BLE001 — any failure -> heuristic fallback
        return lambda text: max(1, len(text or "") // 4)


count_tokens = _make_token_counter()


# ---------------------------------------------------------------------
# Question loading
# ---------------------------------------------------------------------

def load_questions(path: Path, limit: int | None) -> list[dict]:
    questions: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            questions.append({"id": row.get("id", ""), "question": row["question"]})
    if limit is not None:
        questions = questions[:limit]
    return questions


# ---------------------------------------------------------------------
# Pipeline dispatch — reuses the production entry points (see app.py)
# ---------------------------------------------------------------------

def make_runner(pipeline: str):
    """Load heavy resources once and return ``runner(question) -> result_dict``.

    The returned result dict always carries the answer text and the retrieved
    documents, so the caller can estimate token usage uniformly.
    """
    if pipeline == "v1":
        import chat_ollama

        db = chat_ollama.load_db()

        def runner(question: str) -> dict:
            result = chat_ollama.run_query(question, db)
            retrieved = [getattr(d, "page_content", "") for d in result.get("docs", [])]
            return {"answer": result.get("answer", ""), "retrieved": retrieved}

        return runner

    import chat_structured_ollama as chat

    dense_db = chat.load_dense_db()
    bm25 = chat.build_bm25_retriever()

    def runner(question: str) -> dict:
        result = chat.run_query(question, dense_db, bm25, pipeline=pipeline)
        retrieved = [
            getattr(item.get("doc"), "page_content", "")
            for item in result.get("final_results", [])
        ]
        return {"answer": result.get("answer", ""), "retrieved": retrieved}

    return runner


# ---------------------------------------------------------------------
# Benchmark one pipeline
# ---------------------------------------------------------------------

def benchmark_pipeline(
    pipeline: str,
    questions: list[dict],
    warmup: bool,
) -> dict:
    runner = make_runner(pipeline)

    if warmup and questions:
        # Exclude cold-start (model load, first-call JIT) from the timings.
        try:
            runner(questions[0]["question"])
        except Exception as exc:  # noqa: BLE001
            print(f"  [warmup failed for {pipeline}: {exc}]")

    per_query: list[dict] = []
    for q in questions:
        start = time.perf_counter()
        result = runner(q["question"])
        elapsed = time.perf_counter() - start

        in_tokens = sum(count_tokens(t) for t in result["retrieved"])
        out_tokens = count_tokens(result["answer"])
        per_query.append(
            {
                "id": q["id"],
                "seconds": round(elapsed, 3),
                "input_tokens": in_tokens,
                "output_tokens": out_tokens,
            }
        )
        print(f"  {pipeline:<12} {q['id']:<45} {elapsed:6.2f}s")

    times = [r["seconds"] for r in per_query]
    return {
        "pipeline": pipeline,
        "label": PIPELINE_LABELS.get(pipeline, pipeline),
        "n": len(per_query),
        "latency_seconds": _latency_stats(times),
        "total_input_tokens": sum(r["input_tokens"] for r in per_query),
        "total_output_tokens": sum(r["output_tokens"] for r in per_query),
        "per_query": per_query,
    }


def _latency_stats(times: list[float]) -> dict:
    if not times:
        return {"mean": 0, "median": 0, "p95": 0, "min": 0, "max": 0}
    ordered = sorted(times)
    p95_idx = max(0, int(round(0.95 * (len(ordered) - 1))))
    return {
        "mean": round(statistics.mean(times), 3),
        "median": round(statistics.median(times), 3),
        "p95": round(ordered[p95_idx], 3),
        "min": round(min(times), 3),
        "max": round(max(times), 3),
    }


# ---------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------

def estimate_cost(summary: dict, in_price: float, out_price: float) -> float:
    """Projected per-1000-query cost IF generation ran on a hosted API.

    Prices are USD per 1,000,000 tokens. Local Ollama generation has no API cost
    (compute only); this projection is for the "swap Ollama for a paid endpoint"
    conversation. Returns cost for 1,000 queries at the benchmark's average usage.
    """
    n = max(1, summary["n"])
    avg_in = summary["total_input_tokens"] / n
    avg_out = summary["total_output_tokens"] / n
    per_query = (avg_in * in_price + avg_out * out_price) / 1_000_000
    return round(per_query * 1000, 4)


def build_markdown(summaries: list[dict], in_price: float, out_price: float) -> str:
    lines = [
        "# NeuroRag latency + cost benchmark",
        "",
        f"Questions per pipeline: **{summaries[0]['n'] if summaries else 0}**  ",
        "Latency is end-to-end (retrieval + generation) on this machine. "
        "Absolute numbers are hardware/model specific; the v1→v2→v3 comparison "
        "on the same machine is the portable signal.",
        "",
        "## Latency (seconds)",
        "",
        "| Pipeline | Median | Mean | p95 | Min | Max |",
        "|----------|-------:|-----:|----:|----:|----:|",
    ]
    for s in summaries:
        lat = s["latency_seconds"]
        lines.append(
            f"| {s['label']} | {lat['median']:.2f} | {lat['mean']:.2f} | "
            f"{lat['p95']:.2f} | {lat['min']:.2f} | {lat['max']:.2f} |"
        )

    show_cost = in_price > 0 or out_price > 0
    if show_cost:
        lines += [
            "",
            "## Projected hosted-API cost",
            "",
            f"_If generation were served by a paid endpoint at "
            f"${in_price:.2f}/1M input and ${out_price:.2f}/1M output tokens. "
            "Local Ollama generation has no API cost._",
            "",
            "| Pipeline | Avg input tok | Avg output tok | $ / 1,000 queries |",
            "|----------|--------------:|---------------:|------------------:|",
        ]
        for s in summaries:
            n = max(1, s["n"])
            lines.append(
                f"| {s['label']} | {s['total_input_tokens'] // n} | "
                f"{s['total_output_tokens'] // n} | "
                f"${estimate_cost(s, in_price, out_price):.2f} |"
            )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark NeuroRag pipeline latency and cost.")
    parser.add_argument(
        "--pipelines",
        default=",".join(DEFAULT_PIPELINES),
        help="Comma-separated subset of: v1, v2_hybrid, v3_reranked",
    )
    parser.add_argument("--limit", type=int, default=None, help="First N questions only")
    parser.add_argument("--benchmark", type=Path, default=BENCHMARK_PATH)
    parser.add_argument(
        "--no-warmup", action="store_true", help="Skip the cold-start warmup query"
    )
    parser.add_argument(
        "--cost-per-1m-input", type=float, default=0.0,
        help="USD per 1M input tokens for the optional hosted-cost projection",
    )
    parser.add_argument(
        "--cost-per-1m-output", type=float, default=0.0,
        help="USD per 1M output tokens for the optional hosted-cost projection",
    )
    parser.add_argument("--output-basename", default=None)
    args = parser.parse_args()

    pipelines = [p.strip() for p in args.pipelines.split(",") if p.strip()]
    unknown = [p for p in pipelines if p not in PIPELINE_LABELS]
    if unknown:
        parser.error(f"Unknown pipeline(s): {unknown}. Choose from {list(PIPELINE_LABELS)}")

    questions = load_questions(args.benchmark, args.limit)
    print(f"Loaded {len(questions)} questions. Benchmarking: {pipelines}\n")

    summaries = []
    for pipeline in pipelines:
        print(f"== {PIPELINE_LABELS[pipeline]} ==")
        summaries.append(
            benchmark_pipeline(pipeline, questions, warmup=not args.no_warmup)
        )
        print()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    basename = args.output_basename or (
        f"latency_benchmark_{'_'.join(pipelines)}_n{len(questions)}"
    )
    json_path = RESULTS_DIR / f"{basename}.json"
    md_path = RESULTS_DIR / f"{basename}.md"

    payload = {
        "n_questions": len(questions),
        "pipelines": pipelines,
        "cost_per_1m_input": args.cost_per_1m_input,
        "cost_per_1m_output": args.cost_per_1m_output,
        "summaries": summaries,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(
        build_markdown(summaries, args.cost_per_1m_input, args.cost_per_1m_output),
        encoding="utf-8",
    )

    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print("\n" + build_markdown(summaries, args.cost_per_1m_input, args.cost_per_1m_output))


if __name__ == "__main__":
    main()
