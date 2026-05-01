# NeuroRag Answer Evaluation

Benchmark file: `D:/Projects/NeuroRag/benchmarks/answer_eval_questions.jsonl`
Model: `qwen2.5:7b-instruct`

## Summary

| Metric | Value |
|---|---:|
| Questions | 20 |
| Mean fact recall | 72.4% |
| Mean citation validity | 100.0% |
| Mean citation grounding | 87.5% |
| Answers with citations | 20/20 (100.0%) |
| Answers without numeric hallucination | 19/20 (95.0%) |
| Total suspicious numbers across all answers | 2 |

## Per-Question Detail

| ID | Fact Recall | Cite Valid | Cite Ground | Susp. Nums | Missed Facts |
|---|---:|---:|---:|---:|---|
| q001_rattay_sgn_signal_transduction_phases | 0.0% | 100.0% | 50.0% | 0 | postsynaptic delay, peripheral process, presomatic delay, central process |
| q002_rattay_sgn_lengths_human_cat | 60.0% | 100.0% | 100.0% | 2 | 32.35, 15.81 |
| q003_rattay_type_i_process_diameters | 83.3% | 100.0% | 100.0% | 0 | 2.65 |
| q004_rattay_soma_myelination_cat_human | 80.0% | 100.0% | 100.0% | 0 | 3.65 |
| q005_rattay_ribbon_synapse_currents_jitter | 25.0% | 100.0% | 100.0% | 0 | 400, pA, jitter |
| q006_luque_hcn1_localization_type_i_sgn | 66.7% | 100.0% | 50.0% | 0 | perisomatic |
| q007_luque_hcn3_prestin_ohc | 100.0% | 100.0% | 100.0% | 0 | - |
| q008_luque_hcn2_hcn4_postnatal_development | 66.7% | 100.0% | 100.0% | 0 | hearing onset |
| q009_luque_hcn_aging_thresholds | 66.7% | 100.0% | 100.0% | 0 | no direct |
| q010_luque_hcn2_hcn4_coexpression | 66.7% | 100.0% | 100.0% | 0 | HCN4 |
| q011_accili_hcn_isoform_kinetics | 100.0% | 100.0% | 100.0% | 0 | - |
| q012_accili_hcn_ionic_properties | 100.0% | 100.0% | 100.0% | 0 | - |
| q013_neymotin_model_methods_neuron_rxd | 33.3% | 100.0% | 0.0% | 0 | RxD, NMODL |
| q014_neymotin_free_calcium_persistent_activity | 66.7% | 100.0% | 100.0% | 0 | extrusion |
| q015_potrusil_two_step_modeling_framework | 33.3% | 100.0% | 50.0% | 0 | finite element, multi-compartment |
| q016_potrusil_low_frequency_tonotopic_order | 100.0% | 100.0% | 100.0% | 0 | - |
| q017_croner_degeneration_absolute_threshold | 100.0% | 100.0% | 100.0% | 0 | - |
| q018_croner_pitch_degenerative_state | 100.0% | 100.0% | 100.0% | 0 | - |
| q019_recugnat_hcn_klt_spike_rate_adaptation | 100.0% | 100.0% | 100.0% | 0 | - |
| q020_smith_node_geometry_spike_timing | 100.0% | 100.0% | 100.0% | 0 | - |

## Failure Cases

### q001_rattay_sgn_signal_transduction_phases

**Question:** What four phases characterize spike transduction along spiral ganglion neurons?

**Answer:**

```
Answer:
Spike transduction along spiral ganglion neurons (SGNs) can be divided into four characteristic phases. These are spike initiation at the peripheral terminal and a delay caused by either natural synaptic activation or exogenous current injection, followed by a significant delay due to the large soma capacitance that needs to be loaded via axial current flow.

Evidence summary:
The context provided mentions four phases in SGN signal transduction, detailing the initiation of spikes at the peripheral terminal and the delays associated with somatic spike generation.

Source IDs:
[1], [2]
```

- Fact recall: 0.0% (missed: postsynaptic delay, peripheral process, presomatic delay, central process)
- Citation validity: 100.0%
- Citation grounding: 50.0%
- Suspicious numbers: none

### q002_rattay_sgn_lengths_human_cat

**Question:** How do spiral ganglion neuron lengths compare between humans and cats?

**Answer:**

```
Answer:
Spiral ganglion neuron lengths in humans are about 32.36 mm on average, which is more than twice as long as the 15.82 mm average length found in cats.

Evidence summary:
The context provides specific measurements of spiral ganglion neuron lengths for both human and cat subjects, indicating a significant difference between the two species.

Source IDs:
[1]
```

- Fact recall: 60.0% (missed: 32.35, 15.81)
- Citation validity: 100.0%
- Citation grounding: 100.0%
- Suspicious numbers: ['32.36 mm', '15.82 mm']

### q005_rattay_ribbon_synapse_currents_jitter

**Question:** How did strong postsynaptic currents from inner hair cell ribbon synapses affect spike initiation and synchrony in type I spiral ganglion neurons?

**Answer:**

```
Answer:
Strong postsynaptic currents from inner hair cell ribbon synapses initiated precise spikes in type I spiral ganglion neurons, enhancing the precision of spike timing [3]. These currents were 15 times above threshold and ensured quick and reliable sensory transduction to accurately preserve timing information of sound.

Evidence summary:
The context highlights that strong synaptic currents at the ribbon synapses between inner hair cells and type I spiral ganglion neurons facilitate precise spike initiation, which is crucial for accurate temporal coding in auditory processing [3].

Source IDs:
[3], [1]
```

- Fact recall: 25.0% (missed: 400, pA, jitter)
- Citation validity: 100.0%
- Citation grounding: 100.0%
- Suspicious numbers: none

### q013_neymotin_model_methods_neuron_rxd

**Question:** What simulation environment and multiscale modeling components were used in the Neymotin calcium-HCN neocortex model?

**Answer:**

```
Answer:
NEURON simulation environment and multiscale modeling components were used in the Neymotin calcium-HCN neocortex model.

Evidence summary:
The context mentions that NEURON was used for implementing ion channels, specifically HCN channels, which are crucial in the calcium-HCN neocortex model [1]. Additionally, it indicates that this model involves a network scale component as part of a multiscale approach [2].

Source IDs:
[1], [2]
```

- Fact recall: 33.3% (missed: RxD, NMODL)
- Citation validity: 100.0%
- Citation grounding: 0.0%
- Suspicious numbers: none

### q015_potrusil_two_step_modeling_framework

**Question:** What two-step computational framework did Potrusil use to model cochlear implant stimulation of auditory neurons?

**Answer:**

```
Answer:
I do not have enough evidence in the retrieved context to answer confidently.

Evidence summary:
The retrieved context does not provide specific information about the two-step computational framework used by Potrusil to model cochlear implant stimulation of auditory neurons.

Source IDs:
[1], [2]
```

- Fact recall: 33.3% (missed: finite element, multi-compartment)
- Citation validity: 100.0%
- Citation grounding: 50.0%
- Suspicious numbers: none

