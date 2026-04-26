# NeuroRag Retrieval Evaluation

Benchmark file: `D:/Projects/NeuroRag/benchmarks/retrieval_eval_questions.jsonl`

## Summary

| Pipeline | Questions | Paper Hit@1 | Paper Hit@3 | Paper Hit@5 | Paper MRR | Section Questions | Section Hit@3 | Section Hit@5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v1_dense | 6 | 66.7% | 100.0% | 100.0% | 0.806 | 4 | 50.0% | 50.0% |
| v2_dense | 6 | 100.0% | 100.0% | 100.0% | 1.000 | 4 | 50.0% | 100.0% |
| v2_hybrid | 6 | 83.3% | 100.0% | 100.0% | 0.889 | 4 | 25.0% | 75.0% |

## Per-Question Paper Match Rank

| Question ID | Question | v1_dense | v2_dense | v2_hybrid |
|---|---|---:|---:|---:|
| q001_hcn_camp_modulation | How does cAMP modulate HCN channels? | 2 | 1 | 3 |
| q002_hcn_fastest_isoform | Which HCN subunit has the fastest activation kinetics? | 3 | 1 | 1 |
| q003_sgn_myelin_delay | How does lack of myelin affect spike conduction in human spiral ganglion neurons? | 1 | 1 | 1 |
| q004_ribbon_synapse_currents | What do strong ribbon synapse currents do to type I spiral ganglion neuron spiking? | 1 | 1 | 1 |
| q005_hcn_expression_cochlea | What does the Luque 2020 paper investigate about HCN channels in the mammalian cochlea? | 1 | 1 | 1 |
| q006_calcium_hcn_persistent_activity | In the multiscale neocortex model, what does calcium regulation of HCN channels support? | 1 | 1 | 1 |
