# Model Comparison — phi3:mini vs qwen2.5:7b-instruct

We compared two locally-runnable generators on top of the same v2 hybrid retrieval pipeline: `phi3:mini` (the original baseline) and `qwen2.5:7b-instruct`. Same retrieval, same prompts, same 63 benchmark questions, same scoring.

This doc was originally written using only strict-substring fact-recall scoring. We later added an LLM-as-judge (`gemini-2.5-flash`, different model family from both candidates) and re-scored both runs. The updated tables below show both metrics.

## Headline

| Metric | phi3:mini | qwen2.5:7b-instruct |
|---|---:|---:|
| Fact recall (strict) | 24.1% | 23.9% |
| **Fact recall (LLM judge)** | **34.8%** | **33.8%** |
| Citation validity | 97.6% | 100.0% |
| Citation grounding | 33.4% | 39.7% |
| Answers with citations | 62/63 | 63/63 |
| **Numeric hallucinations** | **7** | **0** |
| Clean answers (no halluc nums) | 59/63 | 63/63 |

On fact recall alone, the two models are essentially tied (within 1pp on both metrics — within measurement noise for a 63-question benchmark). The decisive separator is **honesty under uncertainty**, where qwen2.5 is decisively better: 7 numeric hallucinations vs 0.

## Why qwen2.5 wins despite the tied fact-recall

The fact-recall numbers tell us how often a model states the right facts when the retrieved context contains them. They don't tell us how often a model fabricates facts when the context *doesn't* contain them.

That's what the numeric-hallucination check measures. We extract every number-with-unit from the answer (e.g. "1.32 µm", "400 pA", "32.35 mm") and verify each appears verbatim in the retrieved context. A number that doesn't is flagged as suspicious.

| Hallucination axis | phi3:mini | qwen2.5:7b-instruct |
|---|---:|---:|
| Answers with suspicious numbers | 4/63 | 0/63 |
| Total suspicious numbers across all answers | 7 | 0 |

phi3 invented numbers in 4 out of 63 answers — confident-sounding measurements that weren't actually in the source material. For a research assistant, this is the worst kind of error: it's invisible to a reader who trusts the citations.

qwen2.5 went the other way. When it didn't have the answer, it said so. The system prompt instructs both models to write "I do not have enough evidence in the retrieved context to answer confidently" rather than guess; qwen2.5 actually follows that instruction. phi3 sometimes hedges with a number that sounds plausible.

For a portfolio of question types where the cost of confident-wrong is higher than the cost of "I don't know" (which is what most research-assistant use cases look like), qwen2.5 is the clear pick.

## Strict vs judge

Both models gained roughly the same amount when we replaced strict substring matching with the LLM judge: +10.8pp for phi3, +9.9pp for qwen2.5. The gap is real (the strict metric undercounts paraphrases) but it doesn't change the ordering of the two models — they remain ~tied on fact recall under both metrics.

This is what we'd hope to see from a fair metric upgrade. If the judge had flipped the ordering, we'd have to wonder whether the judge was biased toward one model's writing style. The fact that the gap is consistent across both models means the bias the judge corrects is **in the metric**, not in the generators.

## Per-question agreement

On the 63 questions:

- **qwen2.5 scored higher on 16** (judge metric)
- **phi3 scored higher on 14**
- **Tied on 33**

This is closer to a coin flip than the headline averages might suggest. The averages are within 1pp because the per-question pattern is noisy with no systematic preference. The model-selection signal isn't in averages — it's in the hallucination column.

## Other dimensions worth noting

**Citation grounding** (deterministic check that cited chunks actually contain expected facts): qwen2.5 wins 39.7% vs 33.4%. This isn't because qwen2.5 retrieves differently — retrieval is held constant — it's because qwen2.5 cites more consistently when its claims are supported by the chunk, and avoids citing chunks that don't support its claims. This compounds with the hallucination advantage: qwen2.5 doesn't just refrain from making things up, it cites correctly when it doesn't.

**Coverage** (answers with at least one citation): qwen2.5 produced a citation on 63/63 questions; phi3 missed citations on 1 question. Small but consistent.

**Citation validity** (do cited `[n]` IDs fall in the valid range?): both models are near-perfect, with phi3 producing one out-of-range `[n]` and qwen2.5 producing none. We track this because off-by-one citation errors are a common LLM failure; both models handle this fine.

## Conclusion

If the only metric were fact recall, we'd call this a tie. Hallucination resistance breaks the tie decisively in qwen2.5's favour, and citation grounding reinforces it. We chose qwen2.5:7b-instruct as the default generator for NeuroRag v2 onward.

phi3 isn't a bad model — it's small (3.8B parameters vs qwen2.5's 7B), fast, and gets the easy questions right. For users with tight VRAM constraints, it's a defensible fallback. But for grounded scientific QA where invented numbers are catastrophic, qwen2.5 is the right choice.

## Reproducing this comparison

```bash
# Run both models on the v2 hybrid pipeline (≈25 min each)
python src/eval/run_answer_eval.py --pipeline v2_hybrid --model phi3:mini \
  --output-basename answer_eval_summary_phi3_mini_v2hybrid_n63
python src/eval/run_answer_eval.py --pipeline v2_hybrid --model qwen2.5:7b-instruct \
  --output-basename answer_eval_summary_qwen2_5_7b_v2hybrid_n63

# Add the LLM judge to both runs (≈8 min each, cached after first run)
python src/eval/score_existing_runs.py \
  results/answer_eval_summary_phi3_mini_v2hybrid_n63.json
python src/eval/score_existing_runs.py \
  results/answer_eval_summary_qwen2_5_7b_v2hybrid_n63.json
```

Inputs: 63 benchmark questions in `benchmarks/answer_eval_questions.jsonl`. Retrieval: v2 hybrid (FAISS + BM25 + RRF + per-paper diversity cap). Judge: `gemini-2.5-flash`. Both models run via Ollama; the judge runs against the Gemini API.
