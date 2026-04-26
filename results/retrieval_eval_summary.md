# NeuroRag Retrieval Evaluation

Benchmark file: `D:/Projects/NeuroRag/benchmarks/retrieval_eval_questions.jsonl`

## Summary

| Pipeline | Questions | Paper Hit@1 | Paper Hit@3 | Paper Hit@5 | Paper MRR | Section Questions | Section Hit@3 | Section Hit@5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v1_dense | 20 | 85.0% | 90.0% | 90.0% | 0.867 | 20 | 85.0% | 85.0% |
| v2_dense | 20 | 100.0% | 100.0% | 100.0% | 1.000 | 20 | 85.0% | 90.0% |
| v2_hybrid | 20 | 100.0% | 100.0% | 100.0% | 1.000 | 20 | 80.0% | 80.0% |

## Per-Question Paper Match Rank

| Question ID | Question | v1_dense | v2_dense | v2_hybrid |
|---|---|---:|---:|---:|
| q001_rattay_sgn_signal_transduction_phases | What four phases characterize spike transduction along spiral ganglion neurons? | 1 | 1 | 1 |
| q002_rattay_sgn_lengths_human_cat | How do spiral ganglion neuron lengths compare between humans and cats? | 3 | 1 | 1 |
| q003_rattay_type_i_process_diameters | What were the mean peripheral and central process diameters of type I spiral ganglion neurons in humans and cats? | 1 | 1 | 1 |
| q004_rattay_soma_myelination_cat_human | How did myelination of type I spiral ganglion neuron somata differ between cats and humans? | 1 | 1 | 1 |
| q005_rattay_ribbon_synapse_currents_jitter | How did strong postsynaptic currents from inner hair cell ribbon synapses affect spike initiation and synchrony in type I spiral ganglion neurons? | 1 | 1 | 1 |
| q006_luque_hcn1_localization_type_i_sgn | What was the main subcellular localization pattern of HCN1 in adult mammalian type I spiral ganglion neurons? | 1 | 1 | 1 |
| q007_luque_hcn3_prestin_ohc | Which HCN subunit overlapped with prestin at the lateral membrane of outer hair cells, and in which species was this observed? | 1 | 1 | 1 |
| q008_luque_hcn2_hcn4_postnatal_development | How did HCN2 and HCN4 expression change during mouse postnatal development in relation to hair cell innervation and hearing onset? | 1 | 1 | 1 |
| q009_luque_hcn_aging_thresholds | Did age-related changes in HCN channel expression correlate directly with hearing thresholds in CBA/J and C57Bl/6N mice? | 1 | 1 | 1 |
| q010_luque_hcn2_hcn4_coexpression | Which HCN subunit pair showed the strongest co-expression in spiral ganglion neurons, and what did that suggest about their relationship? | 1 | 1 | 1 |
| q011_accili_hcn_isoform_kinetics | According to the Accili HCN review, how do HCN1, HCN2, and HCN4 differ in activation kinetics? | 1 | 1 | 1 |
| q012_accili_hcn_ionic_properties | What ionic selectivity and blocking properties are described for cloned HCN channels in the Accili review? | 1 | 1 | 1 |
| q013_neymotin_model_methods_neuron_rxd | What simulation environment and multiscale modeling components were used in the Neymotin calcium-HCN neocortex model? | 1 | 1 | 1 |
| q014_neymotin_free_calcium_persistent_activity | How did free cytosolic calcium regulate persistent activity in the Neymotin multiscale neocortex model? | 1 | 1 | 1 |
| q015_potrusil_two_step_modeling_framework | What two-step computational framework did Potrusil use to model cochlear implant stimulation of auditory neurons? | miss | 1 | 1 |
| q016_potrusil_low_frequency_tonotopic_order | What did the Potrusil model show about tonotopic stimulation order in the apical low-frequency cochlear region? | miss | 1 | 1 |
| q017_croner_degeneration_absolute_threshold | How did dendritic degeneration affect absolute electrical excitation thresholds in the Croner high-resolution human SGN model? | 1 | 1 | 1 |
| q018_croner_pitch_degenerative_state | How did the Croner model reconstruct pitch and analyze pitch differences across degenerative states? | 1 | 1 | 1 |
| q019_recugnat_hcn_klt_spike_rate_adaptation | What effect did adding HCN and KLT channels have on spike-rate adaptation in the Recugnat human-shaped SGN model? | 1 | 1 | 1 |
| q020_smith_node_geometry_spike_timing | How did developmental changes in node of Ranvier geometry affect spike timing maturation in primary auditory afferents? | 1 | 1 | 1 |
