"""
Optional RAGAS evaluation for NeuroRag.

NeuroRag's primary answer-quality eval is the custom harness in
``run_answer_eval.py`` (fact recall, citation validity/grounding, numeric
hallucination). This script is an *optional* second opinion that scores the
same runs with the widely recognised RAGAS metrics:

    faithfulness        - is the answer grounded in the retrieved contexts?
    answer_relevancy    - does the answer actually address the question?
    context_precision   - are the retrieved contexts on-topic / well-ranked?
    context_recall      - do the retrieved contexts cover the reference?

It reads an existing ``results/answer_eval_summary_*.json`` produced by
``run_answer_eval.py`` and re-scores it, so no pipeline re-run is needed.

Local-first: the judge LLM is the local Ollama model and the embeddings are
the same local sentence-transformer the pipelines use. No hosted API or key
is required. Install the optional dependencies first::

    pip install -r requirements-optional.txt

Run from the project root::

    python src/eval/run_ragas_eval.py
    python src/eval/run_ragas_eval.py --results-file results/answer_eval_summary_qwen2_5_7b_v3reranked_n63.json
    python src/eval/run_ragas_eval.py --limit 5            # quick smoke test
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import warnings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / "src"))
from config import settings  # noqa: E402

RESULTS_DIR = BASE_DIR / "results"
DEFAULT_RESULTS_FILE = RESULTS_DIR / "answer_eval_summary_qwen2_5_7b_v3reranked_n63.json"


def extract_answer_body(response: str) -> str:
    """Pull the ``Answer:`` section out of the structured model output.

    ``run_answer_eval.py`` stores the normalized 3-section output. RAGAS
    scores the answer text itself, so we strip the evidence-summary and
    source-id scaffolding. Falls back to the full response if the structure
    is not present.
    """
    match = re.search(
        r"(?is)answer\s*:\s*(.*?)(?:\n\s*evidence summary\s*:|\Z)", response
    )
    return match.group(1).strip() if match else response.strip()


def load_samples(results_file: Path, limit: int | None) -> list[dict]:
    """Build RAGAS-shaped sample dicts from an answer-eval result file."""
    data = json.loads(results_file.read_text(encoding="utf-8"))
    per_question = data["per_question"]
    if limit is not None:
        per_question = per_question[:limit]

    samples = []
    for record in per_question:
        contexts = [
            chunk["preview"]
            for chunk in record.get("retrieved_chunks", [])
            if chunk.get("preview")
        ]
        # The benchmark's expected facts act as the reference for the
        # context_recall / context_precision metrics.
        reference = "; ".join(record.get("expected_facts", []))
        samples.append(
            {
                "user_input": record["question"],
                "response": extract_answer_body(record["answer"]),
                "retrieved_contexts": contexts,
                "reference": reference,
            }
        )
    return samples


def build_evaluator_llm():
    """Local Ollama chat model wrapped for RAGAS."""
    from langchain_ollama import ChatOllama
    from ragas.llms import LangchainLLMWrapper

    return LangchainLLMWrapper(
        ChatOllama(model=settings.v2_ollama_model, temperature=0.0)
    )


def build_evaluator_embeddings():
    """The same local sentence-transformer the pipelines use, wrapped for RAGAS."""
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:  # pragma: no cover - fallback for older langchain
        from langchain_community.embeddings import HuggingFaceEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper

    return LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name=settings.embedding_model)
    )


def run_ragas(samples: list[dict], timeout: int, max_workers: int):
    """Run the RAGAS evaluation and return the EvaluationResult.

    A local Ollama model is much slower than the hosted APIs RAGAS assumes,
    so the per-job timeout is raised well above the RAGAS default and the
    worker count kept low to avoid overloading a single Ollama instance.
    """
    from ragas import EvaluationDataset, evaluate
    from ragas.run_config import RunConfig

    # These metric instances are deprecated in favour of ragas.metrics.collections
    # in a future major release, but remain the supported path on ragas 0.4.x.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

    dataset = EvaluationDataset.from_list(samples)
    return evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=build_evaluator_llm(),
        embeddings=build_evaluator_embeddings(),
        run_config=RunConfig(timeout=timeout, max_workers=max_workers),
    )


def aggregate_scores(result) -> dict:
    """Average each RAGAS metric across all scored samples.

    ``result.scores`` is a list of per-sample ``{metric: value}`` dicts;
    samples where a metric failed/returned None are skipped for that metric.
    """
    totals: dict[str, list[float]] = {}
    for row in result.scores:
        for metric, value in row.items():
            if value is None:
                continue
            try:
                num = float(value)
            except (TypeError, ValueError):
                continue
            if math.isnan(num):
                continue
            totals.setdefault(metric, []).append(num)
    return {m: sum(vals) / len(vals) for m, vals in totals.items() if vals}


def write_reports(result, results_file: Path, sample_count: int) -> tuple[Path, Path]:
    """Write a JSON and a markdown summary next to the source results file."""
    scores = aggregate_scores(result)

    stem = results_file.stem
    json_path = RESULTS_DIR / f"ragas_eval_{stem}.json"
    md_path = RESULTS_DIR / f"ragas_eval_{stem}.md"

    payload = {
        "source_results_file": results_file.name,
        "questions_scored": sample_count,
        "judge_model": settings.v2_ollama_model,
        "embedding_model": settings.embedding_model,
        "scores": scores,
    }
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    lines = [
        f"# RAGAS evaluation — {results_file.name}",
        "",
        f"- Questions scored: {sample_count}",
        f"- Judge LLM: `{settings.v2_ollama_model}` (local Ollama)",
        f"- Embeddings: `{settings.embedding_model}`",
        "",
        "| Metric | Score |",
        "|--------|------:|",
    ]
    for name, value in scores.items():
        lines.append(f"| {name} | {value:.3f} |")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-file",
        type=Path,
        default=DEFAULT_RESULTS_FILE,
        help="answer_eval_summary_*.json file to re-score with RAGAS",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="score only the first N questions (quick smoke test)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="per-job timeout in seconds (raise for slow local models)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=2,
        help="concurrent RAGAS jobs (keep low for a single local Ollama instance)",
    )
    args = parser.parse_args()

    results_file = args.results_file
    if not results_file.is_absolute():
        results_file = BASE_DIR / results_file
    if not results_file.exists():
        raise SystemExit(
            f"Results file not found: {results_file}\n"
            "Run run_answer_eval.py first, or pass --results-file."
        )

    samples = load_samples(results_file, args.limit)
    print(f"Scoring {len(samples)} questions from {results_file.name} with RAGAS...")

    result = run_ragas(samples, timeout=args.timeout, max_workers=args.max_workers)
    json_path, md_path = write_reports(result, results_file, len(samples))

    print(f"\nRAGAS scores:\n{result}")
    print(f"\nWrote: {json_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
