# NeuroRag Retrieval Evaluation

Benchmark file: `D:/Projects/NeuroRag/benchmarks/retrieval_eval_questions.jsonl`

## Summary

| Pipeline | Questions | Paper Hit@1 | Paper Hit@3 | Paper Hit@5 | Paper MRR | Section Questions | Section Hit@3 | Section Hit@5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v1_dense | 20 | 85.0% | 90.0% | 90.0% | 0.867 | 20 | 85.0% | 85.0% |
| v2_dense | 20 | 100.0% | 100.0% | 100.0% | 1.000 | 20 | 100.0% | 100.0% |
| v2_hybrid | 20 | 100.0% | 100.0% | 100.0% | 1.000 | 20 | 95.0% | 95.0% |

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

## Per-Question Section Match Rank

Section rank is calculated only for benchmark items with `expected_section_keywords`.

| Question ID | Question | v1_dense | v2_dense | v2_hybrid |
|---|---|---:|---:|---:|
| q001_rattay_sgn_signal_transduction_phases | What four phases characterize spike transduction along spiral ganglion neurons? | miss | 1 | 1 |
| q002_rattay_sgn_lengths_human_cat | How do spiral ganglion neuron lengths compare between humans and cats? | 3 | 1 | 1 |
| q003_rattay_type_i_process_diameters | What were the mean peripheral and central process diameters of type I spiral ganglion neurons in humans and cats? | 1 | 1 | 1 |
| q004_rattay_soma_myelination_cat_human | How did myelination of type I spiral ganglion neuron somata differ between cats and humans? | 1 | 1 | 1 |
| q005_rattay_ribbon_synapse_currents_jitter | How did strong postsynaptic currents from inner hair cell ribbon synapses affect spike initiation and synchrony in type I spiral ganglion neurons? | 3 | 1 | miss |
| q006_luque_hcn1_localization_type_i_sgn | What was the main subcellular localization pattern of HCN1 in adult mammalian type I spiral ganglion neurons? | 2 | 1 | 1 |
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
| q017_croner_degeneration_absolute_threshold | How did dendritic degeneration affect absolute electrical excitation thresholds in the Croner high-resolution human SGN model? | 2 | 2 | 3 |
| q018_croner_pitch_degenerative_state | How did the Croner model reconstruct pitch and analyze pitch differences across degenerative states? | 1 | 1 | 1 |
| q019_recugnat_hcn_klt_spike_rate_adaptation | What effect did adding HCN and KLT channels have on spike-rate adaptation in the Recugnat human-shaped SGN model? | 1 | 1 | 1 |
| q020_smith_node_geometry_spike_timing | How did developmental changes in node of Ranvier geometry affect spike timing maturation in primary auditory afferents? | 1 | 1 | 1 |

## Weak Case Analysis

A weak case means the expected paper or section was not found in the top 3 results. Some weak cases may still count as Hit@5.

### v1_dense

#### Paper-level weak cases

| Question ID | Paper Rank | Expected Paper | Likely Issue | Top Retrieved Results |
|---|---:|---|---|---|
| q015_potrusil_two_step_modeling_framework | miss | 2020_Potrusil_FEM_Modeling | Expected paper was not retrieved in top-k. | 1. `2022_Recugnat_SGN_SpikeRate_Adaptation_Model` - (no section)<br>2. `2022_Recugnat_SGN_SpikeRate_Adaptation_Model` - (no section)<br>3. `2025_Bai_HighResolution_HumanCochlea_Model` - (no section)<br>4. `2025_Bai_HighResolution_HumanCochlea_Model` - (no section)<br>5. `2022_Fellner_FEM_Extracellular_Stimulation` - (no section) |
| q016_potrusil_low_frequency_tonotopic_order | miss | 2020_Potrusil_FEM_Modeling | Expected paper was not retrieved in top-k. | 1. `2022_Croner_SGN_Degeneration_Excitation_Model` - (no section)<br>2. `2022_Croner_SGN_Degeneration_Excitation_Model` - (no section)<br>3. `2025_Bai_HighResolution_HumanCochlea_Model` - (no section)<br>4. `2022_Croner_SGN_Degeneration_Excitation_Model` - (no section)<br>5. `2005_Glueckert_Human_SGN_Ultrastructure_Survival_CI` - (no section) |

#### Section-level weak cases

| Question ID | Paper Rank | Section Rank | Expected Section Keywords | Likely Issue | Top Retrieved Results |
|---|---:|---:|---|---|---|
| q001_rattay_sgn_signal_transduction_phases | 1 | miss | Four phases in SGN signal transduction<br>postsynaptic delay<br>presomatic delay<br>central process | Expected paper was retrieved, but expected section/keyword was not found in top-k. | 1. `2013_Rattay_SGN_Morphometry_Myelination_Conduction` - (no section)<br>2. `2013_Rattay_SGN_Morphometry_Myelination_Conduction` - (no section)<br>3. `2020_Luqle_HCN_Expression_Cochlea` - (no section)<br>4. `1980_Ota_Human_SGN_Ultrastructure` - (no section)<br>5. `2013_Rattay_SGN_Morphometry_Myelination_Conduction` - (no section) |
| q015_potrusil_two_step_modeling_framework | miss | miss | Computational modeling and simulation<br>Computational modeling of SGN stimulation<br>two-step procedure<br>finite element method<br>multi-compartment model<br>electrical potential distribution | Expected paper was not retrieved in top-k. | 1. `2022_Recugnat_SGN_SpikeRate_Adaptation_Model` - (no section)<br>2. `2022_Recugnat_SGN_SpikeRate_Adaptation_Model` - (no section)<br>3. `2025_Bai_HighResolution_HumanCochlea_Model` - (no section)<br>4. `2025_Bai_HighResolution_HumanCochlea_Model` - (no section)<br>5. `2022_Fellner_FEM_Extracellular_Stimulation` - (no section) |
| q016_potrusil_low_frequency_tonotopic_order | miss | miss | Loss of the tonotopical stimulation order<br>low frequency region<br>simultaneous activation | Expected paper was not retrieved in top-k. | 1. `2022_Croner_SGN_Degeneration_Excitation_Model` - (no section)<br>2. `2022_Croner_SGN_Degeneration_Excitation_Model` - (no section)<br>3. `2025_Bai_HighResolution_HumanCochlea_Model` - (no section)<br>4. `2022_Croner_SGN_Degeneration_Excitation_Model` - (no section)<br>5. `2005_Glueckert_Human_SGN_Ultrastructure_Survival_CI` - (no section) |

### v2_dense

No weak cases at Hit@3.

### v2_hybrid

#### Paper-level weak cases

No paper-level weak cases at Hit@3.

#### Section-level weak cases

| Question ID | Paper Rank | Section Rank | Expected Section Keywords | Likely Issue | Top Retrieved Results |
|---|---:|---:|---|---|---|
| q005_rattay_ribbon_synapse_currents_jitter | 1 | miss | Jitter and AP delay<br>Synaptic hair cell currents<br>ribbon synapses<br>400 pA<br>15 times | Expected paper was retrieved, but expected section/keyword was not found in top-k. | 1. `2013_Rattay_SGN_Morphometry_Myelination_Conduction` - Abstract<br>2. `2013_Rattay_SGN_Morphometry_Myelination_Conduction` - Four phases in SGN signal transduction<br>3. `2020_Luqle_HCN_Expression_Cochlea` - \| HCN channels at the peripheral nerve endings<br>4. `2015_Liu_Human_TypeI_SGN_PrePostSomatic_Segments` - DISCUSSION<br>5. `2015_Liu_Human_TypeI_SGN_PrePostSomatic_Segments` - Abstract |
