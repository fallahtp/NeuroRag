# NeuroRag Answer Evaluation (LLM-judged fact recall)

Model:    `qwen2.5:7b-instruct`
Pipeline: `?`
Judge:    `gemini-2.5-flash`
Questions: 63
Judge failures: 0

## Headline

| Metric | Strict substring | LLM judge |
|---|---:|---:|
| Mean fact recall | 23.9% | 33.8% |
| Mean citation validity | 100.0% | n/a (deterministic) |
| Mean citation grounding | 39.7% | n/a (deterministic) |

Strict fact recall counts a fact as matched only when the answer contains the exact substring. The LLM judge labels each fact as `present` (1.0), `partial` (0.5), or `absent` (0.0) and takes the mean. Paraphrases and synonyms count under the judge but not under strict matching.

## Per-question scores

| ID | Strict | Judge | Δ |
|---|---:|---:|---:|
| q001_rattay_sgn_signal_transduction_phases | 0.0% | 50.0% | +50pp |
| q002_rattay_sgn_lengths_human_cat | 60.0% | 100.0% | +40pp |
| q003_rattay_type_i_process_diameters | 66.7% | 66.7% | 0 |
| q004_rattay_soma_myelination_cat_human | 60.0% | 60.0% | 0 |
| q005_rattay_ribbon_synapse_currents_jitter | 75.0% | 75.0% | 0 |
| q006_luque_hcn1_localization_type_i_sgn | 66.7% | 66.7% | 0 |
| q007_luque_hcn3_prestin_ohc | 100.0% | 100.0% | 0 |
| q008_luque_hcn2_hcn4_postnatal_development | 66.7% | 100.0% | +33pp |
| q009_luque_hcn_aging_thresholds | 66.7% | 100.0% | +33pp |
| q010_luque_hcn2_hcn4_coexpression | 66.7% | 66.7% | 0 |
| q011_accili_hcn_isoform_kinetics | 100.0% | 100.0% | 0 |
| q012_accili_hcn_ionic_properties | 100.0% | 33.3% | -67pp |
| q013_neymotin_model_methods_neuron_rxd | 33.3% | 33.3% | 0 |
| q014_neymotin_free_calcium_persistent_activity | 66.7% | 66.7% | 0 |
| q015_potrusil_two_step_modeling_framework | 33.3% | 0.0% | -33pp |
| q016_potrusil_low_frequency_tonotopic_order | 66.7% | 0.0% | -67pp |
| q017_croner_degeneration_absolute_threshold | 100.0% | 100.0% | 0 |
| q018_croner_pitch_degenerative_state | 100.0% | 100.0% | 0 |
| q019_recugnat_hcn_klt_spike_rate_adaptation | 100.0% | 100.0% | 0 |
| q020_smith_node_geometry_spike_timing | 100.0% | 100.0% | 0 |
| q021_glueckert_sgn_turn_distances | 0.0% | 0.0% | 0 |
| q022_glueckert_osl_microstructure_measurements | 0.0% | 0.0% | 0 |
| q023_glueckert_longterm_deaf_sgn_survival | 16.7% | 0.0% | -17pp |
| q024_smith_pn_cn_node_maturation | 28.6% | 0.0% | -29pp |
| q025_smith_perisomatic_nodes_after_hearing_onset | 0.0% | 25.0% | +25pp |
| q026_smith_spike_generator_migration | 14.3% | 42.9% | +29pp |
| q027_smith_location_specific_node_geometry_p20 | 0.0% | 43.8% | +44pp |
| q028_smith_node_geometry_model_conduction_speed | 0.0% | 14.3% | +14pp |
| q029_liu_human_cochlea_methods | 0.0% | 0.0% | 0 |
| q030_liu_nmsc_laminin_collagen_expression | 0.0% | 0.0% | 0 |
| q031_liu_habenula_basement_membrane | 0.0% | 0.0% | 0 |
| q032_liu_nihl_monopolar_sgns | 0.0% | 25.0% | +25pp |
| q033_liu_discussion_spike_generation_ci | 0.0% | 0.0% | 0 |
| q034_liu_cx43_human_specimen_methods | 0.0% | 25.0% | +25pp |
| q035_liu_cx43_guinea_pig_comparison | 0.0% | 0.0% | 0 |
| q036_liu_cx43_human_sgc_gap_junctions | 0.0% | 25.0% | +25pp |
| q037_liu_tem_gap_junction_dimensions | 0.0% | 33.3% | +33pp |
| q038_liu_deafness_monopolar_sgn_survival | 0.0% | 16.7% | +17pp |
| q039_tylstedt_tem_human_cochlea_methods | 0.0% | 16.7% | +17pp |
| q040_tylstedt_middle_turn_cell_counts | 0.0% | 14.3% | +14pp |
| q041_tylstedt_physical_interaction_results | 0.0% | 50.0% | +50pp |
| q042_tylstedt_membrane_specializations | 0.0% | 8.3% | +8pp |
| q043_tylstedt_discussion_myelination_units | 0.0% | 33.3% | +33pp |
| q044_ota_human_sgn_specimen_methods | 0.0% | 0.0% | 0 |
| q045_ota_large_small_neuron_population | 0.0% | 0.0% | 0 |
| q046_ota_large_neuron_process_myelination | 0.0% | 60.0% | +60pp |
| q047_ota_age_related_myelinated_large_neurons | 0.0% | 33.3% | +33pp |
| q048_ota_discussion_fiber_distribution_function | 0.0% | 66.7% | +67pp |
| q049_bai_psychophysical_measurement_protocol | 0.0% | 0.0% | 0 |
| q050_bai_microct_fem_sgn_modeling | 0.0% | 33.3% | +33pp |
| q051_bai_dt_mcl_results_variability | 0.0% | 0.0% | 0 |
| q052_bai_jaccard_neural_excitation_profiles | 0.0% | 0.0% | 0 |
| q053_bai_dt_mcl_excitation_level_mapping | 0.0% | 33.3% | +33pp |
| q054_recugnat_single_node_adaptation_channels | 0.0% | 16.7% | +17pp |
| q055_recugnat_multicompartment_sgn_geometry | 16.7% | 16.7% | 0 |
| q056_recugnat_stimulation_electrode_positions | 0.0% | 0.0% | 0 |
| q057_recugnat_single_compartment_adaptation_results | 0.0% | 16.7% | +17pp |
| q058_recugnat_thresholds_recovery_multicompartment | 0.0% | 0.0% | 0 |
| q059_fellner_comsol_framework_physics | 0.0% | 0.0% | 0 |
| q060_fellner_meshing_dof_strategy | 0.0% | 0.0% | 0 |
| q061_fellner_membrane_coupling_signs | 0.0% | 41.7% | +42pp |
| q062_fellner_honeycomb_whole_fem_results | 0.0% | 16.7% | +17pp |
| q063_fellner_cochlear_electrode_mrg_examples | 0.0% | 0.0% | 0 |

## Sample judge rationales

Showing the first 5 questions' per-fact rationales for transparency.

### q001_rattay_sgn_signal_transduction_phases

- **absent** — postsynaptic delay
  - The answer does not mention 'postsynaptic delay'; it refers to a 'delay before the generation of the somatic spike', which corresponds to a presomatic delay.
- **present** — peripheral process
  - The answer refers to 'spike initiation at the peripheral terminal', which is a component of the peripheral process.
- **present** — presomatic delay
  - The evidence summary explicitly states 'a considerable delay before the generation of the somatic spike', which is synonymous with presomatic delay.
- **absent** — central process
  - The answer mentions 'propagation through the soma' but does not explicitly name or describe the 'central process' or axon.

### q002_rattay_sgn_lengths_human_cat

- **present** — 32.35
  - The answer states "32.36", which is numerically very close to the expected "32.35" and within an acceptable rounding range.
- **present** — 15.81
  - The answer states "15.82", which is numerically very close to the expected "15.81" and within an acceptable rounding range.
- **present** — mm
  - The answer explicitly states the unit "mm" for the neuron lengths.
- **present** — human
  - The answer explicitly mentions "humans" in relation to the neuron lengths.
- **present** — cat
  - The answer explicitly mentions "cats" in relation to the neuron lengths.

### q003_rattay_type_i_process_diameters

- **present** — 1.32
  - The answer explicitly states the value "1.32" for the peripheral process diameter in humans.
- **absent** — 2.65
  - The value "2.65" is not mentioned anywhere in the candidate answer.
- **absent** — 1.02
  - The value "1.02" is not mentioned anywhere in the candidate answer.
- **present** — 1.81
  - The answer explicitly states the value "1.81" for the central process diameter in cats.
- **present** — human
  - The answer explicitly mentions "humans" when discussing the peripheral process diameter.
- **present** — cat
  - The answer explicitly mentions "cats" when discussing the central process diameter.

### q004_rattay_soma_myelination_cat_human

- **absent** — 95.54
  - The candidate answer does not mention the numerical value "95.54".
- **absent** — 3.65
  - The candidate answer does not mention the numerical value "3.65".
- **present** — myelinat
  - The answer explicitly uses the terms "myelinated", "myelinating", and "myelination" multiple times.
- **present** — cat
  - The answer explicitly mentions "cats" twice when discussing the myelination of type I spiral ganglion neurons.
- **present** — human
  - The answer explicitly mentions "humans" in the context of comparing myelination with cats.

### q005_rattay_ribbon_synapse_currents_jitter

- **present** — 400
  - The answer explicitly states the numerical value '400' in 'Simulated 400 pA postsynaptic currents'.
- **present** — pA
  - The answer explicitly states the unit 'pA' in 'Simulated 400 pA postsynaptic currents'.
- **absent** — jitter
  - The answer discusses 'precision of spike timing' and 'preserving timing information', which are related to the *absence* of jitter, but it does not mention the term 'jitter' itself or a direct synonym for timing variability.
- **present** — ribbon synapse
  - The answer explicitly states 'ribbon synapses' in 'inner hair cell ribbon synapses'.

