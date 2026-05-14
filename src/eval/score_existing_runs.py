"""
Re-score existing answer-eval JSON files with the Gemini-based fact
recall judge.

Reads one or more results/answer_eval_summary_*.json files, runs the
LLM judge on each per-question record, and writes:
  results/{basename}_judged.json   - augmented JSON with fact_recall_judge
  results/{basename}_judged.md     - markdown report comparing strict vs judge

This script is intentionally separate from run_answer_eval.py because:
  - it lets us re-score archived runs without re-running retrieval
  - judge runs are slow (~7s per question) and we want to retry/cache
    independently of the generation pipeline
  - run_answer_eval.py stays self-contained and doesn't take a hard
    dependency on google-genai or GEMINI_API_KEY at import time

Usage from project root:
    python src/eval/score_existing_runs.py results/answer_eval_summary_qwen2_5_7b_n63.json
    python src/eval/score_existing_runs.py results/answer_eval_summary_*.json
    python src/eval/score_existing_runs.py --skip-cache results/answer_eval_summary_qwen2_5_7b_n63.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean


# Make src/eval importable when this script is run directly from the
# project root (python src/eval/score_existing_runs.py ...).
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from llm_judge import judge_fact_recall, JUDGE_MODEL, DEFAULT_CACHE_DIR  # noqa: E402


BASE_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = BASE_DIR / "results"


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def re_score_file(input_path: Path, *, use_cache: bool = True) -> Path:
    """
    Add fact_recall_judge to each per-question record in input_path,
    update the summary's mean, and write `{basename}_judged.json`.
    Returns the path of the new JSON file.
    """
    print(f"\n=== Judging {input_path.name} ===")
    data = json.loads(input_path.read_text(encoding="utf-8"))

    summary = data.get("summary", {})
    per_question = data.get("per_question", [])
    n = len(per_question)
    if n == 0:
        raise ValueError(f"No per_question records in {input_path}")

    print(f"Model:    {summary.get('model', '?')}")
    print(f"Pipeline: {summary.get('pipeline', '?')}")
    print(f"Judge:    {JUDGE_MODEL}")
    print(f"Records:  {n}")
    print()

    cache_hits = 0
    api_calls = 0
    failures = 0

    for i, q in enumerate(per_question, start=1):
        qid = q.get("id", f"q{i}")
        question = q.get("question", "")
        answer = q.get("answer", "")
        expected_facts = q.get("expected_facts", [])

        result = judge_fact_recall(
            question_id=qid,
            question=question,
            expected_facts=expected_facts,
            answer=answer,
            use_cache=use_cache,
        )

        # Hard-fail tracking is separate from cache vs API tracking so
        # the summary line at the end is informative.
        if result.judge_failed:
            failures += 1
        if result.cached:
            cache_hits += 1
        else:
            api_calls += 1

        q["fact_recall_judge"] = result.to_dict()

        # Strict score is already on the record from the original run.
        strict = q.get("fact_recall", {}).get("score", 0.0)
        marker = "(cached)" if result.cached else ""
        if result.judge_failed:
            marker = "(JUDGE FAILED -> strict fallback)"
        print(
            f"  [{i:>2}/{n}] {qid:<55} "
            f"strict={pct(strict):>6}  judge={pct(result.score):>6}  {marker}"
        )

    # Update the summary with judge means.
    judge_scores = [
        q["fact_recall_judge"]["score"] for q in per_question
    ]
    summary["mean_fact_recall_judge"] = mean(judge_scores) if judge_scores else 0.0
    summary["judge_model"] = JUDGE_MODEL
    summary["judge_failures"] = failures
    data["summary"] = summary

    out_json = RESULTS_DIR / f"{input_path.stem}_judged.json"
    out_json.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    out_md = RESULTS_DIR / f"{input_path.stem}_judged.md"
    out_md.write_text(build_judged_markdown(data), encoding="utf-8")

    print()
    print(f"  Cache hits: {cache_hits}    API calls: {api_calls}    "
          f"Failures: {failures}")
    print(f"  Strict mean fact_recall:        "
          f"{pct(summary.get('mean_fact_recall'))}")
    print(f"  Judge  mean fact_recall_judge:  "
          f"{pct(summary['mean_fact_recall_judge'])}")
    print(f"  Saved: {out_json.name}")
    print(f"  Saved: {out_md.name}")

    return out_json


def build_judged_markdown(data: dict) -> str:
    summary = data.get("summary", {})
    per_question = data.get("per_question", [])

    strict_mean = summary.get("mean_fact_recall")
    judge_mean = summary.get("mean_fact_recall_judge")

    lines = [
        "# NeuroRag Answer Evaluation (LLM-judged fact recall)",
        "",
        f"Model:    `{summary.get('model', '?')}`",
        f"Pipeline: `{summary.get('pipeline', '?')}`",
        f"Judge:    `{summary.get('judge_model', JUDGE_MODEL)}`",
        f"Questions: {len(per_question)}",
        f"Judge failures: {summary.get('judge_failures', 0)}",
        "",
        "## Headline",
        "",
        "| Metric | Strict substring | LLM judge |",
        "|---|---:|---:|",
        f"| Mean fact recall | {pct(strict_mean)} | {pct(judge_mean)} |",
        f"| Mean citation validity | {pct(summary.get('mean_citation_validity'))} | n/a (deterministic) |",
        f"| Mean citation grounding | {pct(summary.get('mean_citation_grounding'))} | n/a (deterministic) |",
        "",
        "Strict fact recall counts a fact as matched only when the answer "
        "contains the exact substring. The LLM judge labels each fact as "
        "`present` (1.0), `partial` (0.5), or `absent` (0.0) and takes "
        "the mean. Paraphrases and synonyms count under the judge but "
        "not under strict matching.",
        "",
        "## Per-question scores",
        "",
        "| ID | Strict | Judge | Δ |",
        "|---|---:|---:|---:|",
    ]

    for q in per_question:
        qid = q.get("id", "")
        strict = q.get("fact_recall", {}).get("score", 0.0)
        judge = q.get("fact_recall_judge", {}).get("score", 0.0)
        delta = judge - strict
        delta_str = ""
        if delta > 0.01:
            delta_str = f"+{delta * 100:.0f}pp"
        elif delta < -0.01:
            delta_str = f"{delta * 100:.0f}pp"
        else:
            delta_str = "0"
        lines.append(
            f"| {qid} | {pct(strict)} | {pct(judge)} | {delta_str} |"
        )

    # A short rationale view so reviewers can spot-check the judge.
    lines.extend([
        "",
        "## Sample judge rationales",
        "",
        "Showing the first 5 questions' per-fact rationales for transparency.",
        "",
    ])
    for q in per_question[:5]:
        qid = q.get("id", "")
        judge_block = q.get("fact_recall_judge", {})
        per_fact = judge_block.get("per_fact", [])
        if not per_fact:
            continue
        lines.append(f"### {qid}")
        lines.append("")
        for pf in per_fact:
            lines.append(
                f"- **{pf.get('label', '?')}** — {pf.get('fact', '')}"
            )
            rationale = pf.get("rationale", "")
            if rationale:
                lines.append(f"  - {rationale}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more answer_eval_summary_*.json files to judge.",
    )
    parser.add_argument(
        "--skip-cache",
        action="store_true",
        help="Force fresh API calls for every question, ignoring cache.",
    )
    args = parser.parse_args()

    print(f"Cache directory: {DEFAULT_CACHE_DIR}")
    if args.skip_cache:
        print("Cache: DISABLED (every question will hit the API)")
    print()

    paths = [Path(p) for p in args.inputs]
    missing = [p for p in paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"ERROR: file not found: {p}", file=sys.stderr)
        sys.exit(1)

    for p in paths:
        re_score_file(p, use_cache=not args.skip_cache)


if __name__ == "__main__":
    main()
