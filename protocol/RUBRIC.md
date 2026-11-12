# Coding Rubric — Wildfire Detection Evidence Audit

Unit of analysis: one primary research paper reporting a wildfire/forest-fire detection method.
Every item is coded from the FULL TEXT. If the full text does not state it, the code is
`not_reported` — never inferred, never guessed from context. "Not reported" is itself the finding.

Each coded item carries an `evidence` field: a verbatim quote (<=300 chars) plus section/page.
An item coded anything other than `not_reported` WITHOUT a verbatim quote is invalid and must
be re-coded.

---

## A. Identification
| Field | Values |
|---|---|
| `paper_id` | OpenAlex ID |
| `doi`, `year`, `venue`, `modality` | from corpus metadata |
| `task` | classification / detection(bbox) / segmentation / anomaly / regression / multi |
| `target` | flame / smoke / both / thermal-hotspot / gas-chemical / other |

## B. Data provenance
| Field | Values |
|---|---|
| `datasets_used` | list of named datasets + "private/self-collected" |
| `dataset_public` | yes / partly / no / not_reported |
| `n_train`, `n_val`, `n_test` | integer or not_reported |
| `data_source_type` | video-derived frames / independent stills / satellite scenes / sensor time-series / synthetic / mixed / not_reported |

## C. SPLIT PROTOCOL  ** the central construct **

### Category set, revised for round 2

Round 1 failed on this field: raw agreement 0.56, Cohen's kappa 0.280 against a pre-registered
0.80. The diagnosis was a rubric defect, not coder noise. Every disagreement had the same
shape — both coders quoted the SAME sentence and split between `random_resplit` and
`not_reported`, because the modal case (a ratio is stated, the mechanism never is) had no code
of its own. One coder read "no statement that it was random" and the other read "a ratio is
given, therefore it was re-split". Both readings were defensible, which is what tells you the
categories were wrong.

**The 0.80 threshold has not been moved.** Round 1 is reported as a failure alongside round 2.

| Code | Definition |
|---|---|
| `official_heldout` | used the benchmark's own designated test set, unmodified |
| `explicitly_random` | the paper states the split was random or shuffled |
| `ratio_only_mechanism_unstated` | a ratio or count is given; the mechanism is never stated. **The modal case, and a finding in its own right: reporting a ratio is not reporting a protocol** |
| `k_fold_random` | k-fold cross-validation over a pooled set |
| `group_disjoint` | explicitly disjoint by video, site, event, camera or time |
| `cross_dataset` | trained on one corpus, tested on another |
| `augment_then_split` | augmented copies generated BEFORE partitioning, so variants of one source image land on both sides |
| `no_split_statement` | no ratio, no counts, no mechanism |
| `internally_inconsistent` | the paper describes two incompatible protocols |

Precedence when more than one applies: `augment_then_split` outranks everything else, because
it determines whether the partition can separate anything at all. Then
`internally_inconsistent`, then the most specific mechanism actually stated.

| Field | Values |
|---|---|
| `split_protocol` | one code from the table above |
| `split_stated_verbatim` | quote |
| `leakage_risk` | `high` = video/burst-derived frames split randomly, or same site/event both sides; `medium` = unclear provenance or unclear split; `low` = disjoint by event/site/camera/time; `none_verifiable` |
| `leakage_acknowledged` | yes / no |
| `duplicate_check_done` | yes / no |

FLAME-specific (code only if FLAME used):
| Field | Values |
|---|---|
| `flame_official_test_used` | yes / no / unclear |
| `flame_n_images_used` | integer (official train pool is 39,375; test is 8,617) |
| `flame_reported_accuracy` | float |

## D. Validity of the reported number
| Field | Values |
|---|---|
| `headline_metric`, `headline_value` | e.g. accuracy, 99.46 |
| `metrics_reported` | multi-select: accuracy / precision / recall / F1 / mAP / IoU / AUC / FPR / FAR-per-time / MCC |
| `class_balance_reported` | yes / no |
| `variance_reported` | yes (seeds/CI/std) / no |
| `n_runs` | integer or not_reported |
| `statistical_test_vs_baseline` | yes / no |
| `ablation_present` | yes / no |
| `comparison_is_like_for_like` | yes / no / unclear — were the compared numbers produced under the SAME split protocol? Flag `no` when a paper tabulates its own re-split score against others' official-split scores. |

## E. External validity
| Field | Values |
|---|---|
| `cross_dataset_eval` | yes / no |
| `cross_dataset_delta` | accuracy drop in points, if reported |
| `tested_unseen_site_or_season` | yes / no |
| `night_or_lowlight_tested` | yes / no |
| `smoke_only_early_stage_tested` | yes / no |
| `adverse_weather_tested` | yes / no (fog, cloud, haze, rain) |
| `false_positive_sources_analysed` | yes / no (sunset glare, cloud, dust, industrial smoke, agricultural burns) |

## F. Deployment reality  ** the second central construct **
| Field | Values |
|---|---|
| `deployment_level` | L0 dataset-only / L1 lab bench / L2 controlled outdoor test burn / L3 short field pilot (<30 d) / L4 sustained deployment (>=1 fire season) / L5 operational service with agency users |
| `deployment_duration_days` | integer or not_reported |
| `n_nodes_or_cameras` | integer or not_reported |
| `area_covered_km2` | float or not_reported |
| `real_wildfire_detected` | yes (an actual unplanned wildfire) / test burns only / no / not_reported |
| `failure_modes_reported` | yes / no |

## G. Operational metrics  ** what agencies actually need **
| Field | Values |
|---|---|
| `false_alarms_per_unit_time` | reported value or not_reported |
| `time_to_detection` | reported value or not_reported |
| `min_detectable_fire_size` | reported value or not_reported |
| `detection_range` | reported value or not_reported |
| `power_measured` | measured / estimated / not_reported |
| `latency_measured_on_target_hw` | yes / no — was inference timed on the deployment hardware, or only on a desktop GPU? |
| `target_hardware_named` | string or not_reported |

## H. Reproducibility
| Field | Values |
|---|---|
| `code_available` | yes+link / stated-on-request / no |
| `weights_available` | yes / no |
| `link_resolves` | yes / no / not_checked — CHECK EVERY LINK, dead links are a finding |
| `hyperparams_full` | yes / partial / no |
| `seed_reported` | yes / no |

---

## Coding procedure (must be followed and reported in the paper)

1. **Control set first.** Two humans independently hand-code 20 papers (stratified) before any
   automated coding. This is the gold standard.
2. **LLM coder validation.** The LLM coder codes the same 20. Compute per-field Cohen's kappa
   against the gold standard. Fields with kappa < 0.7 are either re-specified or coded by hand
   for the whole sample. Report the kappa table in the paper.
3. **Full sample.** Only fields that passed validation are auto-coded.
4. **Verification pass.** A random 15% of auto-coded papers is re-coded by hand; report agreement.
5. **Disclosure.** The manuscript must name the LLM used, the version, the prompt, and the
   validation results. An LLM that acts as a rater is a method, and undisclosed it is a defect.
6. Every quantitative claim in the paper must be regenerable from `coded.json` by a script.

## Guard against the obvious reviewer attack
The reviewer will say: "you cannot tell leakage from the text alone." Correct — which is why
`leakage_risk` is coded as RISK, never as confirmed leakage, and why the FLAME retraining
experiment exists: it converts one instance of the risk into a measured effect.
