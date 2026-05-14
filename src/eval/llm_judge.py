"""
LLM-as-judge for fact recall.

Replaces the strict-substring fact_recall scorer in run_answer_eval.py.
For each (question, expected_facts, answer) triple, we ask Gemini 2.5
Flash to label every expected fact as one of:

    present   -> the answer clearly states this fact (paraphrase OK)
    partial   -> the answer states part of the fact, or hints at it
                 without committing to the full claim
    absent    -> the answer does not state or imply this fact

Labels map to numeric scores 1.0 / 0.5 / 0.0, then averaged across the
question's facts to produce a single judge score directly comparable
to the existing strict-substring score.

Design notes
------------
- ONE Gemini call per question, judging all facts together. This is
  ~7x fewer API calls than per-fact and lets the model reason about
  the answer holistically.
- Structured output via Pydantic schema -> response.parsed gives a
  validated object. No fragile regex on free-form text.
- On-disk cache keyed by sha256(question_id + answer + sorted(facts)).
  Reruns with the same inputs hit cache and pay zero API cost.
- Conservative rate limit: free tier is 10 RPM, we sleep 7s between
  live calls. Plenty of margin for transient slowdowns.
- Failures fall back to strict-substring score and tag the record
  with judge_failed=True so they're easy to filter in analysis.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

JUDGE_MODEL = "gemini-2.5-flash"

# Free tier is 10 RPM. 7s between calls = ~8.5 RPM, leaves margin for
# slow responses or transient retries without hitting 429.
SECONDS_BETWEEN_CALLS = 7.0

# Where cached judgments live. One file per question hash. Cheap to
# inspect/diff; easy to invalidate by deleting individual files.
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "neurorag_judge"

# How long to wait on a single Gemini call before giving up.
REQUEST_TIMEOUT_SECONDS = 60

# Map labels to scores. Defined here so all downstream code agrees.
LABEL_TO_SCORE = {"present": 1.0, "partial": 0.5, "absent": 0.0}


# ---------------------------------------------------------------------
# Module state — lazy client, last-call timestamp for rate limiting
# ---------------------------------------------------------------------

_genai_client = None
_last_call_at: float = 0.0


def _get_client():
    """Lazy import + construct so importing this module is cheap and
    doesn't error out when GEMINI_API_KEY isn't set (e.g. on a CI box
    that only re-scores from cache)."""
    global _genai_client
    if _genai_client is None:
        # Imported here so users who only use the cache don't need
        # google-genai installed.
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY env var is not set. "
                "Get a free key at https://aistudio.google.com/apikey"
            )
        _genai_client = genai.Client(api_key=api_key)
    return _genai_client


def _rate_limit_sleep() -> None:
    """Sleep just long enough that the next call respects SECONDS_BETWEEN_CALLS."""
    global _last_call_at
    now = time.monotonic()
    elapsed = now - _last_call_at
    if elapsed < SECONDS_BETWEEN_CALLS:
        time.sleep(SECONDS_BETWEEN_CALLS - elapsed)
    _last_call_at = time.monotonic()


# ---------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------

def _cache_key(question_id: str, answer: str, facts: list[str]) -> str:
    """
    Stable key across runs. Sorting facts means re-ordering the
    benchmark's expected_facts list doesn't bust the cache.
    """
    payload = json.dumps(
        {
            "qid": question_id,
            "answer": answer,
            "facts": sorted(facts),
            # Bump this if we change the rubric or model; old cache is
            # silently invalidated when keys no longer match.
            "rubric_version": "v1",
            "model": JUDGE_MODEL,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.json"


def _load_cached(cache_dir: Path, key: str) -> dict | None:
    path = _cache_path(cache_dir, key)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Corrupt cache entry — pretend it's not there.
        return None


def _save_cached(cache_dir: Path, key: str, value: dict) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    _cache_path(cache_dir, key).write_text(
        json.dumps(value, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------
# Prompt + structured output schema
# ---------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """You are a strict but fair grader of scientific question-answering.

You will be shown:
  - a research question,
  - a list of expected facts (the rubric),
  - a candidate answer.

For each expected fact, decide whether the candidate answer conveys it.

Use exactly one of these labels per fact:
  present  - The answer clearly states the fact, in original words or
             a faithful paraphrase. Synonymous terminology counts as
             present (e.g., "peripheral terminal" vs "peripheral
             process", "axon" vs "central process", "hearing onset"
             vs "P12-P14"). Numerical values must match within obvious
             rounding (e.g., "about 32 mm" vs "32.35 mm" is present).
  partial  - The answer mentions part of the fact, gives a vague or
             qualified version, or implies it without committing.
             Use this for half-right numbers, missing units, or
             gestures toward the right idea without naming it.
  absent   - The answer does not state, paraphrase, or imply the fact.
             Wrong values, contradictory claims, or silence all count
             as absent.

Be charitable about wording but strict about content. The goal is to
measure whether the answer would actually inform a reader looking up
this fact, not whether it copies the rubric verbatim.

For each fact, also give a one-sentence rationale explaining the
label. The rationale must reference specific words from the answer
where possible.
"""


def _build_user_prompt(question: str, facts: list[str], answer: str) -> str:
    fact_lines = "\n".join(f"  {i + 1}. {f}" for i, f in enumerate(facts))
    return (
        f"QUESTION:\n{question}\n\n"
        f"EXPECTED FACTS (the rubric):\n{fact_lines}\n\n"
        f"CANDIDATE ANSWER:\n{answer}\n\n"
        f"For each numbered fact above, output a label and rationale. "
        f"Return facts in the same order as the rubric."
    )


def _build_schema(num_facts: int) -> dict:
    """
    JSON schema for Gemini structured output. We use a fact_judgments
    array with a fixed length matching the rubric so the response is
    one-to-one with our expected_facts list.

    We don't use Pydantic here so this module has zero hard import
    dependency on pydantic — the SDK accepts plain JSON Schema dicts.
    """
    return {
        "type": "object",
        "required": ["fact_judgments"],
        "properties": {
            "fact_judgments": {
                "type": "array",
                "minItems": num_facts,
                "maxItems": num_facts,
                "items": {
                    "type": "object",
                    "required": ["fact_index", "label", "rationale"],
                    "properties": {
                        "fact_index": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": num_facts,
                        },
                        "label": {
                            "type": "string",
                            "enum": ["present", "partial", "absent"],
                        },
                        "rationale": {
                            "type": "string",
                        },
                    },
                },
            },
        },
    }


# ---------------------------------------------------------------------
# Strict-matcher fallback (mirrors run_answer_eval.score_fact_recall)
# ---------------------------------------------------------------------

def _strict_score(answer: str, facts: list[str]) -> dict:
    """
    Deterministic substring fallback. Used when:
      - facts list is empty (judge has nothing to grade)
      - the answer itself is empty
      - Gemini call fails after retries
    """
    a = (answer or "").lower()
    matched, missed = [], []
    for f in facts:
        f_norm = (f or "").strip().lower()
        if not f_norm:
            continue
        if f_norm in a:
            matched.append(f)
        else:
            missed.append(f)
    total = len(matched) + len(missed)
    score = (len(matched) / total) if total else 0.0
    return {
        "score": score,
        "matched": matched,
        "missed": missed,
        "total": total,
    }


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

@dataclass
class JudgeResult:
    """
    Container for one judged question. Serializes cleanly to JSON via
    asdict(); merge into the per_question record by setting
    record['fact_recall_judge'] = asdict(result).
    """
    score: float
    per_fact: list[dict] = field(default_factory=list)
    judge_model: str = JUDGE_MODEL
    judge_failed: bool = False
    error: str | None = None
    cached: bool = False

    def to_dict(self) -> dict:
        d = {
            "score": self.score,
            "per_fact": self.per_fact,
            "judge_model": self.judge_model,
            "judge_failed": self.judge_failed,
            "cached": self.cached,
        }
        if self.error:
            d["error"] = self.error
        return d


def judge_fact_recall(
    question_id: str,
    question: str,
    expected_facts: list[str],
    answer: str,
    *,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    use_cache: bool = True,
) -> JudgeResult:
    """
    Score one question's answer against its expected facts using
    Gemini 2.5 Flash. Returns a JudgeResult with per-fact labels and
    an averaged numeric score on the same 0..1 scale as the strict
    substring matcher.

    If expected_facts is empty, returns score 0.0 (matching the strict
    matcher's behavior on the empty case) without making a call.
    """
    facts = [f for f in (expected_facts or []) if f and f.strip()]
    if not facts:
        return JudgeResult(score=0.0, per_fact=[])

    # Empty answers can't possibly contain facts; skip the API call.
    if not (answer or "").strip():
        return JudgeResult(
            score=0.0,
            per_fact=[
                {
                    "fact": f,
                    "label": "absent",
                    "rationale": "Answer is empty.",
                }
                for f in facts
            ],
        )

    # Cache check.
    key = _cache_key(question_id, answer, facts)
    if use_cache:
        cached = _load_cached(cache_dir, key)
        if cached is not None:
            return JudgeResult(
                score=cached["score"],
                per_fact=cached["per_fact"],
                judge_model=cached.get("judge_model", JUDGE_MODEL),
                judge_failed=cached.get("judge_failed", False),
                error=cached.get("error"),
                cached=True,
            )

    # Live call.
    try:
        result = _judge_via_api(question, facts, answer)
    except Exception as exc:
        # On hard failure, fall back to strict matcher and tag the
        # record so analysis can filter it out cleanly.
        strict = _strict_score(answer, facts)
        return JudgeResult(
            score=strict["score"],
            per_fact=[
                {
                    "fact": f,
                    "label": "present" if f in strict["matched"] else "absent",
                    "rationale": "Judge failed; strict substring fallback.",
                }
                for f in facts
            ],
            judge_failed=True,
            error=f"{type(exc).__name__}: {exc}",
        )

    if use_cache:
        _save_cached(cache_dir, key, result.to_dict())

    return result


def _judge_via_api(question: str, facts: list[str], answer: str) -> JudgeResult:
    """
    Single live call to Gemini, with structured output. Retries once
    on transient errors (rate limit, timeout, transient 5xx). Anything
    else propagates so the caller can decide whether to fall back.
    """
    client = _get_client()
    schema = _build_schema(len(facts))
    config = {
        "response_mime_type": "application/json",
        "response_schema": schema,
        "system_instruction": JUDGE_SYSTEM_PROMPT,
        # Low temperature: judging is supposed to be repeatable, not creative.
        "temperature": 0.1,
    }
    prompt = _build_user_prompt(question, facts, answer)

    # Up to 3 attempts. We retry on:
    #   - 429 / rate / quota errors (rate limit hiccups even within tier)
    #   - 5xx server errors (transient backend failures)
    #   - timeout / deadline / connection errors (network blip)
    #   - RuntimeError raised by _parse_response when Gemini returns
    #     malformed JSON despite response_schema (rare, happens under
    #     load and is recoverable)
    # Backoff doubles between attempts: short pause, then long pause.
    last_exc: Exception | None = None
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            _rate_limit_sleep()
            response = client.models.generate_content(
                model=JUDGE_MODEL,
                contents=prompt,
                config=config,
            )
            return _parse_response(response, facts)
        except Exception as exc:
            last_exc = exc
            if attempt >= max_attempts - 1:
                raise
            if not _is_transient_error(exc):
                raise
            # Exponential backoff: 2s, then 4s. Plenty of margin
            # for a transient blip without dragging the run.
            backoff = SECONDS_BETWEEN_CALLS * (2 ** (attempt + 1))
            time.sleep(backoff)
            continue

    # Defensive — loop should always either return or raise.
    raise last_exc or RuntimeError("Judge call failed for unknown reason")


def _is_transient_error(exc: Exception) -> bool:
    """
    Decide whether to retry a failed Gemini call.

    True for: 429s, 5xx server errors, timeouts, and JSON parse errors
    from the response (which sometimes happens under load even with
    response_schema set). False for auth errors, invalid request
    errors (4xx other than 429), and other permanent failures.
    """
    msg = str(exc).lower()

    # Auth / permission / quota cap — not retryable; user must act.
    permanent_markers = (
        "401", "403",
        "api key", "authentication",
        "spending cap", "spend cap", "billing",
        "permission denied",
    )
    if any(m in msg for m in permanent_markers):
        return False

    # Transient: rate / server / network / parse.
    transient_markers = (
        "429", "rate limit", "resource_exhausted",
        "500", "502", "503", "504",
        "timeout", "deadline", "unavailable",
        "connection", "reset",
        "non-json", "json", "parse",
    )
    return any(m in msg for m in transient_markers)


def _parse_response(response, facts: list[str]) -> JudgeResult:
    """
    Pull fact_judgments out of a Gemini response. We trust the schema
    for shape but still defensively re-align by fact_index in case the
    model returns items out of order.
    """
    # response.parsed is the Pydantic-typed payload when response_schema
    # is given; we asked for plain dict output, so parse from .text.
    raw = response.text or ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Judge returned non-JSON despite response_schema: {raw[:300]!r}"
        ) from exc

    judgments = payload.get("fact_judgments", [])
    by_index = {}
    for j in judgments:
        try:
            idx = int(j["fact_index"])
        except (KeyError, TypeError, ValueError):
            continue
        by_index[idx] = j

    per_fact = []
    scores = []
    for i, fact in enumerate(facts, start=1):
        j = by_index.get(i)
        if j is None:
            # Model skipped this fact — count as absent and record why.
            per_fact.append({
                "fact": fact,
                "label": "absent",
                "rationale": "Judge did not return a label for this fact.",
            })
            scores.append(0.0)
            continue
        label = str(j.get("label", "absent")).strip().lower()
        if label not in LABEL_TO_SCORE:
            label = "absent"
        per_fact.append({
            "fact": fact,
            "label": label,
            "rationale": str(j.get("rationale", "")).strip(),
        })
        scores.append(LABEL_TO_SCORE[label])

    score = sum(scores) / len(scores) if scores else 0.0
    return JudgeResult(score=score, per_fact=per_fact)


# ---------------------------------------------------------------------
# Smoke test (runs only when invoked directly)
# ---------------------------------------------------------------------

if __name__ == "__main__":
    # End-to-end check: judges one tiny example and prints the result.
    # Useful as a one-shot "is my key set up correctly?" verification
    # before kicking off score_existing_runs.py over 63 questions.
    print(f"Judge model: {JUDGE_MODEL}")
    print(f"Cache dir:   {DEFAULT_CACHE_DIR}")
    print()

    result = judge_fact_recall(
        question_id="smoke_test",
        question="What four phases characterize spike transduction along spiral ganglion neurons?",
        expected_facts=[
            "postsynaptic delay",
            "peripheral process",
            "presomatic delay",
            "central process",
        ],
        answer=(
            "Spike transduction has four phases. The first is at the peripheral "
            "terminal with a delay after synaptic input, then conduction along the "
            "peripheral fiber, a delay before the soma, and finally conduction "
            "along the axon."
        ),
        use_cache=False,  # always hit the API for the smoke test
    )

    print(f"Score: {result.score:.3f}  (judge_failed={result.judge_failed})")
    for pf in result.per_fact:
        print(f"  [{pf['label']:<8}] {pf['fact']}")
        print(f"            {pf['rationale']}")