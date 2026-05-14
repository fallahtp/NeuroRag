# NeuroRag Answer Evaluation (LLM-judged fact recall)

Model:    `phi3:mini`
Pipeline: `?`
Judge:    `gemini-2.5-flash`
Questions: 63
Judge failures: 0

## Headline

| Metric | Strict substring | LLM judge |
|---|---:|---:|
| Mean fact recall | 24.1% | 34.8% |
| Mean citation validity | 97.6% | n/a (deterministic) |
| Mean citation grounding | 33.4% | n/a (deterministic) |

Strict fact recall counts a fact as matched only when the answer contains the exact substring. The LLM judge labels each fact as `present` (1.0), `partial` (0.5), or `absent` (0.0) and takes the mean. Paraphrases and synonyms count under the judge but not under strict matching.

## Per-question scores

| ID | Strict | Judge | Δ |
|---|---:|---:|---:|
| q001_rattay_sgn_signal_transduction_phases | 0.0% | 37.5% | +38pp |
| q002_rattay_sgn_lengths_human_cat | 80.0% | 100.0% | +20pp |
| q003_rattay_type_i_process_diameters | 50.0% | 50.0% | 0 |
| q004_rattay_soma_myelination_cat_human | 60.0% | 60.0% | 0 |
| q005_rattay_ribbon_synapse_currents_jitter | 50.0% | 25.0% | -25pp |
| q006_luque_hcn1_localization_type_i_sgn | 66.7% | 66.7% | 0 |
| q007_luque_hcn3_prestin_ohc | 100.0% | 100.0% | 0 |
| q008_luque_hcn2_hcn4_postnatal_development | 100.0% | 100.0% | 0 |
| q009_luque_hcn_aging_thresholds | 100.0% | 100.0% | 0 |
| q010_luque_hcn2_hcn4_coexpression | 33.3% | 66.7% | +33pp |
| q011_accili_hcn_isoform_kinetics | 100.0% | 100.0% | 0 |
| q012_accili_hcn_ionic_properties | 100.0% | 100.0% | 0 |
| q013_neymotin_model_methods_neuron_rxd | 0.0% | 0.0% | 0 |
| q014_neymotin_free_calcium_persistent_activity | 66.7% | 66.7% | 0 |
| q015_potrusil_two_step_modeling_framework | 66.7% | 66.7% | 0 |
| q016_potrusil_low_frequency_tonotopic_order | 66.7% | 0.0% | -67pp |
| q017_croner_degeneration_absolute_threshold | 100.0% | 100.0% | 0 |
| q018_croner_pitch_degenerative_state | 100.0% | 100.0% | 0 |
| q019_recugnat_hcn_klt_spike_rate_adaptation | 100.0% | 100.0% | 0 |
| q020_smith_node_geometry_spike_timing | 100.0% | 100.0% | 0 |
| q021_glueckert_sgn_turn_distances | 0.0% | 10.0% | +10pp |
| q022_glueckert_osl_microstructure_measurements | 0.0% | 0.0% | 0 |
| q023_glueckert_longterm_deaf_sgn_survival | 16.7% | 0.0% | -17pp |
| q024_smith_pn_cn_node_maturation | 28.6% | 28.6% | 0 |
| q025_smith_perisomatic_nodes_after_hearing_onset | 0.0% | 33.3% | +33pp |
| q026_smith_spike_generator_migration | 14.3% | 35.7% | +21pp |
| q027_smith_location_specific_node_geometry_p20 | 0.0% | 0.0% | 0 |
| q028_smith_node_geometry_model_conduction_speed | 0.0% | 7.1% | +7pp |
| q029_liu_human_cochlea_methods | 0.0% | 0.0% | 0 |
| q030_liu_nmsc_laminin_collagen_expression | 0.0% | 0.0% | 0 |
| q031_liu_habenula_basement_membrane | 0.0% | 20.0% | +20pp |
| q032_liu_nihl_monopolar_sgns | 0.0% | 33.3% | +33pp |
| q033_liu_discussion_spike_generation_ci | 0.0% | 20.0% | +20pp |
| q034_liu_cx43_human_specimen_methods | 0.0% | 16.7% | +17pp |
| q035_liu_cx43_guinea_pig_comparison | 0.0% | 40.0% | +40pp |
| q036_liu_cx43_human_sgc_gap_junctions | 0.0% | 25.0% | +25pp |
| q037_liu_tem_gap_junction_dimensions | 0.0% | 33.3% | +33pp |
| q038_liu_deafness_monopolar_sgn_survival | 0.0% | 16.7% | +17pp |
| q039_tylstedt_tem_human_cochlea_methods | 0.0% | 0.0% | 0 |
| q040_tylstedt_middle_turn_cell_counts | 0.0% | 0.0% | 0 |
| q041_tylstedt_physical_interaction_results | 0.0% | 41.7% | +42pp |
| q042_tylstedt_membrane_specializations | 0.0% | 0.0% | 0 |
| q043_tylstedt_discussion_myelination_units | 0.0% | 33.3% | +33pp |
| q044_ota_human_sgn_specimen_methods | 0.0% | 16.7% | +17pp |
| q045_ota_large_small_neuron_population | 0.0% | 0.0% | 0 |
| q046_ota_large_neuron_process_myelination | 0.0% | 60.0% | +60pp |
| q047_ota_age_related_myelinated_large_neurons | 0.0% | 25.0% | +25pp |
| q048_ota_discussion_fiber_distribution_function | 0.0% | 33.3% | +33pp |
| q049_bai_psychophysical_measurement_protocol | 0.0% | 0.0% | 0 |
| q050_bai_microct_fem_sgn_modeling | 0.0% | 33.3% | +33pp |
| q051_bai_dt_mcl_results_variability | 0.0% | 0.0% | 0 |
| q052_bai_jaccard_neural_excitation_profiles | 0.0% | 16.7% | +17pp |
| q053_bai_dt_mcl_excitation_level_mapping | 0.0% | 33.3% | +33pp |
| q054_recugnat_single_node_adaptation_channels | 0.0% | 33.3% | +33pp |
| q055_recugnat_multicompartment_sgn_geometry | 0.0% | 50.0% | +50pp |
| q056_recugnat_stimulation_electrode_positions | 0.0% | 0.0% | 0 |
| q057_recugnat_single_compartment_adaptation_results | 0.0% | 8.3% | +8pp |
| q058_recugnat_thresholds_recovery_multicompartment | 0.0% | 0.0% | 0 |
| q059_fellner_comsol_framework_physics | 0.0% | 0.0% | 0 |
| q060_fellner_meshing_dof_strategy | 0.0% | 0.0% | 0 |
| q061_fellner_membrane_coupling_signs | 0.0% | 25.0% | +25pp |
| q062_fellner_honeycomb_whole_fem_results | 16.7% | 25.0% | +8pp |
| q063_fellner_cochlear_electrode_mrg_examples | 0.0% | 0.0% | 0 |

## Sample judge rationales

Showing the first 5 questions' per-fact rationales for transparency.

### q001_rattay_sgn_signal_transduction_phases

- **absent** — postsynaptic delay
  - The answer describes spike initiation at the peripheral terminal but does not mention a postsynaptic delay as a distinct phase.
- **partial** — peripheral process
  - The answer mentions "Spike initiation at the peripheral terminal" which is related to the peripheral process, but does not explicitly state "peripheral process" as a phase of transduction or describe conduction along it.
- **present** — presomatic delay
  - The answer explicitly states "a delay before somatic spike generation due to large soma capacitance loading via axial current flow," which accurately describes the presomatic delay.
- **absent** — central process
  - The answer explicitly states that phases "iv & v seems incomplete" and does not mention the central process as a phase of spike transduction.

### q002_rattay_sgn_lengths_human_cat

- **present** — 32.35
  - The answer states "approximately 32 mm" and the evidence summary explicitly mentions "32.35" as part of the range for human SGNs.
- **present** — 15.81
  - The answer states "around 16 mm" and the evidence summary explicitly mentions "15.80" as part of the range for cat SGNs.
- **present** — mm
  - The answer explicitly uses the unit "mm" when stating the lengths for both human and cat SGNs.
- **present** — human
  - The answer clearly refers to "humans" and "human SGNs" when discussing the neuron lengths.
- **present** — cat
  - The answer clearly refers to "cats" and "cat SGNs" when discussing the neuron lengths.

### q003_rattay_type_i_process_diameters

- **present** — 1.32
  - The answer explicitly states "a mean of 1.3260.15 mm" for human peripheral process diameter.
- **absent** — 2.65
  - The value "2.65" is not mentioned or implied anywhere in the candidate answer.
- **absent** — 1.02
  - The value "1.02" is not mentioned or implied anywhere in the candidate answer.
- **absent** — 1.81
  - The value "1.81" is not mentioned or implied anywhere in the candidate answer.
- **present** — human
  - The answer explicitly refers to "human type I SGNs" and "In humans".
- **present** — cat
  - The answer explicitly refers to "cat spiral ganglion neurons" and "on cats".

### q004_rattay_soma_myelination_cat_human

- **absent** — 95.54
  - The candidate answer does not mention the numerical value '95.54'.
- **absent** — 3.65
  - The candidate answer does not mention the numerical value '3.65'.
- **present** — myelinat
  - The answer repeatedly uses the term 'myelination patterns' and 'soma myelination'.
- **present** — cat
  - The answer explicitly mentions 'cats' multiple times, discussing 'cats versus humans' and 'feline soma myelination'.
- **present** — human
  - The answer explicitly mentions 'humans' multiple times, discussing 'cats versus humans' and 'human cochlear cells'.

### q005_rattay_ribbon_synapse_currents_jitter

- **absent** — 400
  - The candidate answer does not mention the numerical value '400' or any similar specific current amplitude.
- **absent** — pA
  - The candidate answer mentions 'postsynaptic currents' but does not specify 'pA' as a unit of current.
- **absent** — jitter
  - The candidate answer mentions 'shortened delays' and 'rapid signal propagation' but does not use the term 'jitter' or a direct synonym for it in relation to spike synchrony.
- **present** — ribbon synapse
  - The candidate answer explicitly states 'inner hair cell ribbon synapses' in the first sentence.

