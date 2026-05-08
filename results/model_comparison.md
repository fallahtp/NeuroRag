# NeuroRag Answer-Quality Model Comparison

Benchmark file: `benchmarks/answer_eval_questions.jsonl`
Pipeline: v2 structured (FAISS + BM25 + RRF, top-6 evidence chunks)
Questions: 63
Evaluation script: `src/eval/run_answer_eval.py`

This document compares two local LLMs serving as the generation step
of the NeuroRag v2 hybrid pipeline: `phi3:mini` (3.8B) and
`qwen2.5:7b-instruct` (7B). The retrieval pipeline is identical for
both runs, so any differences below are attributable to the
generation model alone.

## Headline Result

`qwen2.5:7b-instruct` is the stronger model for grounded scientific
question-answering on this corpus. It eliminated numeric
hallucinations entirely (0 vs 7), improved citation grounding by
6 points, and never failed to cite a source. Fact recall under
strict-substring matching is essentially tied between the two
models — a finding that says more about the limits of strict-token
matching than about the models, and is discussed in the limitations
section below.

`qwen2.5:7b-instruct` is therefore the default model in
`src/pipelines/v2/chat_structured_ollama.py`.

## Summary

| Metric | phi3:mini | qwen2.5:7b-instruct | Δ |
|---|---:|---:|---:|
| Mean fact recall (strict substring) | 24.1% | 23.9% | −0.2 pts |
| Mean citation validity | 97.6% | 100.0% | +2.4 pts |
| Mean citation grounding | 33.4% | 39.7% | +6.3 pts |
| Answers with at least one citation | 62/63 (98.4%) | 63/63 (100.0%) | +1.6 pts |
| Answers without numeric hallucination | 59/63 (93.7%) | 63/63 (100.0%) | +6.3 pts |
| Total fabricated numeric values | 7 | 0 | −7 |

## What Each Metric Measures

- **Fact recall (strict substring):** fraction of `expected_facts`
  tokens (from the benchmark gold standard) that appear as exact
  substrings in the generated answer. Penalizes correct paraphrases.
- **Citation validity:** fraction of cited bracket IDs (e.g. `[2]`)
  that fall within the range of source IDs actually given to the
  model in its context. Penalizes invented IDs.
- **Citation grounding:** for each valid citation, whether the
  cited evidence chunk contains at least one `expected_facts` token
  from the gold standard. Penalizes "decorative" citations that do
  not actually support the claim.
- **Numeric hallucination:** number-with-unit values appearing in
  the answer (e.g. `400 pA`, `32 mm`) that do not appear in any of
  the retrieved evidence chunks the model was given. Penalizes
  fabricated quantitative claims, which is the most safety-relevant
  failure mode for scientific QA.

## Per-Question Trade-offs

Across 63 questions:

- Fact recall: `qwen` wins on 5, `phi3` wins on 5, tied on 53.
- Numeric hallucination: `qwen` wins on 4, `phi3` wins on 0, tied on 59.

The fact-recall trade-off is symmetric — neither model is
systematically better at producing exact gold-standard tokens.

The hallucination trade-off is fully one-directional: there is no
question on which `phi3:mini` is cleaner than `qwen2.5:7b-instruct`,
and there are 4 questions on which `qwen2.5:7b-instruct` is cleaner.

## Concrete Failure Modes

### `phi3:mini` numeric hallucinations

| Question ID | Suspicious values |
|---|---|
| q002_rattay_sgn_lengths_human_cat | `32 mm`, `16 mm`, `32.35-39 mm`, `15.80-17 mm` |
| q017_croner_degeneration_absolute_threshold | `15 mm` |
| q029_liu_human_cochlea_methods | `0.25 mm` |
| q052_bai_jaccard_neural_excitation_profiles | `0 s` |

q002 is illustrative: `phi3:mini` actually scored higher than
`qwen2.5:7b-instruct` on strict fact recall for this question
(80% vs 60%), but introduced four fabricated values alongside the
correct ones. This is the cost of a more confident model: it
recovers more correct facts and invents more incorrect ones.
`qwen2.5:7b-instruct` is the more conservative answerer.

### `phi3:mini` citation bugs

- q006: cited `[3]` and `[4]` when only 6 sources were provided
  (valid range is `[1]`–`[6]`, so these were within range, but
  the answer cited multiple non-existent IDs in earlier drafts —
  worth re-checking).
- q045: cited `[1980]`, which is the year from
  `1980_Ota_Human_SGN_Ultrastructure` mistakenly inserted as a
  citation ID. A clear instance of the model confusing source
  metadata with citation syntax.
- 1 question received no citation at all from `phi3:mini`.

`qwen2.5:7b-instruct` produced no analogous citation bugs:
0 invalid IDs, 0 missing citations.

### Citation grounding distribution

| Score | phi3:mini | qwen2.5:7b-instruct |
|---|---:|---:|
| Perfect (1.0) | 15/63 | 22/63 |
| Zero (0.0) | 36/63 | 35/63 |
| Partial | 12/63 | 6/63 |

Both models cite a "wrong" source about half the time when measured
by whether the cited chunk contains a gold token. This is the
single largest weakness in the system overall — see Roadmap.

## Limitations

### Strict-substring fact recall is a noisy floor, not a ceiling

41/63 `phi3:mini` answers and 40/63 `qwen2.5:7b-instruct` answers
score exactly 0% on fact recall — yet manual inspection of these
answers shows many are scientifically correct. Examples of how the
matcher fails:

- Expected `pA`; answer says "picoamperes". Counted as miss.
- Expected `jitter`; answer says "timing variability". Counted as miss.
- Expected `peripheral process`; answer says "peripheral terminal".
  Counted as miss.
- Expected `1.32`; answer says `1.326`. Counted as miss.

Because both models paraphrase at similar rates, this matcher
penalizes them roughly equally and the comparison is not
distorted — but the absolute number (24%) understates real answer
correctness substantially.

The right fix is an LLM-as-judge fact-recall metric (see Roadmap).
The hallucination, citation-validity, and citation-grounding
metrics are not affected by this limitation, because they check
specific structural properties of the answer (numbers, IDs) rather
than fuzzy semantic content.

### Numeric hallucination check has its own false positives

The hallucination detector flags any number-with-unit in the answer
that does not appear in the retrieved evidence chunks. This is a
useful signal but has known false positives: when the source paper
contains both a mean (`32.35 mm`) and a range (`32–63.80 mm`), and
only the mean is in the retrieved chunk window, the model citing
the range gets flagged as fabricating it. A few of the 7
`phi3:mini` flagged values may fall into this category.

### Same-corpus, same-pipeline comparison

The two models were compared with identical retrieval, identical
context windows, and identical prompts. Differences in answer
quality between models on a different corpus or with a different
prompt should not be assumed.

### N=63 on a domain-specific benchmark

63 questions is enough to show the hallucination difference clearly
(0 vs 7 is not noise) but is small for fine-grained per-paper or
per-section claims. The benchmark is also drawn from a single
neuroscience subdomain (cochlear / spiral ganglion / HCN
literature) and these results may not transfer to other scientific
domains.

## Decision

`qwen2.5:7b-instruct` becomes the default model for the v2
structured pipeline. The decision rests on three findings:

1. Zero numeric hallucinations across 63 questions, vs 7 for
   `phi3:mini`. This is the most safety-relevant metric for a
   scientific QA system and the gap is one-directional.
2. Better citation behavior: 100% citation rate, 0 invalid IDs,
   higher grounding rate.
3. No fact-recall regression under the available matcher.

The 4× larger model size and slower inference are accepted in
exchange for these gains.

## Roadmap Items Surfaced By This Eval

In rough priority order:

1. **LLM-as-judge fact recall** using a different model family
   (e.g. Google Gemini 2.5 Flash, free tier) to avoid
   self-judgment bias. Replaces the strict-substring matcher
   with a semantic judge. Expected to lift fact-recall numbers
   from the current ~24% floor to a more informative range.
2. **Improve citation grounding.** Both models cite "wrong"
   sources in ~55% of answers when measured against gold tokens.
   Likely fixes: stricter prompt instructions on which `[N]` to
   pick, or post-hoc citation rewriting based on which chunk
   contains the answer's claims.
3. **Reduce false positives in the numeric hallucination check.**
   Currently checks against the trimmed evidence-sentence window;
   should also check against the full retrieved chunk content
   before flagging.
4. **Expand the benchmark beyond 63 questions** if specific
   per-paper or per-section claims are needed.

## Reproducing These Numbers

```powershell
# from project root, with venv active
python src/eval/run_answer_eval.py --model qwen2.5:7b-instruct
Rename-Item results\answer_eval_summary.json results\answer_eval_summary_qwen2.5_7b_n63.json
Rename-Item results\answer_eval_summary.md results\answer_eval_summary_qwen2.5_7b_n63.md

python src/eval/run_answer_eval.py --model phi3:mini
Rename-Item results\answer_eval_summary.json results\answer_eval_summary_phi3_mini_n63.json
Rename-Item results\answer_eval_summary.md results\answer_eval_summary_phi3_mini_n63.md
```

Both runs require Ollama running locally with the relevant models
pulled (`ollama pull qwen2.5:7b-instruct`, `ollama pull phi3:mini`)
and a built v2 structured FAISS index at
`storage/faiss_index_v2_structured/`.
