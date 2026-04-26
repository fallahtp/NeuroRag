# NeuroRag Retrieval Evaluation

Benchmark file: `D:/Projects/NeuroRag/benchmarks/retrieval_eval_questions.jsonl`

## Summary

| Pipeline | Questions | Paper Hit@1 | Paper Hit@3 | Paper Hit@5 | Paper MRR | Section Questions | Section Hit@3 | Section Hit@5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v1_dense | 10 | 90.0% | 100.0% | 100.0% | 0.933 | 10 | 90.0% | 90.0% |
| v2_dense | 10 | 100.0% | 100.0% | 100.0% | 1.000 | 10 | 80.0% | 80.0% |
| v2_hybrid | 10 | 100.0% | 100.0% | 100.0% | 1.000 | 10 | 80.0% | 80.0% |

## Per-Question Paper Match Rank

| Question ID | Question | v1_dense | v2_dense | v2_hybrid |
|---|---|---:|---:|---:|
| q001_sgn_signal_transduction_phases | What four phases characterize spike transduction along spiral ganglion neurons? | 1 | 1 | 1 |
| q002_sgn_lengths_human_cat | How do spiral ganglion neuron lengths compare between humans and cats? | 3 | 1 | 1 |
| q003_sgn_process_diameters | What were the mean peripheral and central process diameters of type I spiral ganglion neurons in humans and cats? | 1 | 1 | 1 |
| q004_sgn_soma_myelination_cat_human | How did myelination of type I spiral ganglion neuron somata differ between cats and humans? | 1 | 1 | 1 |
| q005_ribbon_synapse_currents_jitter | How did strong postsynaptic currents from inner hair cell ribbon synapses affect spike initiation and synchrony in type I spiral ganglion neurons? | 1 | 1 | 1 |
| q006_hcn1_localization_type_i_sgn | What was the main subcellular localization pattern of HCN1 in adult mammalian type I spiral ganglion neurons? | 1 | 1 | 1 |
| q007_hcn3_prestin_outer_hair_cells | Which HCN subunit overlapped with prestin at the lateral membrane of outer hair cells, and in which species was this observed? | 1 | 1 | 1 |
| q008_hcn2_hcn4_postnatal_development | How did HCN2 and HCN4 expression change during mouse postnatal development in relation to hair cell innervation and hearing onset? | 1 | 1 | 1 |
| q009_hcn_aging_hearing_thresholds | Did age-related changes in HCN channel expression correlate directly with hearing thresholds in CBA/J and C57Bl/6N mice? | 1 | 1 | 1 |
| q010_hcn2_hcn4_coexpression_sgn | Which HCN subunit pair showed the strongest co-expression in spiral ganglion neurons, and what did that suggest about their relationship? | 1 | 1 | 1 |
