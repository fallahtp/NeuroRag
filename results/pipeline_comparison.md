# Pipeline Comparison — v2 Hybrid vs v3 Reranked

We built two retrieval pipelines on top of the same structured FAISS index and benchmarked them on the same 63-question neuroscience set with the same generator (`qwen2.5:7b-instruct` via Ollama). This doc explains what changed between the two pipelines, what we measured, and what we found.

The model is held constant. The only difference is what happens between candidate retrieval and the generator's prompt.

## What's different between v2 and v3

**v2 hybrid** runs dense retrieval (FAISS over MiniLM embeddings) and lexical retrieval (BM25) in parallel, fuses them with Reciprocal Rank Fusion, applies a per-paper diversity cap (≤2 chunks per paper), and feeds the top 6 chunks to the generator.

**v3 reranked** adds one stage: between fusion and the diversity cap, we score the top 16 fused candidates with a `cross-encoder/ms-marco-MiniLM-L-6-v2` cross-encoder against the query, sort by that score, and *then* apply the diversity cap. The cross-encoder sees the full query–document pair (unlike bi-encoder retrieval, which embeds them separately), so it can catch matches the dense + BM25 fusion ranks too low.

Putting the rerank *before* the diversity cap matters: if the cap ran first, the cross-encoder would never see chunks 3+ from the strongest paper, and we'd lose cases where the best chunk for the question wasn't the bi-encoder's favourite. After-cap rerank also keeps the implementation consistent with our retrieval-only eval harness.

## Methodology

For each pipeline we ran the same end-to-end loop per question: retrieve → build prompt → generate answer → score the answer on four axes. The first pipeline took ~25 minutes wall time, the second ~30 (the cross-encoder adds maybe 30 seconds total over 63 questions).

We score on four signals:

- **Fact recall (strict)** — substring match of expected facts in the answer. Originally our only fact-recall metric; we keep it for transparency and because it shows the systematic bias the LLM judge later corrects.
- **Fact recall (LLM-judged)** — `gemini-2.5-flash` labels each expected fact `present` / `partial` / `absent` against the answer, mapped to 1.0 / 0.5 / 0.0 and averaged. The judge belongs to a different model family from both generators we tested, which mitigates self-judgment bias.
- **Citation validity** — deterministic check that every `[n]` cited by the generator is in range.
- **Citation grounding** — deterministic substring check that the cited chunks actually contain the expected facts. This metric has no LLM in the loop and is the most trustworthy signal we have.

All metrics use the same 63 benchmark questions with hand-written expected facts.

## Headline results

| Metric | v2 hybrid | v3 reranked | Δ |
|---|---:|---:|---:|
| Fact recall (strict) | 23.9% | 27.0% | **+3.1pp** |
| Fact recall (judge) | 33.8% | 38.7% | **+4.9pp** |
| Citation grounding | 39.7% | 43.7% | **+4.0pp** |
| Citation validity | 100.0% | 99.2% | -0.8pp |
| Numeric hallucinations | 0 | 0 | — |
| Judge failures (re-scored) | 0/63 | 0/63 | — |

Citation grounding moved by +4pp without an LLM anywhere in the metric. We treat that as the strongest evidence the v3 pipeline is genuinely surfacing better evidence chunks, not just generating more agreeable text.

## Where v3 wins, where v3 loses

We can't summarise the per-question deltas honestly with averages alone. Out of 63 questions:

- v3 scored **higher** on 17
- v3 scored **lower** on 14
- v3 **tied** v2 on 32 (of which 14 are both 0%)

Reranking is a *re-ordering* — it can demote a useful chunk into 7th place as easily as it can promote one into 1st. Below are the questions where v3's re-ordering swung the answer score by ≥20 percentage points in either direction.

### Big wins (v3 ≥ +20pp)

| ID | Question | v2 → v3 |
|---|---|---:|
| q015_potrusil_two_step_modeling_framework | What two-step computational framework did Potrusil use to model cochlear implant stimulation? | 0% → 100% |
| q016_potrusil_low_frequency_tonotopic_order | What did the Potrusil model show about tonotopic stimulation order in the apical region? | 0% → 100% |
| q012_accili_hcn_ionic_properties | What ionic selectivity and blocking properties are described for cloned HCN channels in the Accili review? | 33% → 100% |
| q059_fellner_comsol_framework_physics | What simulation environment + physics did Fellner use to model extracellular stimulation? | 0% → 67% |
| q028_smith_node_geometry_model_conduction_speed | How did node-geometry modelling affect conduction speed predictions? | 14% → 50% |
| q010_luque_hcn2_hcn4_coexpression | Which HCN subunit pair showed the strongest co-expression in SGNs? | 67% → 100% |
| q047_ota_age_related_myelinated_large_neurons | How did age affect myelinated large-neuron counts in the Ota human-cochlea TEM study? | 33% → 58% |
| q001_rattay_sgn_signal_transduction_phases | What four phases characterise spike transduction along SGNs? | 50% → 75% |
| q033_liu_discussion_spike_generation_ci | What does Liu's discussion say about spike generation in cochlear-implant stimulation? | 0% → 20% |

The two cleanest cases are q015 and q016, both about Potrusil's two-step modelling paper. v1 (dense retrieval only) **missed this paper entirely** on these questions. v2 hybrid found it but interleaved it with other FEM-modelling papers. v3 promoted both Potrusil chunks to ranks 1 and 2 — placing them adjacent in the prompt so the generator could synthesise from them coherently. With strong evidence at the top of the prompt, the answer locked onto the right facts.

### Honest losses (v3 ≤ -20pp)

| ID | Question | v2 → v3 |
|---|---|---:|
| q009_luque_hcn_aging_thresholds | Did age-related HCN expression changes correlate with hearing thresholds? | 100% → 33% |
| q048_ota_discussion_fiber_distribution_function | How does Ota's discussion link fibre distribution to function? | 67% → 17% |
| q003_rattay_type_i_process_diameters | What were the mean peripheral and central process diameters of type I SGNs? | 67% → 33% |
| q005_rattay_ribbon_synapse_currents_jitter | How did strong postsynaptic currents affect spike initiation and synchrony? | 75% → 50% |
| q027_smith_location_specific_node_geometry_p20 | How did node-of-Ranvier geometry vary with cochlear location at P20? | 44% → 19% |

q009 is the headline regression. Looking at what changed: v2 retrieved the abstract section of the Luque HCN paper, where the no-correlation finding is stated plainly. v3's reranker promoted a more technical methods chunk that discusses HCN-channel measurements without re-stating the headline conclusion. The generator then hedged. The reranker isn't wrong to think the methods chunk is "more relevant" to the literal question text — it just doesn't know that the abstract is where the punchline is.

We could mitigate this by either (a) always including the abstract chunk in the candidate pool, or (b) training a domain-tuned reranker. Both are tractable but neither is on today's path.

## Why the strict and judge metrics disagree

The judge gives v3 a +4.9pp lift on fact recall; strict gives it +3.1pp. The gap exists because v3 surfaces better evidence, and a better-evidenced answer paraphrases more naturally. Strict matching penalises paraphrases as misses; the judge labels them present.

A concrete example. **q001** asks for the four phases of SGN spike transduction. v3 + qwen2.5 produced:

> The four phases are: (i) postsynaptic delay t1, (ii) conduction in the peripheral process with velocity v1, (iii) a subsequent significant delay due to the large soma capacitance loading via axial current flow, (iv) conduction along the axon.

The expected facts are `postsynaptic delay`, `peripheral process`, `presomatic delay`, `central process`. Strict matching scores this 25% — three of the four facts are paraphrased rather than verbatim. The judge labels it 75%: `postsynaptic delay` and `peripheral process` are stated directly, `presomatic delay` is correctly described as "delay due to the large soma capacitance", and only `central process` (answered as "axon") is flagged absent — the judge is conservative about whether "axon" counts as the same concept when the rubric asks for the specific anatomical name.

This is the exact bias we built the judge to expose. The judge isn't softer than strict matching — it judges each of the same expected facts independently, and it disagrees with strict about three of them. If the judge said "this answer is broadly correct, give it 75%" we'd distrust the metric. It doesn't. It marks specific facts as `present` with specific quoted evidence from the answer.

## What the judge can't fix

The judge improves recall scoring, but it doesn't change retrieval. If the right chunk isn't in the prompt, no amount of judge generosity recovers the answer.

The block of consistently zero-scoring questions (q021–q058, mostly) reflects this. v3 helped some of them — q028 went 14% → 50%, q046 stayed at 60%, q053 went 33% → 50%. But for many, both v2 and v3 retrieve content that's *related* to the question but doesn't contain the specific facts our rubric asks for. The next set of improvements has to come from better section-aware chunking, table/figure extraction, or query reformulation — not from re-scoring the same retrieval.

## Score distribution shift

| Bucket | phi3 v2 | qwen2.5 v2 | qwen2.5 v3 |
|---|---:|---:|---:|
| 0% (judge gave nothing) | 18 | 21 | **15** |
| 1–33% | 23 | 20 | 23 |
| 34–66% | 12 | 12 | 12 |
| 67–99% | 0 | 1 | 1 |
| 100% (judge full credit) | 10 | 9 | **12** |

Both ends improved with v3. Six questions moved out of the 0% bucket; three more questions reached the 100% bucket. The middle stayed roughly stable. This is the shape we'd expect from "better retrieval makes hard questions tractable and makes easy questions complete."

## Conclusion

v3 reranking is a net positive on every aggregate metric. It is not strictly dominant per-question — 14 questions regress — and the regressions are real, not measurement noise. We'd choose v3 over v2 for the default pipeline, accepting that some questions get worse, because the average improvement plus the cleaner score distribution outweigh the few losses, and because citation grounding (the most trustworthy signal) improves alongside fact recall rather than diverging from it.

The biggest remaining bottleneck is retrieval coverage on questions whose evidence isn't well represented in any chunk we currently produce. That's a chunking and parsing problem, not a ranking problem, and that's where we'll look next.

## Reproducing this comparison

```bash
# Run the answer-eval harness on both pipelines (≈25-30 min each)
python src/eval/run_answer_eval.py --pipeline v2_hybrid \
  --output-basename answer_eval_summary_qwen2_5_7b_v2hybrid_n63
python src/eval/run_answer_eval.py --pipeline v3_reranked \
  --output-basename answer_eval_summary_qwen2_5_7b_v3reranked_n63

# Re-score both with the Gemini judge (≈8 min each, cached after first run)
python src/eval/score_existing_runs.py \
  results/answer_eval_summary_qwen2_5_7b_v2hybrid_n63.json
python src/eval/score_existing_runs.py \
  results/answer_eval_summary_qwen2_5_7b_v3reranked_n63.json
```

Inputs: 63 benchmark questions in `benchmarks/answer_eval_questions.jsonl`. Generator: `qwen2.5:7b-instruct`. Judge: `gemini-2.5-flash`. Both judge and reranker are cached on disk, so reruns are near-free.
