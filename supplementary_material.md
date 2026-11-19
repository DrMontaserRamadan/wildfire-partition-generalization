# Supplementary materials

Companion to the article "Random image splits overstate wildfire detector accuracy: A controlled experiment on data leakage and an audit of reporting practice". Every table
here is generated from the same frozen records the manuscript's verification gate reads, so
the two cannot drift apart.

This document names files and scripts by path. That is deliberate and is confined to
this document: here they are re-run instructions for the archive, not narrative, and the
article itself names none of them. Every file named below is verified to exist in the
archive at build time, and the build fails if one does not.

## S1. Corpus construction and the search record

The eligible frame was frozen at 2026-09-11T10:28:25 with
checksum `cb3410d76acec26d…` before any retrieval, so that later
acquisition could fill cells in a fixed table without changing which papers were eligible.
No update search was performed after the freeze.

### S1.1 Eligibility criteria as registered

- primary research article reporting a wildfire/forest-fire detection method
- publication year >= 2020
- indexed venue (predatory/preprint-only venues removed)
- abstract of at least 250 characters available
- detection/recognition is the subject of the TITLE
- not a review, survey, taxonomy or bibliometric study

### S1.2 Search strings

Five searches were run against the OpenAlex works endpoint, each the same wildfire term
crossed with one modality vocabulary, restricted to
`from_publication_date:2019-01-01` and `type:article|preprint|book-chapter|proceedings-article`. They are reproduced here exactly as the harvest
script holds them, not retyped.

Shared wildfire term:

```
(wildfire OR wildfires OR "forest fire" OR "forest fires" OR "wildland fire" OR bushfire OR "flame detection" OR "smoke detection")
```

`vision`:

```
title_and_abstract.search:(wildfire OR wildfires OR "forest fire" OR "forest fires" OR "wildland fire" OR bushfire OR "flame detection" OR "smoke detection") AND ("deep learning" OR CNN OR "convolutional" OR YOLO OR "computer vision" OR "neural network" OR transformer OR "image classification" OR "object detection")
```

`uav`:

```
title_and_abstract.search:(wildfire OR wildfires OR "forest fire" OR "forest fires" OR "wildland fire" OR bushfire OR "flame detection" OR "smoke detection") AND (UAV OR "unmanned aerial" OR drone OR "aerial vehicle" OR quadcopter)
```

`iot`:

```
title_and_abstract.search:(wildfire OR wildfires OR "forest fire" OR "forest fires" OR "wildland fire" OR bushfire OR "flame detection" OR "smoke detection") AND ("internet of things" OR IoT OR "wireless sensor network" OR WSN OR LoRa OR LoRaWAN OR ZigBee OR "sensor node" OR "sensor nodes")
```

`edge`:

```
title_and_abstract.search:(wildfire OR wildfires OR "forest fire" OR "forest fires" OR "wildland fire" OR bushfire OR "flame detection" OR "smoke detection") AND ("edge computing" OR "edge AI" OR TinyML OR embedded OR microcontroller OR "on-device" OR "real-time detection")
```

`sat`:

```
title_and_abstract.search:(wildfire OR wildfires OR "forest fire" OR "forest fires" OR "wildland fire" OR bushfire OR "flame detection" OR "smoke detection") AND (satellite OR MODIS OR VIIRS OR Sentinel OR Landsat OR "remote sensing") AND (detect OR "active fire" OR "early detection")
```

### S1.3 Search log

A per-query log was not written at run time. What follows is reconstructed from the
harvest artifacts themselves: the tag each record carries names the query that returned
it, and the dates are the artifacts' modification times rather than timestamps recorded
by the searches. It is reported this way so a reader can tell a reconstruction from a
contemporaneous log. A record may be returned by more than one query, so the columns sum
to more than the row totals.

| query | raw harvest | after venue and type cleaning | in the eligible frame |
|---|---|---|---|
| `vision` | 3185 | 2190 | 109 |
| `uav` | 1559 | 1132 | 42 |
| `iot` | 1023 | 626 | 23 |
| `edge` | 1692 | 1190 | 36 |
| `sat` | 1617 | 1119 | 34 |
| **distinct records** | **7113** | **4915** | **159** |

| stage | artifact | dated |
|---|---|---|
| raw harvest | `corpus/primary_raw.json` | 2026-09-09T12:19:34 |
| after cleaning | `corpus/primary_clean.json` | 2026-09-09T12:21:54 |
| eligible frame | `corpus/sample.json` | 2026-09-09T15:20:06 |
| frame frozen | `corpus/UNIVERSE_FROZEN.json` | 2026-09-11T10:28:25 |

No update search was run after the freeze, so the frame reflects the literature as of
these dates and not as of submission.

### S1.4 Venue exclusions

Venues were removed by pattern before the frame was frozen: preprint servers, repository
deposits and venues that publish no peer-reviewed primary research. The patterns applied
were:

```
arXiv|Research Square|DOAJ|Preprints|eBooks|international archives|Biodiversidade|Coimbra
zenodo|figshare|ssrn|preprint|osf|arxiv|research square|authorea
```

Records were then deduplicated on DOI, and where a DOI was absent, on normalized title
and first-author surname.

### S1.5 Exclusions applied before the freeze

**13 papers — document type is a review/survey, not a primary study** (title/abstract screen, before retrieval)

`W4414392371`, `W4407010276`, `W4298004560`, `W4393210577`, `W4404469625`, `W3100733145`, `W4403494901`, `W4402191377`, `W4398238258`, `W7128720729`, `W3129488782`, `W4389279575`, `W4400623715`

**10 papers — out of scope on full-text inspection** (full-text screen, author-supplied batch)

| id | reason |
|---|---|
| W4400604543 | not a wildfire-detection study: smart-city traffic monitoring. Only 2 fire menti |
| W4353034569 | not a fire-detection study: forestry road-network extraction from ALS. Fire appe |
| W4415459744 | not a wildfire study: industrial biomass-reactor smoke monitoring. RETAINED AS A |
| W4399887245 | document type is a review: One Earth labels it a 'Primer'. Moves to the excluded |
| W4312801608 | not wildfire: UV-sensor flame detection for 'homes and industries', radial secto |
| W4362653270 | not a detection study: WSN energy/routing protocol (Lie algebra). Forest fire is |
| W4403277959 | not wildfire: generic infrared small-target detection; 'marine rescue, forest fi |
| W4292258945 | not wildfire: land-cover change detection from remote sensing. |
| W4392694047 | not wildfire (borderline): anomaly detection in the Internet of Drone Things wit |
| W4410086460 | not wildfire: DOMESTIC/INDOOR fires. Its own abstract positions against our scop |

### S1.6 Retrieval by publisher

Retrieval is not random with respect to publisher; this is the full table behind that
statement in the Results.

| publisher | retrieved | candidates | rate |
|---|---|---|---|
| MDPI | 63 | 63 | 100.0% |
| other/small publisher | 2 | 31 | 6.5% |
| IEEE | 23 | 24 | 95.8% |
| Elsevier | 12 | 12 | 100.0% |
| Springer | 7 | 7 | 100.0% |
| no DOI | 0 | 6 | 0.0% |
| Nature Portfolio | 5 | 5 | 100.0% |
| Taylor & Francis | 0 | 5 | 0.0% |
| Wiley | 0 | 3 | 0.0% |
| BMC/SpringerOpen | 0 | 2 | 0.0% |
| Frontiers | 1 | 2 | 50.0% |
| Hindawi (Wiley) | 0 | 2 | 0.0% |
| IOP | 0 | 2 | 0.0% |
| PLOS | 2 | 2 | 100.0% |
| CSIRO | 0 | 1 | 0.0% |
| Copernicus | 0 | 1 | 0.0% |
| IET (Wiley) | 0 | 1 | 0.0% |
| **total** | | **169** | |

### S1.7 The eight candidates never retrieved

Of the 169 candidates, 115 were obtained by
automated retrieval and 46 by hand, leaving
8. Each is named with its abstract-level code and the reason,
because unretrieved papers named with their reasons are a limitation, whereas
unretrieved papers silently absent are not. All eight remain at scope tier C, meaning
their scope decision rests on the abstract and was never checked against an article.

| id | abstract code | in scope on abstract | doi | title | why not retrieved |
|---|---|---|---|---|---|
| W4393996034 | IN | yes | 10.3233/jifs-240531 | A few-shot target detection method for wildfires: Research | paywalled |
| W4396670524 | IN_BORDERLINE | yes | 10.4018/979-8-3693-1335-0.ch014 | An Analysis of Internet-of-Things-Based Fire Detection and | paywalled |
| W4404920067 | IN | yes | 10.55421/1998-7072_2024_27_7_115 | NEURAL NETWORK MODEL FOR FOREST FIRES RECOGNITION | paywalled |
| W7112289761 | IN | yes | 10.2514/6.2024-4946 (recovered) | Optimizing Fire Detection in Edge Devices: Integrating Ear | paywalled |
| W3115648885 | OUT_S2 | no | no DOI | Flood Detection System Based on Cloud Computing Server | paywalled |
| W3134708246 | OUT_S2 | no | no DOI | RANCANG BANGUN SISTEM MONITORING DAN PENGKONDISI POLUSI UD | paywalled |
| W4400172797 | OUT_S2 | no | 10.1142/s0219649224500758 | Fake News Detection: Traditional vs. Contemporary Machine  | paywalled |
| W4415949982 | OUT_S1 | no | 10.30693/smj.2025.14.10.63 | Evaluation of real-time fire and smoke detection performan | paywalled |

The four in scope on their abstracts would enter the endpoint denominator if they were
ever obtained. Their reporting practice is unobserved, and at this size the residual
cannot move the estimate far. Access was re-verified in a live browser on 2026-09-20 and
all four are still closed; the routes tried, including the ones that failed, are recorded
in the project's retrieval notes.

A DOI marked recovered was absent from the harvest record and found afterwards:
W7112289761 is 10.2514/6.2024-4946, AIAA AVIATION Forum and ASCEND 2024; exact-title Crossref match. The harvest reached it through a metadata-only repository
deposit that carries no DOI, which is why the frame recorded none; the paper is
still not retrievable, and the correction changes its identifier and nothing else.

## S2. The eight papers reclassified by full-text validation

The central variable was re-examined against complete stored full texts with the frozen
codes withheld. Agreement was 87.5% on the 64 papers carrying
both codes. The eight papers that moved are listed here with the sentence or the reason
that decided each, as the Results undertake.

| paper | frozen code | frozen category | validated category | what decided it |
|---|---|---|---|---|
| W4396937715 | ratio_only_mechanism_unstated | 2 — ratio or counts only | 4 — unresolved | leave-one-out CV stated only for the regression sub-models; the detection model's partition is never stated |
| W4403544374 | augment_then_split | 2 — ratio or counts only | 1 — mechanism reported | "The dataset is randomly divided into training, validation, and test sets in a 7:2:1 ratio" - random stated |
| W4413480292 | ratio_only_mechanism_unstated | 2 — ratio or counts only | 4 — unresolved | "divided ... in a ratio of 8:1:1" but the paper elsewhere defers to another work's partitioning; cannot resolve whether a rule is inherited |
| W4400071697 | explicitly_random | 1 — mechanism reported | 2 — ratio or counts only | set sizes stated (15,000 total; 4500 held out); no allocation rule |
| W4385704549 | no_split_statement | 3 — no partition statement | 1 — mechanism reported | "stratified four-fold cross-validation scheme, repeated five times" - mechanism stated |
| W4403079437 | group_disjoint | 1 — mechanism reported | 2 — ratio or counts only | per-palette training and test frame counts; no allocation rule |
| W4391034444 | explicitly_random | 1 — mechanism reported | 2 — ratio or counts only | "divided into training, validation, and test sets, with a distribution ratio of 8:1:1" - no rule |
| W4207031702 | augment_then_split | 2 — ratio or counts only | 1 — mechanism reported | "Among these data, 70% was used for training, and 30% was used for testing. The training and testing data were randomly selected" - random |

3 moved toward a stated mechanism, 3 away from one, and 2 into the unresolved category.

## S3. Full reliability table, including the failures

All 49 substantive variables, coded on 67 papers by two
roles. A variable was admitted to primary analysis at kappa ≥ 0.8, or on a
modal category above 90% with raw agreement ≥ 0.90. The classification rule was fixed
before coding. Failures are listed here rather than omitted.

Summary: 38 primary, 4 qualified secondary, 4 failed, 3 excluded in advance as free text.

| variable | raw | kappa | modal share | disagreements | class |
|---|---|---|---|---|---|
| `ablation_present` | 0.970 | 0.932 | 0.672 | 2 | PRIMARY-SAFE |
| `adverse_weather_tested` | 0.940 | 0.836 | 0.776 | 4 | PRIMARY-SAFE |
| `class_balance_reported` | 0.940 | 0.884 | 0.522 | 4 | PRIMARY-SAFE |
| `code_available` | 1.000 | 1.000 | 0.940 | 0 | PRIMARY-SAFE |
| `comparison_is_like_for_like` | 0.910 | 0.851 | 0.552 | 6 | PRIMARY-SAFE |
| `cross_dataset_delta` | 0.970 | 0.922 | 0.761 | 2 | PRIMARY-SAFE |
| `cross_dataset_eval` | 0.985 | 0.948 | 0.821 | 1 | PRIMARY-SAFE |
| `data_source_type` | 0.910 | 0.880 | 0.373 | 6 | PRIMARY-SAFE |
| `deployment_level` | 0.985 | 0.966 | 0.731 | 1 | PRIMARY-SAFE |
| `detection_range` | 0.925 | 0.270 | 0.970 | 5 | PRIMARY-SAFE |
| `duplicate_check_done` | 1.000 | 1.000 | 0.910 | 0 | PRIMARY-SAFE |
| `failure_modes_reported` | 0.955 | 0.888 | 0.731 | 3 | PRIMARY-SAFE |
| `false_alarms_per_unit_time` | 1.000 | — | 1.000 | 0 | PRIMARY-SAFE |
| `false_positive_sources_analysed` | 0.970 | 0.934 | 0.672 | 2 | PRIMARY-SAFE |
| `flame_n_images_used` | 1.000 | 1.000 | 0.806 | 0 | PRIMARY-SAFE |
| `flame_official_test_used` | 1.000 | 1.000 | 0.806 | 0 | PRIMARY-SAFE |
| `flame_reported_accuracy` | 0.985 | 0.956 | 0.806 | 1 | PRIMARY-SAFE |
| `headline_value` | 0.851 | 0.845 | 0.179 | 10 | PRIMARY-SAFE |
| `latency_measured_on_target_hw` | 0.970 | 0.862 | 0.896 | 2 | PRIMARY-SAFE |
| `leakage_acknowledged` | 0.970 | 0.905 | 0.806 | 2 | PRIMARY-SAFE |
| `leakage_risk` | 0.925 | 0.863 | 0.657 | 5 | PRIMARY-SAFE |
| `metrics_reported` | 0.821 | 0.811 | 0.134 | 12 | PRIMARY-SAFE |
| `min_detectable_fire_size` | 0.955 | 0.242 | 0.985 | 3 | PRIMARY-SAFE |
| `n_runs` | 0.970 | 0.789 | 0.925 | 2 | PRIMARY-SAFE |
| `n_test` | 0.896 | 0.828 | 0.627 | 7 | PRIMARY-SAFE |
| `n_train` | 0.970 | 0.955 | 0.582 | 2 | PRIMARY-SAFE |
| `n_val` | 0.940 | 0.897 | 0.672 | 4 | PRIMARY-SAFE |
| `night_or_lowlight_tested` | 0.925 | 0.823 | 0.716 | 5 | PRIMARY-SAFE |
| `power_measured` | 0.955 | 0.808 | 0.896 | 3 | PRIMARY-SAFE |
| `real_wildfire_detected` | 0.970 | 0.951 | 0.582 | 2 | PRIMARY-SAFE |
| `seed_reported` | 1.000 | 1.000 | 0.910 | 0 | PRIMARY-SAFE |
| `split_protocol` | 0.970 | 0.958 | 0.493 | 2 | PRIMARY-SAFE |
| `statistical_test_vs_baseline` | 1.000 | 1.000 | 0.985 | 0 | PRIMARY-SAFE |
| `target` | 0.970 | 0.957 | 0.418 | 2 | PRIMARY-SAFE |
| `task` | 0.955 | 0.932 | 0.537 | 3 | PRIMARY-SAFE |
| `time_to_detection` | 0.955 | 0.489 | 0.955 | 3 | PRIMARY-SAFE |
| `variance_reported` | 0.970 | 0.739 | 0.955 | 2 | PRIMARY-SAFE |
| `weights_available` | 1.000 | 1.000 | 0.955 | 0 | PRIMARY-SAFE |
| `dataset_public` | 0.866 | 0.799 | 0.388 | 9 | SECONDARY-QUALIFIED |
| `hyperparams_full` | 0.791 | 0.684 | 0.418 | 14 | SECONDARY-QUALIFIED |
| `smoke_only_early_stage_tested` | 0.881 | 0.734 | 0.761 | 8 | SECONDARY-QUALIFIED |
| `tested_unseen_site_or_season` | 0.925 | 0.768 | 0.836 | 5 | SECONDARY-QUALIFIED |
| `area_covered_km2` | 0.701 | 0.132 | 0.955 | 20 | UNRELIABLE-REMOVE |
| `deployment_duration_days` | 0.448 | -0.341 | 0.791 | 37 | UNRELIABLE-REMOVE |
| `link_resolves` | 0.836 | 0.000 | 0.836 | 11 | UNRELIABLE-REMOVE |
| `n_nodes_or_cameras` | 0.418 | -0.053 | 0.701 | 39 | UNRELIABLE-REMOVE |
| `datasets_used` | 0.090 | 0.088 | 0.015 | 61 | EXCLUDED (free text, P2) |
| `headline_metric` | 0.299 | 0.289 | 0.075 | 47 | EXCLUDED (free text, P2) |
| `target_hardware_named` | 0.836 | 0.637 | 0.731 | 11 | EXCLUDED (free text, P2) |

The four failures support no claim anywhere in the paper. Two of them carry a systematic
directional disagreement traceable to a defect recorded before coding began: the
instrument never specified which absence code applied to constructs a paper could not
have addressed.

## S4. Deployment context

This section stood in the Results until 2026-09-20. It is reproduced unchanged.

Of the 67 papers coded with the full instrument, 49 report work at the dataset level only, nine at a laboratory bench, six at a controlled outdoor test burn, and three at a short field pilot. None reports a sustained deployment across a fire season or an operational service with agency users. Two of the eighteen papers reporting any deployment describe detecting an unplanned wildfire. Six of those 67 report any operational metric, an agreement statistic driven by near-uniform absence.

We report these as context. The maturity levels behind them are not a new instrument, readiness framings for wildfire detection already exist in the review literature, and four variables that would quantify deployment scale failed our reliability threshold.

### S4.1 The maturity ladder in full

| level | meaning | papers |
|---|---|---|
| L0 | dataset level only — no physical deployment reported | 49 |
| L1 | laboratory bench | 9 |
| L2 | controlled outdoor test burn | 6 |
| L3 | short field pilot | 3 |
| | **total** | **67** |

Deployment duration in days, node or camera counts, area covered, and whether a code or
data link resolves all failed the reliability threshold, so no figure for deployment
scale is reported from this corpus in either document.

## S5. Controlled experiments on benchmark overlap

The passages in this section stood in the manuscript until 2026-10-13, when the
article was prepared for a journal whose guide sets a 10,000-word maximum. They are
reproduced unchanged, and nothing in them was rewritten on the way here. The article
keeps the measurement itself, both figures and the dataset citations. Where these
paragraphs say "the supplementary materials", they mean this document.

Partition provenance is one of two assumptions behind a cross-paper comparison. The other is that the datasets involved are independent. We tested that on a pair of widely circulated fire corpora, as a mechanistic illustration rather than a claim about this literature.

Using two perceptual hashes with a Hamming threshold of five and confirming candidates by normalized cross-correlation at 0.95, 218 of 502 images in FireNET have a near-duplicate in DeepQuestAI Fire-Smoke: 43.4% of the smaller corpus (Figure 6). Neither repository references the other. A third corpus, D-Fire, shows no overlap with any of the three, a specificity control demonstrating that the method does not return matches indiscriminately.

Near-duplicate contamination of benchmarks has been measured before, which puts this figure in proportion. Barz and Denzler found that 3.3% of the CIFAR-10 test set and 10% of the CIFAR-100 test set have a duplicate in the corresponding training set, and Lee and colleagues reduced a train-test overlap affecting over 4% of the validation set of standard language-modelling datasets by deduplicating the training corpora. Those are overlaps between the arms of one dataset, where ours is between two separately published corpora, so the quantities are not interchangeable; stated against them, the share measured here is between four and thirteen times larger. That is a statement about these two fire corpora and not about either field.

The comparison confirms 369 duplicate pairs in total: 275 spanning the two corpora, 89 sitting within a single split, three crossing the training and test partitions of one dataset, and two crossing training and validation. The 89 within-split pairs cross no partition boundary but are not inconsequential: duplicated items are effectively upweighted, reducing the effective sample size an estimate rests on.

None of the 275 cross-corpus pairs is byte-identical or pixel-identical. Deduplication by file hash, which at least one aggregator documents applying, returns nothing on this data and reports a clean corpus.

Two controlled experiments identify what the overlap does (Figure 7). Training on DeepQuestAI and evaluating on FireNET, the cross-dataset generalization experiment a researcher would naturally run, produces near-perfect recall on the overlapping subset and substantially lower recall on the remainder. Our first hypothesis was that the model memorizes the duplicated items. Removing all 234 of them from the training pool left the gap where it was: 33.5% against 33.0% with the full pool, a difference of 0.45 percentage points (95% CI −2.5 to +3.4). Removing a size-matched random subset of non-duplicated images instead produced the same gap, 33.5%, differing from the twin-removal arm by −0.02 percentage points (95% CI −3.1 to +3.1). We do not read either non-significant test as evidence of equivalence; the claim rests on the intervals, which bound whatever the duplicated items contribute at roughly three percentage points of a thirty-three-point gap, under a tenth of the effect and too little to carry item memorization as the explanation. That control refuted our own hypothesis. A second experiment, training instead on the non-overlapping D-Fire corpus, reduced the gap by 69.5% (t = 13.65, p = 7.8 × 10⁻¹⁰); changing the training corpus changes more than its provenance, so we do not treat this as isolating provenance as a cause. The pair of results is inconsistent with a simple item-memorization explanation and shows the gap depends strongly on which corpus the model was trained on.

Two scope limits apply. Only one paper in our audited corpus uses either of these corpora, so this analysis does not explain the corpus-level reporting result and is not offered as its mechanism. And the relationship between the two corpora is overlap, not leakage: separate publication alone does not establish a training-test relationship. We reserve leakage for the three pairs that cross the training and test partitions of a single dataset's own designated split.

Images were compared using 64-bit difference and perceptual hashes with a Hamming distance threshold of five, and candidate pairs confirmed by normalized cross-correlation at or above 0.95 on 32 × 32 grayscale. Confirmed pairs were classified by identity, by locus, and by consequence. Pairs crossing the training and test partitions of one dataset are labeled leakage; pairs spanning two separately published corpora are labeled overlap.

Both experiments train one ResNet-18 on a fixed schedule and report recall on FireNET, partitioned into the subset with a DeepQuestAI near-duplicate and the remainder; the reported gap is recall on the overlapping subset minus recall on the remainder. The first compares three training pools over ten seeds each — the unmodified DeepQuestAI pool, the same pool with the duplicated items removed, and a size-matched random removal drawn independently per seed — and the second substitutes the non-overlapping D-Fire corpus, holding architecture, schedule, training-set size and evaluation fixed. Architecture and optimization settings, arm sizes, the Welch test applied to the per-seed gaps, software versions and the exact commands are in the supplementary materials.

The protocol paragraphs below stood in the manuscript's Experimental procedures until
2026-09-20 and are reproduced unchanged.

Both experiments use a single architecture, ResNet-18 initialized from ImageNet-pretrained weights, with the final layer replaced for binary classification. Images were resized to 224 × 224 and normalized with ImageNet statistics; training augmentation was limited to random horizontal flipping. Optimization used AdamW with a learning rate of 3 × 10⁻⁴, weight decay 10⁻⁴, batch size 32, and a cosine annealing schedule over 12 epochs. Each run drew 1800 training items. Ten seeds were run per arm, with the seed controlling weight initialization, data ordering, and any sampling.

The first experiment has three arms sharing one test set, the FireNET corpus, partitioned into the subset with a DeepQuestAI near-duplicate and the remainder. The full arm trains on the unmodified DeepQuestAI training pool. The removal arm deletes the duplicated items. The placebo arm deletes a size-matched random subset drawn independently per seed. Thirty runs in total. The outcome is recall on FireNET, and the reported gap is recall on the overlapping subset minus recall on the remainder. Arms were compared by Welch's two-sample t-test on the per-seed gaps, ten observations per arm.

The second experiment replaces the training corpus with D-Fire, which has no measured overlap with the test set, holding architecture, schedule, training-set size and evaluation fixed. Ten runs. The same gap definition and test apply, compared against the full arm of the first experiment.

### S5.1 Arms and outcomes

| arm | seeds | mean gap (pp) | sd (pp) |
|---|---|---|---|
| full pool (unmodified DeepQuestAI) | 10 | 33.028 | 2.777 |
| duplicated items removed | 10 | 33.479 | 3.524 |
| placebo: size-matched random removal | 10 | 33.500 | 3.128 |

| contrast | difference (pp) | 95% CI (pp) |
|---|---|---|
| duplicates removed vs full pool | +0.45 | -2.5 to +3.4 |
| duplicates removed vs placebo | -0.02 | -3.1 to +3.1 |

Second experiment, training on the non-overlapping D-Fire corpus: mean gap 10.088 pp against 33.028 pp for the full arm, a reduction of 69.5%.

Neither non-significant test is read as evidence of equivalence. The claim rests on the
intervals, which bound whatever the duplicated items contribute at roughly three
percentage points of a thirty-three-point gap.

### S5.2 Software and commands

```
python scripts/decontamination_experiment.py   # first experiment, 30 runs
python scripts/placebo_bound.py                # arm contrasts and intervals
python scripts/provenance_control.py           # second experiment, 10 runs
python scripts/overlap_audit.py                # perceptual-hash overlap measurement
python scripts/contamination_taxonomy.py       # pair classification
```

Python 3.13.1 on the recorded environment. Per-run outputs are in
`corpus/decontamination_results.json`, `corpus/placebo_bound.json` and
`corpus/provenance_control_results.json`.

## S6. The coding instrument, the coders, and blinding

The instrument was frozen before any of the 67 papers was coded. These files carry the
rubric, the coder brief that served as the prompt, and the excerpt construction, and are
hashed in `corpus/INSTRUMENT_FREEZE.json`:

- `RUBRIC.md`
- `notes/CODER_BRIEF_67.md`
- `PRE_CODING_FREEZE.md`
- `corpus/to_code.json`
- `scripts/prep_coding.py`
- `corpus/scope_final.json`

Two coding roles, each of four instances, coded 67 papers across
4 disjoint shards assigned by a deterministic hash of the paper
identifier, so every paper received exactly one code from each role and no paper was
singly coded.

| role | shard | papers | completed | blinding evidence |
|---|---|---|---|---|
| A | 0 | 17 | 2026-09-11T10:24:48 | UNAVAILABLE - transcript truncated on completion |
| A | 1 | 17 | 2026-09-11T10:17:15 | UNAVAILABLE - transcript truncated on completion |
| A | 2 | 17 | 2026-09-11T10:12:35 | UNAVAILABLE - transcript truncated on completion |
| A | 3 | 16 | 2026-09-11T10:18:22 | UNAVAILABLE - transcript truncated on completion |
| B | 0 | 17 | 2026-09-11T10:22:48 | UNAVAILABLE - transcript truncated on completion |
| B | 1 | 17 | 2026-09-11T10:14:07 | transcript captured live |
| B | 2 | 17 | 2026-09-11T10:12:44 | UNAVAILABLE - transcript truncated on completion |
| B | 3 | 16 | 2026-09-11T10:19:48 | UNAVAILABLE - transcript truncated on completion |

Blinding was verified directly for 1 of the 8 coding instances.
For the rest the execution environment did not retain the transcript, so independence
rests on structural controls: outputs were written once at completion, shard boundaries
were disjoint, and agreement within each shard pair shows no anomaly. This is stated as a
limit rather than resolved.

The instrument was applied by 8 instances of a Claude large
language model, accessed through the Claude Code command-line interface, in 2 roles over
4 disjoint shards, completing between 2026-09-11T10:12:35 and 2026-09-11T10:24:48. The family and the
access route are attested by the operator and corroborated by the execution artifacts:
every instance's transcript is a harness output file, and seven of the eight were
truncated to zero bytes on completion, which is that harness's behaviour.

The version is not recoverable, and no version is stated. No version identifier was
written to `corpus/coder_provenance.json`, `corpus/INSTRUMENT_FREEZE.json` or the raw
coding rows, which carry only the role letter; the one transcript that escaped truncation
is no longer present on disk; and the session records for the coding date show two
different model versions in use that day, so no version can be inferred from an adjacent
run. An identifier is therefore given to the precision the record supports and no
further. Inventing one after the fact would be worse than the gap, and in a paper about
reconstructable method reporting it would be the same error the audit measures. What a
replicator can reproduce is the instrument, the prompts and the excerpt construction;
what they cannot reproduce is the exact model that read them.

### S6.1 The two referred cases, and how the coders decided them

Two disagreements were not settled in the reconciliation round and were referred
back to the two coders, who read the papers again and returned one agreed category
each. The referral asked for the boundary reasoning above the category itself, and
it is reproduced here as returned, with the deciding quotation each rests on.

The first is the corresponding author's own paper, which is the reason he declined
to classify it. The coders reached category 1 on it, the same category this study's
own coding records and on the same sentence, so the referral did not move the
endpoint. That is its outcome, not the reason it was referred.

**W4399615782 — agreed category 1, mechanism reported**

> "where \(D_t\) is the set of training image data taken as a randomly selected 80% of all available data"

The paper gives more than subset proportions: it explicitly states that the training images were randomly selected from all available data. Random assignment is a partition mechanism under the coding instructions. The paper later reports an 80:20 training/testing ratio and gives 4,493 training, 561 validation, and 561 testing images, but those statements do not remove the explicitly reported random-selection mechanism.

The boundary is therefore resolved in favor of category 1 rather than category 2. The instructions state that an explicit random assignment counts as a mechanism, and that if a rule is stated for one stage but not another, the paper is still coded 1, with the gap noted if needed.

**W4413480292 — agreed category 4, unresolved**

> "To ensure experimental consistency, we follow the data partitioning way proposed in [19]. Specifically, the dataset is divided into training, validation, and test sets in a ratio of 8:1:1, resulting in 2083 training images, 260 validation images, and 260 test images."

The paper gives the 8:1:1 proportions and corresponding counts, but it does not state within the paper how individual images were assigned to those sets. Instead, it explicitly says that it follows the partitioning method proposed in reference [19].

This places the paper on the category 4 rather than category 2 side of the boundary. Category 2 would apply if the paper merely reported ratios or counts with no assignment rule. Here, however, the paper explicitly defers the partitioning procedure to another work without stating that procedure. The coding instructions identify exactly this situation as category 4: a paper that "defers to another work ('we follow the protocol of [12]') without stating what that protocol was."

The fixed random seed reported later concerns model training and does not state how observations were assigned to the training, validation, and test sets. The partition statement itself therefore remains unresolved within the supplied paper.


Two defects were known before coding began and were carried rather than repaired,
because amending an instrument in response to data it has already produced is not a
repair:

- P1: FLAME block does not specify what to code for non-FLAME papers
- P2: four free-text fields scored as categories; kappa not meaningful on them

## S7. Partition-granularity experiment: secondary metrics

The primary metric in the manuscript is mAP@0.50 on the held-out test arm. The secondary
metrics fixed in section 4 of the protocol are reported here. The operating point is
chosen on the validation arm by maximizing F1 and is never chosen on test.

All 76 runs share one hyperparameter set and one inference configuration.

| model | partition | mAP@0.50 | mAP@0.50:0.95 | val F1-max threshold | test precision | test recall | test F1 |
|---|---|---|---|---|---|---|---|
| fasterrcnn | P1_random_image__seed20260911 | 0.3027 | 0.0992 | 0.3717 | 0.3842 | 0.3849 | 0.3845 |
| retinanet | P1_random_image__seed20260911 | 0.8127 | 0.4234 | 0.3965 | 0.7937 | 0.8021 | 0.7979 |
| yolov8n | P1_random_image__seed20260911 | 0.8156 | 0.4681 | 0.3564 | 0.8060 | 0.7932 | 0.7995 |
| yolov8s | P1_random_image__seed20260911 | 0.8280 | 0.5071 | 0.3215 | 0.8103 | 0.8262 | 0.8182 |
| fasterrcnn | P1_random_image__seed20260912 | 0.3108 | 0.1027 | 0.4311 | 0.4479 | 0.3613 | 0.3999 |
| retinanet | P1_random_image__seed20260912 | 0.8066 | 0.4188 | 0.4208 | 0.8105 | 0.7781 | 0.7940 |
| yolov8n | P1_random_image__seed20260912 | 0.8210 | 0.4745 | 0.2992 | 0.8050 | 0.8183 | 0.8116 |
| yolov8s | P1_random_image__seed20260912 | 0.8368 | 0.5104 | 0.3721 | 0.8326 | 0.8119 | 0.8221 |
| fasterrcnn | P1_random_image__seed20260913 | 0.3148 | 0.1032 | 0.3992 | 0.4294 | 0.3798 | 0.4031 |
| retinanet | P1_random_image__seed20260913 | 0.8051 | 0.4194 | 0.3739 | 0.7798 | 0.8040 | 0.7917 |
| yolov8n | P1_random_image__seed20260913 | 0.8076 | 0.4661 | 0.3506 | 0.8103 | 0.8011 | 0.8057 |
| yolov8s | P1_random_image__seed20260913 | 0.8272 | 0.5047 | 0.3382 | 0.8160 | 0.8176 | 0.8168 |
| fasterrcnn | P1_random_image__seed20260914 | 0.3253 | 0.1053 | 0.4301 | 0.4594 | 0.3654 | 0.4070 |
| retinanet | P1_random_image__seed20260914 | 0.8125 | 0.4161 | 0.4220 | 0.8071 | 0.7865 | 0.7967 |
| yolov8n | P1_random_image__seed20260914 | 0.8149 | 0.4664 | 0.2844 | 0.7900 | 0.8179 | 0.8037 |
| yolov8s | P1_random_image__seed20260914 | 0.8346 | 0.5059 | 0.3307 | 0.8217 | 0.8196 | 0.8206 |
| fasterrcnn | P1_random_image__seed20260915 | 0.3192 | 0.1011 | 0.4290 | 0.4394 | 0.3647 | 0.3985 |
| retinanet | P1_random_image__seed20260915 | 0.8155 | 0.4165 | 0.4144 | 0.8118 | 0.7973 | 0.8045 |
| yolov8n | P1_random_image__seed20260915 | 0.8296 | 0.4725 | 0.3103 | 0.8119 | 0.8224 | 0.8171 |
| yolov8s | P1_random_image__seed20260915 | 0.8434 | 0.5147 | 0.3846 | 0.8475 | 0.8211 | 0.8341 |
| fasterrcnn | P2_event_disjoint__seed20260911 | 0.1056 | 0.0246 | 0.2724 | 0.2289 | 0.1905 | 0.2079 |
| retinanet | P2_event_disjoint__seed20260911 | 0.5849 | 0.2574 | 0.3543 | 0.6933 | 0.5851 | 0.6346 |
| yolov8n | P2_event_disjoint__seed20260911 | 0.5527 | 0.2650 | 0.2244 | 0.6978 | 0.5580 | 0.6201 |
| yolov8s | P2_event_disjoint__seed20260911 | 0.5695 | 0.2943 | 0.1771 | 0.7163 | 0.5722 | 0.6362 |
| fasterrcnn | P2_event_disjoint__seed20260912 | 0.0981 | 0.0269 | 0.2505 | 0.1983 | 0.1817 | 0.1896 |
| retinanet | P2_event_disjoint__seed20260912 | 0.5483 | 0.2249 | 0.3638 | 0.6291 | 0.5956 | 0.6119 |
| yolov8n | P2_event_disjoint__seed20260912 | 0.5145 | 0.2398 | 0.1397 | 0.5747 | 0.5675 | 0.5711 |
| yolov8s | P2_event_disjoint__seed20260912 | 0.5354 | 0.2664 | 0.1940 | 0.6337 | 0.5713 | 0.6009 |
| fasterrcnn | P2_event_disjoint__seed20260913 | 0.1028 | 0.0246 | 0.3087 | 0.2275 | 0.1742 | 0.1973 |
| retinanet | P2_event_disjoint__seed20260913 | 0.5943 | 0.2517 | 0.3251 | 0.6790 | 0.6158 | 0.6458 |
| yolov8n | P2_event_disjoint__seed20260913 | 0.5753 | 0.2665 | 0.1206 | 0.6478 | 0.6137 | 0.6303 |
| yolov8s | P2_event_disjoint__seed20260913 | 0.6144 | 0.3131 | 0.2331 | 0.7554 | 0.6020 | 0.6700 |
| fasterrcnn | P2_event_disjoint__seed20260914 | 0.1074 | 0.0294 | 0.2534 | 0.2079 | 0.2080 | 0.2079 |
| retinanet | P2_event_disjoint__seed20260914 | 0.5670 | 0.2554 | 0.2842 | 0.6087 | 0.6386 | 0.6233 |
| yolov8n | P2_event_disjoint__seed20260914 | 0.5381 | 0.2655 | 0.1577 | 0.6411 | 0.5748 | 0.6061 |
| yolov8s | P2_event_disjoint__seed20260914 | 0.5574 | 0.2977 | 0.1449 | 0.6632 | 0.6007 | 0.6304 |
| fasterrcnn | P2_event_disjoint__seed20260915 | 0.0980 | 0.0284 | 0.1763 | 0.1745 | 0.2155 | 0.1928 |
| retinanet | P2_event_disjoint__seed20260915 | 0.5928 | 0.2495 | 0.2892 | 0.6456 | 0.6449 | 0.6453 |
| yolov8n | P2_event_disjoint__seed20260915 | 0.5325 | 0.2466 | 0.1316 | 0.6275 | 0.5719 | 0.5984 |
| yolov8s | P2_event_disjoint__seed20260915 | 0.5830 | 0.2870 | 0.1272 | 0.6651 | 0.6158 | 0.6395 |
| fasterrcnn | P3_camera_disjoint__seed20260911 | 0.0705 | 0.0175 | 0.1505 | 0.1266 | 0.1822 | 0.1494 |
| retinanet | P3_camera_disjoint__seed20260911 | 0.4839 | 0.2142 | 0.2359 | 0.5139 | 0.5924 | 0.5503 |
| yolov8n | P3_camera_disjoint__seed20260911 | 0.3910 | 0.1963 | 0.0456 | 0.4676 | 0.4883 | 0.4777 |
| yolov8s | P3_camera_disjoint__seed20260911 | 0.4639 | 0.2430 | 0.0496 | 0.5498 | 0.5568 | 0.5533 |
| fasterrcnn | P3_camera_disjoint__seed20260912 | 0.0501 | 0.0139 | 0.3503 | 0.2081 | 0.0787 | 0.1142 |
| retinanet | P3_camera_disjoint__seed20260912 | 0.5205 | 0.2210 | 0.2539 | 0.6360 | 0.5516 | 0.5908 |
| yolov8n | P3_camera_disjoint__seed20260912 | 0.3443 | 0.1651 | 0.0255 | 0.4134 | 0.4414 | 0.4269 |
| yolov8s | P3_camera_disjoint__seed20260912 | 0.3700 | 0.1926 | 0.0120 | 0.4757 | 0.4663 | 0.4709 |
| fasterrcnn | P3_camera_disjoint__seed20260913 | 0.0217 | 0.0103 | 0.1963 | 0.0779 | 0.0503 | 0.0611 |
| retinanet | P3_camera_disjoint__seed20260913 | 0.3832 | 0.1505 | 0.2111 | 0.5632 | 0.4120 | 0.4759 |
| yolov8n | P3_camera_disjoint__seed20260913 | 0.2115 | 0.0857 | 0.0537 | 0.4607 | 0.2294 | 0.3063 |
| yolov8s | P3_camera_disjoint__seed20260913 | 0.2667 | 0.1197 | 0.0414 | 0.4922 | 0.2977 | 0.3710 |
| fasterrcnn | P3_camera_disjoint__seed20260914 | 0.0675 | 0.0195 | 0.1155 | 0.1001 | 0.1824 | 0.1293 |
| retinanet | P3_camera_disjoint__seed20260914 | 0.4947 | 0.2261 | 0.2532 | 0.5466 | 0.5792 | 0.5624 |
| yolov8n | P3_camera_disjoint__seed20260914 | 0.3766 | 0.1835 | 0.0544 | 0.4661 | 0.4828 | 0.4743 |
| yolov8s | P3_camera_disjoint__seed20260914 | 0.4267 | 0.2221 | 0.0583 | 0.5677 | 0.5010 | 0.5322 |
| fasterrcnn | P3_camera_disjoint__seed20260915 | 0.0243 | 0.0071 | 0.3100 | 0.1241 | 0.0396 | 0.0601 |
| retinanet | P3_camera_disjoint__seed20260915 | 0.4343 | 0.1696 | 0.2312 | 0.5741 | 0.4560 | 0.5082 |
| yolov8n | P3_camera_disjoint__seed20260915 | 0.3020 | 0.1271 | 0.1168 | 0.5667 | 0.2940 | 0.3872 |
| yolov8s | P3_camera_disjoint__seed20260915 | 0.3191 | 0.1416 | 0.1026 | 0.5865 | 0.2875 | 0.3859 |
| fasterrcnn | P4_partner_lopo__seed20260911 | 0.0478 | 0.0145 | 0.2315 | 0.1227 | 0.1117 | 0.1169 |
| retinanet | P4_partner_lopo__seed20260911 | 0.4276 | 0.1851 | 0.4168 | 0.5182 | 0.5297 | 0.5239 |
| yolov8n | P4_partner_lopo__seed20260911 | 0.2824 | 0.1364 | 0.1470 | 0.4033 | 0.3732 | 0.3877 |
| yolov8s | P4_partner_lopo__seed20260911 | 0.3569 | 0.1803 | 0.1590 | 0.5443 | 0.4105 | 0.4680 |
| fasterrcnn | P4_partner_lopo__seed20260912 | 0.0296 | 0.0093 | 0.3047 | 0.1646 | 0.0419 | 0.0668 |
| retinanet | P4_partner_lopo__seed20260912 | 0.3570 | 0.1392 | 0.3028 | 0.6400 | 0.3322 | 0.4374 |
| yolov8n | P4_partner_lopo__seed20260912 | 0.2600 | 0.1113 | 0.0973 | 0.5878 | 0.2366 | 0.3374 |
| yolov8s | P4_partner_lopo__seed20260912 | 0.2645 | 0.1199 | 0.0592 | 0.5540 | 0.2656 | 0.3591 |
| fasterrcnn | P4_partner_lopo__seed20260913 | 0.0071 | 0.0017 | 0.2732 | 0.0705 | 0.0264 | 0.0384 |
| retinanet | P4_partner_lopo__seed20260913 | 0.3318 | 0.1287 | 0.3002 | 0.4628 | 0.3979 | 0.4279 |
| yolov8n | P4_partner_lopo__seed20260913 | 0.1222 | 0.0531 | 0.1899 | 0.5395 | 0.1121 | 0.1856 |
| yolov8s | P4_partner_lopo__seed20260913 | 0.2001 | 0.0875 | 0.1381 | 0.4541 | 0.2353 | 0.3100 |
| fasterrcnn | P5_temporal__seed20260911 | 0.0506 | 0.0123 | 0.2458 | 0.1529 | 0.1309 | 0.1411 |
| retinanet | P5_temporal__seed20260911 | 0.3954 | 0.1722 | 0.3596 | 0.5517 | 0.4301 | 0.4833 |
| yolov8n | P5_temporal__seed20260911 | 0.3468 | 0.1580 | 0.1936 | 0.5524 | 0.4125 | 0.4723 |
| yolov8s | P5_temporal__seed20260911 | 0.3556 | 0.1768 | 0.1182 | 0.5478 | 0.4244 | 0.4783 |

The Faster R-CNN arm sits far below the other three at every rung. That is a property of
the configuration the protocol fixed — a mobile backbone at 416 pixels on a schedule
derived from the YOLO arms — and not a finding about the architecture. It is constant
across partitions, so it enters the rank statistics as a full member while supporting no
comparative claim about detectors.

## S8. The audited corpus

All 85 papers that passed the scope screen, with the category each
received on the central classification. 79 of them train a learned model and
carry a category; the remaining 6 are threshold or index
algorithms that do not, and are excluded from the partition estimands by a rule fixed in
advance. The article's own reference list contains none of these papers: it cites the
works its argument engages with, and this is the evidence base the estimates are
computed over. Both are needed to check the result.

Identifiers are OpenAlex work IDs. Ordered by year, then by identifier.

| # | paper | year | venue | DOI | category |
|---|---|---|---|---|---|
| 1 | A classification scheme to determine wildfires from the satellite record in the cool grasslands of southern Canada: considerations for fire occurrence modelling and warning criteria | 2020 | Natural hazards and earth system sciences | [10.5194/nhess-20-3439-2020](https://doi.org/10.5194/nhess-20-3439-2020) | no partition statement |
| 2 | Early Fire Detection Based on Aerial 360-Degree Sensors, Deep Convolution Neural Networks and Exploitation of Fire Dynamic Textures | 2020 | Remote Sensing | [10.3390/rs12193177](https://doi.org/10.3390/rs12193177) | mechanism reported |
| 3 | Ground-Based Corroboration of GOES-17 Fire Detection Capabilities During Ignition of the Kincade Fire | 2020 | Journal of Operational Meteorology | [10.15191/nwajom.2020.0808](https://doi.org/10.15191/nwajom.2020.0808) | not a learned model |
| 4 | Forest Fire Detection System using ZigBee | 2020 | International Journal of Engineering and Advanced Technology | [10.35940/ijeat.f1212.089620](https://doi.org/10.35940/ijeat.f1212.089620) | not a learned model |
| 5 | ATT Squeeze U-Net: A Lightweight Network for Forest Fire Detection and Recognition | 2021 | IEEE Access | [10.1109/access.2021.3050628](https://doi.org/10.1109/access.2021.3050628) | ratio or counts only |
| 6 | A Forest Fire Detection System Based on Ensemble Learning | 2021 | Forests | [10.3390/f12020217](https://doi.org/10.3390/f12020217) | ratio or counts only |
| 7 | Forest Fire Recognition Based on Feature Extraction from Multi-View Images | 2021 | Traitement du signal | [10.18280/ts.380324](https://doi.org/10.18280/ts.380324) | no partition statement |
| 8 | EdgeFireSmoke: A Novel Lightweight CNN Model for Real-Time Video Fire–Smoke Detection | 2022 | IEEE Transactions on Industrial Informatics | [10.1109/tii.2021.3138752](https://doi.org/10.1109/tii.2021.3138752) | mechanism reported |
| 9 | Real-Time Detection of Full-Scale Forest Fire Smoke Based on Deep Convolution Neural Network | 2022 | Remote Sensing | [10.3390/rs14030536](https://doi.org/10.3390/rs14030536) | mechanism reported |
| 10 | FIgLib & SmokeyNet: Dataset and Deep Learning Model for Real-Time Wildland Fire Smoke Detection | 2022 | Remote Sensing | [10.3390/rs14041007](https://doi.org/10.3390/rs14041007) | mechanism reported |
| 11 | Fire-Net: A Deep Learning Framework for Active Forest Fire Detection | 2022 | Journal of Sensors | [10.1155/2022/8044390](https://doi.org/10.1155/2022/8044390) | ratio or counts only |
| 12 | A Vision-Based Detection and Spatial Localization Scheme for Forest Fire Inspection from UAV | 2022 | Forests | [10.3390/f13030383](https://doi.org/10.3390/f13030383) | no partition statement |
| 13 | Deep Learning and Transformer Approaches for UAV-Based Wildfire Detection and Segmentation | 2022 | Sensors | [10.3390/s22051977](https://doi.org/10.3390/s22051977) | mechanism reported |
| 14 | Efficient Forest Fire Detection using Rule-Based Multi-color Space and Correlation Coefficient for Application in Unmanned Aerial Vehicles | 2022 | KSII Transactions on Internet and Information Systems | [10.3837/tiis.2022.02.002](https://doi.org/10.3837/tiis.2022.02.002) | not a learned model |
| 15 | Fire-YOLO: A Small Target Object Detection Method for Fire Inspection | 2022 | Sustainability | [10.3390/su14094930](https://doi.org/10.3390/su14094930) | mechanism reported |
| 16 | Forest fire detection system using wireless sensor networks and machine learning | 2022 | Scientific Reports | [10.1038/s41598-021-03882-9](https://doi.org/10.1038/s41598-021-03882-9) | mechanism reported |
| 17 | DeepFire: A Novel Dataset and Deep Transfer Learning Benchmark for Forest Fire Detection | 2022 | Mobile Information Systems | [10.1155/2022/5358359](https://doi.org/10.1155/2022/5358359) | ratio or counts only |
| 18 | A Small Target Forest Fire Detection Model Based on YOLOv5 Improvement | 2022 | Forests | [10.3390/f13081332](https://doi.org/10.3390/f13081332) | ratio or counts only |
| 19 | FFireNet: Deep Learning Based Forest Fire Classification and Detection in Smart Cities | 2022 | Symmetry | [10.3390/sym14102155](https://doi.org/10.3390/sym14102155) | ratio or counts only |
| 20 | High-Precision Real-Time Forest Fire Video Detection Using One-Class Model | 2022 | Forests | [10.3390/f13111826](https://doi.org/10.3390/f13111826) | mechanism reported |
| 21 | An Intelligent Wildfire Detection Approach through Cameras Based on Deep Learning | 2022 | Sustainability | [10.3390/su142315690](https://doi.org/10.3390/su142315690) | ratio or counts only |
| 22 | Wildland Fire Detection and Monitoring Using a Drone-Collected RGB/IR Image Dataset | 2022 | IEEE Access | [10.1109/access.2022.3222805](https://doi.org/10.1109/access.2022.3222805) | mechanism reported |
| 23 | CoFFI: an image classification GUI for forest fire imagery applying convolution neural networks | 2022 | Institutional Repositories DataBase (IRDB) | — | ratio or counts only |
| 24 | Ultra-Low-Power Architecture for the Detection and Notification of Wildfires Using the Internet of Things | 2023 | IoT | [10.3390/iot4010001](https://doi.org/10.3390/iot4010001) | not a learned model |
| 25 | Autonomous Satellite Wildfire Detection Using Hyperspectral Imagery and Neural Networks: A Case Study on Australian Wildfire | 2023 | Remote Sensing | [10.3390/rs15030720](https://doi.org/10.3390/rs15030720) | mechanism reported |
| 26 | An Improved Forest Fire Detection Method Based on the Detectron2 Model and a Deep Learning Approach | 2023 | Sensors | [10.3390/s23031512](https://doi.org/10.3390/s23031512) | no partition statement |
| 27 | Forest fire and smoke detection using deep learning-based learning without forgetting | 2023 | Fire Ecology | [10.1186/s42408-022-00165-0](https://doi.org/10.1186/s42408-022-00165-0) | ratio or counts only |
| 28 | Forest Fire Segmentation via Temporal Transformer from Aerial Images | 2023 | Forests | [10.3390/f14030563](https://doi.org/10.3390/f14030563) | ratio or counts only |
| 29 | Integrating Machine Learning and a Spatial Contextual Algorithm to Detect Wildfire from Himawari-8 Data in Southwest China | 2023 | Forests | [10.3390/f14050919](https://doi.org/10.3390/f14050919) | ratio or counts only |
| 30 | Tokenized Time-Series in Satellite Image Segmentation With Transformer Network for Active Fire Detection | 2023 | IEEE Transactions on Geoscience and Remote Sensing | [10.1109/tgrs.2023.3287498](https://doi.org/10.1109/tgrs.2023.3287498) | mechanism reported |
| 31 | Detection of Forest Fires through Deep Unsupervised Learning Modeling of Sentinel-1 Time Series | 2023 | ISPRS International Journal of Geo-Information | [10.3390/ijgi12080332](https://doi.org/10.3390/ijgi12080332) | mechanism reported |
| 32 | Study of the Application of FY-3D/MERSI-II Far-Infrared Data in Wildfire Monitoring | 2023 | Remote Sensing | [10.3390/rs15174228](https://doi.org/10.3390/rs15174228) | not a learned model |
| 33 | Fast Forest Fire Detection and Segmentation Application for UAV-Assisted Mobile Edge Computing System | 2023 | IEEE Internet of Things Journal | [10.1109/jiot.2023.3311950](https://doi.org/10.1109/jiot.2023.3311950) | ratio or counts only |
| 34 | Assessing the Effectiveness of YOLO Architectures for Smoke and Wildfire Detection | 2023 | IEEE Access | [10.1109/access.2023.3312217](https://doi.org/10.1109/access.2023.3312217) | ratio or counts only |
| 35 | An Efficient Forest Fire Detection Algorithm Using Improved YOLOv5 | 2023 | Forests | [10.3390/f14122440](https://doi.org/10.3390/f14122440) | ratio or counts only |
| 36 | LEF-YOLO: a lightweight method for intelligent detection of four extreme wildfires based on the YOLO framework | 2023 | International Journal of Wildland Fire | [10.1071/wf23044](https://doi.org/10.1071/wf23044) | ratio or counts only |
| 37 | Identification of Forest Fires in Satellite Images Using Machine Learning / Deep Learning Supported in Integrated Computer Systems | 2023 | Universidad Industrial de Santander | — | ratio or counts only |
| 38 | A Forest Fire Recognition Method Based on Modified Deep CNN Model | 2024 | Forests | [10.3390/f15010111](https://doi.org/10.3390/f15010111) | mechanism reported |
| 39 | SWVR: A Lightweight Deep Learning Algorithm for Forest Fire Detection and Recognition | 2024 | Forests | [10.3390/f15010204](https://doi.org/10.3390/f15010204) | ratio or counts only |
| 40 | FCLGYOLO: Feature Constraint and Local Guided Global Feature for Fire Detection in Unmanned Aerial Vehicle Imagery | 2024 | IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing | [10.1109/jstars.2024.3358544](https://doi.org/10.1109/jstars.2024.3358544) | ratio or counts only |
| 41 | CNTCB-YOLOv7: An Effective Forest Fire Detection Model Based on ConvNeXtV2 and CBAM | 2024 | Fire | [10.3390/fire7020054](https://doi.org/10.3390/fire7020054) | ratio or counts only |
| 42 | SegNet: A segmented deep learning based Convolutional Neural Network approach for drones wildfire detection | 2024 | Remote Sensing Applications Society and Environment | [10.1016/j.rsase.2024.101181](https://doi.org/10.1016/j.rsase.2024.101181) | ratio or counts only |
| 43 | Development of a deep learning-based surveillance system for forest fire detection and monitoring using UAV | 2024 | PLoS ONE | [10.1371/journal.pone.0299058](https://doi.org/10.1371/journal.pone.0299058) | ratio or counts only |
| 44 | FFYOLO: A Lightweight Forest Fire Detection Model Based on YOLOv8 | 2024 | Fire | [10.3390/fire7030093](https://doi.org/10.3390/fire7030093) | ratio or counts only |
| 45 | YOLO-Based Models for Smoke and Wildfire Detection in Ground and Aerial Images | 2024 | Fire | [10.3390/fire7040140](https://doi.org/10.3390/fire7040140) | ratio or counts only |
| 46 | Early Wildfire Detection and Distance Estimation Using Aerial Visible-Infrared Images | 2024 | IEEE Transactions on Industrial Electronics | [10.1109/tie.2024.3387089](https://doi.org/10.1109/tie.2024.3387089) | ratio or counts only |
| 47 | Forest Smoke-Fire Net (FSF Net): A Wildfire Smoke Detection Model That Combines MODIS Remote Sensing Images with Regional Dynamic Brightness Temperature Thresholds | 2024 | Forests | [10.3390/f15050839](https://doi.org/10.3390/f15050839) | unresolved |
| 48 | Robust Forest Fire Detection Method for Surveillance Systems Based on You Only Look Once Version 8 and Transfer Learning Approaches | 2024 | Processes | [10.3390/pr12051039](https://doi.org/10.3390/pr12051039) | ratio or counts only |
| 49 | Hyperparameter optimization of YOLOv8 for smoke and wildfire detection: Implications for agricultural and environmental safety | 2024 | Artificial Intelligence in Agriculture | [10.1016/j.aiia.2024.05.003](https://doi.org/10.1016/j.aiia.2024.05.003) | ratio or counts only |
| 50 | An open flame and smoke detection dataset for deep learning in remote sensing based fire detection | 2024 | Geo-spatial Information Science | [10.1080/10095020.2024.2347922](https://doi.org/10.1080/10095020.2024.2347922) | mechanism reported |
| 51 | Detecting Forest Fires in Southwest China From Remote Sensing Nighttime Lights Using the Random Forest Classification Model | 2024 | IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing | [10.1109/jstars.2024.3410172](https://doi.org/10.1109/jstars.2024.3410172) | ratio or counts only |
| 52 | RFWNet: A Multiscale Remote Sensing Forest Wildfire Detection Network With Digital Twinning, Adaptive Spatial Aggregation, and Dynamic Sparse Features | 2024 | IEEE Transactions on Geoscience and Remote Sensing | [10.1109/tgrs.2024.3412112](https://doi.org/10.1109/tgrs.2024.3412112) | ratio or counts only |
| 53 | Towards early forest fire detection and prevention using AI-powered drones and the IoT | 2024 | Internet of Things | [10.1016/j.iot.2024.101248](https://doi.org/10.1016/j.iot.2024.101248) | mechanism reported |
| 54 | LUFFD-YOLO: A Lightweight Model for UAV Remote Sensing Forest Fire Detection Based on Attention Mechanism and Multi-Level Feature Fusion | 2024 | Remote Sensing | [10.3390/rs16122177](https://doi.org/10.3390/rs16122177) | ratio or counts only |
| 55 | Enhancing Satellite-Based Wildfire Monitoring: Advanced Contextual Model Using Environmental and Structural Information | 2024 | IEEE Transactions on Geoscience and Remote Sensing | [10.1109/tgrs.2024.3418475](https://doi.org/10.1109/tgrs.2024.3418475) | mechanism reported |
| 56 | YOLO-ULNet: Ultralightweight Network for Real-Time Detection of Forest Fire on Embedded Sensing Devices | 2024 | IEEE Sensors Journal | [10.1109/jsen.2024.3416548](https://doi.org/10.1109/jsen.2024.3416548) | ratio or counts only |
| 57 | The Multi-Scale Depth-Separable Convolution Network for Fire and Smoke Detection | 2024 | Combustion Science and Technology | [10.1080/00102202.2024.2372689](https://doi.org/10.1080/00102202.2024.2372689) | mechanism reported |
| 58 | Efficient forest fire detection based on an improved YOLO model | 2024 | Visual Intelligence | [10.1007/s44267-024-00053-y](https://doi.org/10.1007/s44267-024-00053-y) | mechanism reported |
| 59 | Wildfire and smoke early detection for drone applications: A light-weight deep learning approach | 2024 | Engineering Applications of Artificial Intelligence | [10.1016/j.engappai.2024.108977](https://doi.org/10.1016/j.engappai.2024.108977) | ratio or counts only |
| 60 | Tiny-Object Detection Based on Optimized YOLO-CSQ for Accurate Drone Detection in Wildfire Scenarios | 2024 | Drones | [10.3390/drones8090454](https://doi.org/10.3390/drones8090454) | ratio or counts only |
| 61 | LD-YOLO: A Lightweight Dynamic Forest Fire and Smoke Detection Model with Dysample and Spatial Context Awareness Module | 2024 | Forests | [10.3390/f15091630](https://doi.org/10.3390/f15091630) | ratio or counts only |
| 62 | Deep learning with ensemble approach for early pile fire detection using aerial images | 2024 | Frontiers in Environmental Science | [10.3389/fenvs.2024.1440396](https://doi.org/10.3389/fenvs.2024.1440396) | ratio or counts only |
| 63 | FGYOLO: An Integrated Feature Enhancement Lightweight Unmanned Aerial Vehicle Forest Fire Detection Framework Based on YOLOv8n | 2024 | Forests | [10.3390/f15101823](https://doi.org/10.3390/f15101823) | mechanism reported |
| 64 | Revolutionizing Wildfire Detection Through UAV-Driven Fire Monitoring with a Transformer-Based Approach | 2024 | Fire | [10.3390/fire7120443](https://doi.org/10.3390/fire7120443) | no partition statement |
| 65 | Drone-Based Wildfire Detection with Multi-Sensor Integration | 2024 | Remote Sensing | [10.3390/rs16244651](https://doi.org/10.3390/rs16244651) | ratio or counts only |
| 66 | Development of a model for segmentation of forest fires on satellite images using neural network technologies | 2024 | Electronic Institutional Repository of Admiral Makarov National Shipbuilding University (Admiral Makarov National University of Shipbuilding) | — | no partition statement |
| 67 | Wildfire Detection and Mapping by Satellite With an Enhanced Configuration of the Normalized Hotspot Indices: Results From Sentinel-2 and Landsat 8/9 Data Integration | 2025 | IEEE Transactions on Geoscience and Remote Sensing | [10.1109/tgrs.2025.3528641](https://doi.org/10.1109/tgrs.2025.3528641) | not a learned model |
| 68 | A Comparative Analysis of YOLOv9, YOLOv10, YOLOv11 for Smoke and Fire Detection | 2025 | Fire | [10.3390/fire8010026](https://doi.org/10.3390/fire8010026) | ratio or counts only |
| 69 | Multiscale wildfire and smoke detection in complex drone forest environments based on YOLOv8 | 2025 | Scientific Reports | [10.1038/s41598-025-86239-w](https://doi.org/10.1038/s41598-025-86239-w) | ratio or counts only |
| 70 | Optimizing Deep Learning Models for Fire Detection, Classification, and Segmentation Using Satellite Images | 2025 | Fire | [10.3390/fire8020036](https://doi.org/10.3390/fire8020036) | ratio or counts only |
| 71 | Early Forest Fire Detection With UAV Image Fusion: A Novel Deep Learning Method Using Visible and Infrared Sensors | 2025 | IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing | [10.1109/jstars.2025.3541205](https://doi.org/10.1109/jstars.2025.3541205) | ratio or counts only |
| 72 | Active wildfire detection via satellite imagery and machine learning: an empirical investigation of Australian wildfires | 2025 | Natural Hazards | [10.1007/s11069-025-07163-w](https://doi.org/10.1007/s11069-025-07163-w) | no partition statement |
| 73 | A study of YOLO architectures for wildfire and smoke detection in ground and aerial imagery | 2025 | Results in Engineering | [10.1016/j.rineng.2025.104869](https://doi.org/10.1016/j.rineng.2025.104869) | ratio or counts only |
| 74 | Forest Fire Detection Algorithm Based on Improved YOLOv11n | 2025 | Sensors | [10.3390/s25102989](https://doi.org/10.3390/s25102989) | ratio or counts only |
| 75 | Research and application of deep learning object detection methods for forest fire smoke recognition | 2025 | Scientific Reports | [10.1038/s41598-025-98086-w](https://doi.org/10.1038/s41598-025-98086-w) | ratio or counts only |
| 76 | Federated Learning for Smart and Sustainable Forest Fire Detection in Green Internet of Things | 2025 | ESTIDAMAA. | [10.70470/estidamaa/2025/002](https://doi.org/10.70470/estidamaa/2025/002) | ratio or counts only |
| 77 | High-precision Wildfire Detection Algorithm Using an Enhanced You Only Look Once Model in a Jetson Xavier Environment | 2025 | Sensors and Materials | [10.18494/sam5716](https://doi.org/10.18494/sam5716) | ratio or counts only |
| 78 | F3-YOLO: A Robust and Fast Forest Fire Detection Model | 2025 | Forests | [10.3390/f16091368](https://doi.org/10.3390/f16091368) | unresolved |
| 79 | Comparative Assessment of YOLO Segmentation Extensions for Intelligent Fire Detection | 2025 | International Journal of Fire Science and Engineering | [10.7731/kifse.d14e3746](https://doi.org/10.7731/kifse.d14e3746) | ratio or counts only |
| 80 | Multimodal Wildfire Classification Using Synthetic Night-Vision-like and Thermal-Inspired Image Representations | 2026 | Fire | [10.3390/fire9030109](https://doi.org/10.3390/fire9030109) | mechanism reported |
| 81 | A Lightweight and Sustainable UAV-Based Forest Fire Detection Algorithm Based on an Improved YOLO11 Model | 2026 | Sustainability | [10.3390/su18052436](https://doi.org/10.3390/su18052436) | ratio or counts only |
| 82 | ASCA-YOLO: Adaptive Sparse and Context-Aware YOLO Algorithm for Forest Wildfire Detection | 2026 | Sensors | [10.3390/s26113444](https://doi.org/10.3390/s26113444) | mechanism reported |
| 83 | A Real-World Benchmark for Early Wildfire Detection Using Sequential Data with the PyroNear Dataset | 2026 | Electronics | [10.3390/electronics15122652](https://doi.org/10.3390/electronics15122652) | mechanism reported |
| 84 | Energy-Aware Edge Vision for Event-Level Fire Detection with YOLO-Equipped UAVs | 2026 | Drones | [10.3390/drones10070527](https://doi.org/10.3390/drones10070527) | mechanism reported |
| 85 | LRM-YOLO: A Lightweight YOLOv10n-Based Model for Forest Fire Smoke Detection in UAV Images | 2026 | Sensors | [10.3390/s26154887](https://doi.org/10.3390/s26154887) | ratio or counts only |

Category totals over the 79 learned-model papers: mechanism reported 23, ratio or counts only 47, no partition statement 7, unresolved 2.

## S9. The benchmark-adherence record, paper by paper

The 31 papers the FLAME accuracy comparison is computed over, with the
protocol each was classified as using and the evidence grade of the text that decided
it. 34 papers were classified in total; the 3 that report no
held-out headline accuracy are listed after the table and are in no numerator or
denominator of the comparison. This record is a targeted set assembled from one
dataset's citing literature and is not the audited corpus; its adherence rate and the
corpus adherence rate estimate different quantities and neither bounds the other.

| # | first author | year | venue | DOI | protocol | headline | evidence |
|---|---|---|---|---|---|---|---|
| 1 | Dutta | 2021 | IEEE CAIDA 2021 | [10.1109/CAIDA51941.2021.9425170](https://doi.org/10.1109/CAIDA51941.2021.9425170) | designated test set | 92.0 | full text, not re-read here |
| 2 | Shamsoshoara | 2021 | Computer Networks 193:108001 | [10.1016/j.comnet.2021.108001](https://doi.org/10.1016/j.comnet.2021.108001) | designated test set | 76.23 | full text read here |
| 3 | Treneska | 2021 | Proc. 18th Int. Conf. on Informatics and Information Technologies (CIIT-18), Skopje, pp. 6-7 | — | designated test set | 88.01 | secondary records only |
| 4 | Ghali | 2022 | Sensors 22(5):1977 | [10.3390/s22051977](https://doi.org/10.3390/s22051977) | designated test set | 85.12 | full text read here |
| 5 | Guan | 2022 | Remote Sensing 14(13):3159 | [10.3390/rs14133159](https://doi.org/10.3390/rs14133159) | subset of unclear provenance | 93.65 | full text read here |
| 6 | Li | 2022 | IEEE ISAS 2022 | [10.1109/ISAS55863.2022.9757053](https://doi.org/10.1109/ISAS55863.2022.9757053) | designated test set | 86.33 | full text, not re-read here |
| 7 | Li | 2022 | IEEE ISAS 2022 | [10.1109/ISAS55863.2022.9757318](https://doi.org/10.1109/ISAS55863.2022.9757318) | designated test set | 82.3 | full text, not re-read here |
| 8 | Yan | 2022 | Forests 14(1):52 | [10.3390/f14010052](https://doi.org/10.3390/f14010052) | designated test set | 63.9 | full text read here |
| 9 | Zhang | 2022 | Forests 13(7):975 | [10.3390/f13070975](https://doi.org/10.3390/f13070975) | designated test set | 79.48 | full text read here |
| 10 | Bahhar | 2023 | Electronics 12(1):228 | [10.3390/electronics12010228](https://doi.org/10.3390/electronics12010228) | internally inconsistent | 99.3 | full text read here |
| 11 | Deng | 2023 | IEEE PRML 2023 | [10.1109/PRML59573.2023.10348345](https://doi.org/10.1109/PRML59573.2023.10348345) | designated test set | 86.14 | full text, not re-read here |
| 12 | Islam | 2023 | Forests 14(10):2080 | [10.3390/f14102080](https://doi.org/10.3390/f14102080) | pooled k-fold | 97.45 | full text read here |
| 13 | Kurasinski | 2023 | Wireless Personal Communications 130(2):1085 | [10.1007/s11277-023-10321-7](https://doi.org/10.1007/s11277-023-10321-7) | random re-split | 99.0 | full text read here |
| 14 | Namburu | 2023 | Electronics 12(3):733 | [10.3390/electronics12030733](https://doi.org/10.3390/electronics12030733) | subset of unclear provenance | 97.22 | full text read here |
| 15 | Reis | 2023 | Applied Soft Computing 143:110362 | [10.1016/j.asoc.2023.110362](https://doi.org/10.1016/j.asoc.2023.110362) | subset of unclear provenance | 99.32 | full text read here |
| 16 | Wang | 2023 | Geographical Bulletin 64(2) | — | random re-split | 99.19 | abstract only |
| 17 | Wang | 2023 | IEEE Access 11:32671-32681 | [10.1109/ACCESS.2023.3262701](https://doi.org/10.1109/ACCESS.2023.3262701) | subset of unclear provenance | 91.2 | full text, not re-read here |
| 18 | Arunkumar | 2024 | IEEE COMPSAC 2024 | [10.1109/COMPSAC61105.2024.00260](https://doi.org/10.1109/COMPSAC61105.2024.00260) | random re-split | 98.1 | full text, not re-read here |
| 19 | Fahim-Ul-Islam | 2024 | IEEE J. Sel. Top. Appl. Earth Obs. Remote Sens. 17 | [10.1109/jstars.2024.3450714](https://doi.org/10.1109/jstars.2024.3450714) | internally inconsistent | 98.1 | full text read here |
| 20 | Joshi | 2024 | Frontiers in Environmental Science 12:1440396 | [10.3389/fenvs.2024.1440396](https://doi.org/10.3389/fenvs.2024.1440396) | designated test set | 77.37 | full text read here |
| 21 | Khan | 2024 | Electronics 13(10):1881 | [10.3390/electronics13101881](https://doi.org/10.3390/electronics13101881) | designated test set | 87.32 | full text read here |
| 22 | Li | 2024 | Remote Sensing 16(15):2846 | [10.3390/rs16152846](https://doi.org/10.3390/rs16152846) | subset of unclear provenance | 98.18 | full text read here |
| 23 | Liang | 2024 | Sensors 24(7):2265 | [10.3390/s24072265](https://doi.org/10.3390/s24072265) | designated test set | 82.6 | full text read here |
| 24 | Mowla | 2024 | IEEE Access 13:3412-3433 | [10.1109/access.2024.3524320](https://doi.org/10.1109/access.2024.3524320) | random re-split | 99.83 | full text, not re-read here |
| 25 | Ramadan | 2024 | Internet of Things 27:101248 | [10.1016/j.iot.2024.101248](https://doi.org/10.1016/j.iot.2024.101248) | random re-split | 99.46 | full text read here |
| 26 | Yan | 2024 | Forests 15(10):1684 | [10.3390/f15101684](https://doi.org/10.3390/f15101684) | designated test set | 78.36 | full text read here |
| 27 | Zhao | 2024 | IEEE/RSJ IROS 2024 | [10.1109/iros58592.2024.10801629](https://doi.org/10.1109/iros58592.2024.10801629) | designated test set | 82.84 | full text read here |
| 28 | Bai | 2025 | IEEE J. Sel. Top. Appl. Earth Obs. Remote Sens. | [10.1109/jstars.2026.3685660](https://doi.org/10.1109/jstars.2026.3685660) | designated test set | 82.84 | full text read here |
| 29 | Deng | 2025 | Soft Computing 29(4):2363 | [10.1007/s00500-025-10512-3](https://doi.org/10.1007/s00500-025-10512-3) | designated test set | 88.05 | full text read here |
| 30 | Zhang | 2025 | Forests 16(3):544 | [10.3390/f16030544](https://doi.org/10.3390/f16030544) | designated test set | 89.42 | full text read here |
| 31 | Yar | 2026 | Remote Sensing 18(16):2706 | [10.3390/rs18162706](https://doi.org/10.3390/rs18162706) | designated test set | 87.81 | full text read here |

Of the 31, 18 use the designated camera-disjoint test set and
13 substitute a partition of their own, the latter being the four non-designated labels combined: random re-split 5, subset of unclear provenance 5, pooled k-fold 1, internally inconsistent 2.

Evidence grades over the same papers: abstract only 1, full text read here 22, full text, not re-read here 7, secondary records only 1. A grade below full text
read on our own machine is a limit on that row, not on the classification scheme, and
the rows carrying it are named here so the comparison can be recomputed without them.

Classified but reporting no held-out headline accuracy, and therefore excluded from the
comparison: Cheriguene (random re-split), Zachariadis (internally inconsistent), Le Hong (subset of unclear provenance).

## S10. Every reconciled disagreement, and what decided it

The 14 papers the two independent coders coded differently, with each
coder's category, the agreed category, and the reason recorded at the time. The
agreed category matches coder A's on 13 of them, coder B's alone on 0, and neither coder's on 1. That asymmetry is
reported in the article and is a property of this corpus and these two readers. It is
given case by case here so a reader can judge each decision rather than the ratio.

| paper | coder A | coder B | agreed | quotation behind the agreed category | how it was settled |
|---|---|---|---|---|---|
| W3090022951 | 1 mechanism reported | 3 no partition statement | 1 | Furthermore, we created a test 360-dataset (Figure 2), namely the “Fire detection 360-degree dataset” [52], consisting of 150 360-degree equirectangular images of forest and urban  [truncated] | Consensus 1. Approved by the corresponding author on the coding rule and the packet text; coder A had 1, coder B had 3. The validated author coding was not consulted. |
| W3186499362 | 3 no partition statement | 2 ratio or counts only | 3 | the adopted category is an absence code and carries no quotation | Consensus 3. Approved by the corresponding author on the coding rule and the packet text; coder A had 3, coder B had 2. The validated author coding was not consulted. |
| W4207031702 | 1 mechanism reported | 3 no partition statement | 1 | The training and testing data were randomly selected. | Consensus 1. Approved by the corresponding author on the coding rule and the packet text; coder A had 1, coder B had 3. The validated author coding was not consulted. |
| W4213193982 | 1 mechanism reported | 2 ratio or counts only | 1 | The Fire-Net model utilizes training data from the active fires in North America and Australia. | Consensus 1. Approved by the corresponding author on the coding rule and the packet text; coder A had 1, coder B had 2. The validated author coding was not consulted. |
| W4309091309 | 1 mechanism reported | 3 no partition statement | 1 | Under the guidance of GT, the training set is composed of two-class pixel-pattern samples, randomly drawn from the first frame. | Consensus 1. Approved by the corresponding author on the coding rule and the packet text; coder A had 1, coder B had 3. The validated author coding was not consulted. |
| W4312250248 | 2 ratio or counts only | 1 mechanism reported | 2 | we only used 1% randomly sampled data and split it model is suitable only under some weather and illumination into 80% to train and 20% to test. This operation can acceler- conditi [truncated] | Consensus 2. Approved by the corresponding author on the coding rule and the packet text; coder A had 2, coder B had 1. The validated author coding was not consulted. |
| W4386453639 | 3 no partition statement | 1 mechanism reported | 2 | neither coder's category was adopted; no coder quotation supports it | Consensus 2. Approved by the corresponding author on the coding rule and the packet text; coder A had 3, coder B had 1. The validated author coding was not consulted. |
| W4396605531 | 2 ratio or counts only | 4 unresolved | 2 | The dataset is separated into 70%, 20%, and 10% for training, validation, and test, separately. | Consensus 2. Approved by the corresponding author on the coding rule and the packet text; coder A had 2, coder B had 4. The validated author coding was not consulted. |
| W4399361386 | 1 mechanism reported | 2 ratio or counts only | 1 | Experiment configuration In our experiment, we follow the established random partitioning strategies (Agrawal, Girshick, and Malik 2014; Ma et al. | Consensus 1. Approved by the corresponding author on the coding rule and the packet text; coder A had 1, coder B had 2. The validated author coding was not consulted. |
| W4399615782 | 1 mechanism reported | 4 unresolved | 1 | We use [ ] , = argmin (2) ( ([]; ), []) , , [],[] where is the set of training image data taken as a randomly selected 80% of all available data, we do not only aim to find the opt [truncated] | Consensus 1. Agreed by the two independent coders on a fresh re-reading after referral, not decided on this side; coder A had 1, coder B had 4 before it. The deciding quotation and the boundary reasoning are recorded verbatim in referral_return.md. The validated author coding was not consulted. |
| W4400071697 | 1 mechanism reported | 2 ratio or counts only | 1 | taining 15 000 forest fire images was prepared to train and validate the performance of the designed YOLO-LNet on the 2) Neck: The neck has an MAFP structure containing a USP compu [truncated] | Consensus 1. Approved by the corresponding author on the coding rule and the packet text; coder A had 1, coder B had 2. The validated author coding was not consulted. |
| W4400354193 | 1 mechanism reported | 2 ratio or counts only | 1 | Afterward, these images were randomly allocated into training, validation and test set, following an 8:1:1 ratio. | Consensus 1. Approved by the corresponding author on the coding rule and the packet text; coder A had 1, coder B had 2. The validated author coding was not consulted. |
| W4413480292 | 4 unresolved | 2 ratio or counts only | 4 | follow the data partitioning way proposed in [19]. Specifically, the dataset is divided into training, validation, and test sets in a ratio of 8:1:1, resulting in 2083 training ima [truncated] | Consensus 4. Agreed by the two independent coders on a fresh re-reading after referral, not decided on this side; coder A had 4, coder B had 2 before it. The deciding quotation and the boundary reasoning are recorded verbatim in referral_return.md. The validated author coding was not consulted. |
| W7133383941 | 2 ratio or counts only | 4 unresolved | 2 | INE LEARNING/DEEP 31 Para el entrenamiento de las redes neuronales se asignaron 800 imágenes (80%) para entrenamiento y 200 (20%) para validación. | Consensus 2. Approved by the corresponding author on the coding rule and the packet text; coder A had 2, coder B had 4. The validated author coding was not consulted. |

Categories are 1 mechanism reported, 2 ratio or counts only, 3 no partition
statement, 4 unresolved. Quotations longer than 180 characters are marked
truncated; each is recorded in full, with both coders' quotations and the packet
passages both of them saw, in `human_coding/returned/reconciliation.csv`. Categories 3
and 4 are absence codes and are supported by the absence of a qualifying sentence in
the passages shown to both coders rather than by a quotation.

## S11. References cited only in this document

The article's reference list covers every work it cites.
The 5 works below are named only in the passages reproduced in S5,
and are given here so that nothing in this document is cited without a reference.

- Russakovsky, O., Deng, J., Su, H., Krause, J., Satheesh, S., Ma, S., Huang, Z., Karpathy, A., Khosla, A., Bernstein, M., et al. (2015). ImageNet Large Scale Visual Recognition Challenge. International Journal of Computer Vision 115, 211-252. https://doi.org/10.1007/s11263-015-0816-y
- Loshchilov, I., and Hutter, F. (2017). Decoupled Weight Decay Regularization. arXiv preprint. https://doi.org/10.48550/arXiv.1711.05101
- Barz, B., and Denzler, J. (2020). Do We Train on Test Data? Purging CIFAR of Near-Duplicates. Journal of Imaging 6, 41. https://doi.org/10.3390/jimaging6060041
- Lee, K., Ippolito, D., Nystrom, A., Zhang, C., Eck, D., Callison-Burch, C., and Carlini, N. (2022). Deduplicating Training Data Makes Language Models Better. Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), 8424-8445. https://doi.org/10.18653/v1/2022.acl-long.577
- He, K., Zhang, X., Ren, S., and Sun, J. (2016). Deep Residual Learning for Image Recognition. 2016 IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 770-778. https://doi.org/10.1109/CVPR.2016.90

## S10. Re-analyses reported in the ESWA version

Computed on 2026-11-18 from the stored per-run records, raw predictions, split files and images; no model was retrained. Analyses the protocol pre-specified are marked as such; the rest are post hoc. Scripts: `scripts/eswa_experiment_reanalysis.py`, `scripts/eswa_sample_design.py`, `scripts/eswa_flame_sensitivity.py`.

### S10.1 Detector ranking under mAP@0.50 and mAP@0.50:0.95 (pre-specified)

| rule | order under mAP@0.50 | order under mAP@0.50:0.95 |
|---|---|---|
| P1_random_image | yolov8s > yolov8n > retinanet > fasterrcnn | yolov8s > yolov8n > retinanet > fasterrcnn |
| P2_event_disjoint | retinanet > yolov8s > yolov8n > fasterrcnn | yolov8s > yolov8n > retinanet > fasterrcnn |
| P3_camera_disjoint | retinanet > yolov8s > yolov8n > fasterrcnn | retinanet > yolov8s > yolov8n > fasterrcnn |
| P4_partner_lopo | retinanet > yolov8s > yolov8n > fasterrcnn | retinanet > yolov8s > yolov8n > fasterrcnn |
| P5_temporal | retinanet > yolov8s > yolov8n > fasterrcnn | yolov8s > retinanet > yolov8n > fasterrcnn |

| rule pair | τ, mAP@0.50 | τ, mAP@0.50:0.95 | τ without Faster R-CNN, mAP@0.50 | τ without Faster R-CNN, mAP@0.50:0.95 |
|---|---|---|---|---|
| P1_random_image vs P2_event_disjoint | +0.33 | +1.00 | -0.33 | +1.00 |
| P1_random_image vs P3_camera_disjoint | +0.33 | +0.33 | -0.33 | -0.33 |
| P1_random_image vs P4_partner_lopo | +0.33 | +0.33 | -0.33 | -0.33 |
| P1_random_image vs P5_temporal | +0.33 | +0.67 | -0.33 | +0.33 |
| P2_event_disjoint vs P3_camera_disjoint | +1.00 | +0.33 | +1.00 | -0.33 |
| P2_event_disjoint vs P4_partner_lopo | +1.00 | +0.33 | +1.00 | -0.33 |
| P2_event_disjoint vs P5_temporal | +1.00 | +0.67 | +1.00 | +0.33 |
| P3_camera_disjoint vs P4_partner_lopo | +1.00 | +1.00 | +1.00 | +1.00 |
| P3_camera_disjoint vs P5_temporal | +1.00 | +0.67 | +1.00 | +0.33 |
| P4_partner_lopo vs P5_temporal | +1.00 | +0.67 | +1.00 | +0.33 |

### S10.2 Linear mixed model for the change in mAP@0.50 (pre-specified, E1)

Fixed effect: allocation rule (reference: random). Random intercepts: detector and replicate. Partner rule excluded (different training size). REML.

| detectors | term | estimate | 95% CI |
|---|---|---|---|
| all4 | Intercept | 0.694 | 0.507 to 0.881 |
| all4 | C(rule)[T.P2_event_disjoint] | -0.246 | -0.279 to -0.212 |
| all4 | C(rule)[T.P3_camera_disjoint] | -0.393 | -0.427 to -0.359 |
| all4 | C(rule)[T.P5_temporal] | -0.409 | -0.474 to -0.344 |
| working3 | Intercept | 0.821 | 0.784 to 0.858 |
| working3 | C(rule)[T.P2_event_disjoint] | -0.257 | -0.290 to -0.223 |
| working3 | C(rule)[T.P3_camera_disjoint] | -0.435 | -0.468 to -0.401 |
| working3 | C(rule)[T.P5_temporal] | -0.466 | -0.535 to -0.397 |

### S10.3 RetinaNet minus YOLOv8s, paired within replicate (t interval, post hoc)

| rule and metric | n | mean | 95% CI |
|---|---|---|---|
| P1_random_image, map_50 | 5 | -0.024 | -0.031 to -0.016 |
| P1_random_image, map_50_95 | 5 | -0.090 | -0.097 to -0.083 |
| P2_event_disjoint, map_50 | 5 | 0.005 | -0.013 to 0.024 |
| P2_event_disjoint, map_50_95 | 5 | -0.044 | -0.056 to -0.031 |
| P3_camera_disjoint, map_50 | 5 | 0.094 | 0.031 to 0.157 |
| P3_camera_disjoint, map_50_95 | 5 | 0.012 | -0.019 to 0.044 |
| P4_partner_lopo, map_50 | 3 | 0.098 | 0.022 to 0.175 |
| P4_partner_lopo, map_50_95 | 3 | 0.022 | -0.024 to 0.067 |
| P5_temporal, map_50 | 1 | 0.040 | single split, no interval |
| P5_temporal, map_50_95 | 1 | -0.005 | single split, no interval |

### S10.4 Complete separation of random-split and group-disjoint runs (post hoc)

| detector | random runs | group-disjoint runs | worst random run | best group-disjoint run |
|---|---|---|---|---|
| yolov8n | 5 | 14 | 0.8076 | 0.5753 |
| yolov8s | 5 | 14 | 0.8272 | 0.6144 |
| retinanet | 5 | 14 | 0.8051 | 0.5943 |
| fasterrcnn | 5 | 14 | 0.3027 | 0.1074 |

### S10.5 Test images with a confirmed near-duplicate in the training arm used (post hoc)

64-bit dHash or pHash within Hamming distance 5, confirmed by normalized cross-correlation ≥ 0.95 on 32×32 greyscale; the training arm is the matched subsample actually trained on.

| partition | test images | training images used | test images with a near-duplicate | share |
|---|---|---|---|---|
| P1_random_image__seed20260911 | 6728 | 21995 | 6365 | 94.6% |
| P1_random_image__seed20260912 | 6728 | 21995 | 6346 | 94.3% |
| P1_random_image__seed20260913 | 6728 | 21995 | 6343 | 94.3% |
| P1_random_image__seed20260914 | 6728 | 21995 | 6362 | 94.6% |
| P1_random_image__seed20260915 | 6728 | 21995 | 6362 | 94.6% |
| P2_event_disjoint__seed20260911 | 6718 | 21995 | 2237 | 33.3% |
| P2_event_disjoint__seed20260912 | 6836 | 21995 | 2496 | 36.5% |
| P2_event_disjoint__seed20260913 | 6721 | 21995 | 2279 | 33.9% |
| P2_event_disjoint__seed20260914 | 6737 | 21995 | 2128 | 31.6% |
| P2_event_disjoint__seed20260915 | 6757 | 21995 | 2432 | 36.0% |
| P3_camera_disjoint__seed20260911 | 5614 | 21995 | 90 | 1.6% |
| P3_camera_disjoint__seed20260912 | 5203 | 21995 | 0 | 0.0% |
| P3_camera_disjoint__seed20260913 | 7552 | 21995 | 61 | 0.8% |
| P3_camera_disjoint__seed20260914 | 6687 | 21995 | 3 | 0.0% |
| P3_camera_disjoint__seed20260915 | 6712 | 21995 | 0 | 0.0% |
| P4_partner_lopo__seed20260911 | 13768 | 13836 | 0 | 0.0% |
| P4_partner_lopo__seed20260912 | 17766 | 13836 | 0 | 0.0% |
| P4_partner_lopo__seed20260913 | 2102 | 13836 | 0 | 0.0% |
| P5_temporal__seed20260911 | 6728 | 21995 | 526 | 7.8% |

### S10.6 Event-level detection and false detections at the validation-chosen threshold (post hoc)

An event counts as detected if any of its smoke images carries a detection at or above the threshold with IoU ≥ 0.50 to an annotated box. A smoke-free image counts as a false detection if it carries any detection at or above the threshold.

| detector, rule, seed | threshold | test events with smoke | detected | event detection rate | smoke-free test images | with a detection | rate |
|---|---|---|---|---|---|---|---|
| fasterrcnn, P1_random_image, 20260911 | 0.372 | 807 | 457 | 56.6% | 1161 | 165 | 14.2% |
| fasterrcnn, P1_random_image, 20260912 | 0.431 | 798 | 445 | 55.8% | 1137 | 134 | 11.8% |
| fasterrcnn, P1_random_image, 20260913 | 0.399 | 789 | 447 | 56.7% | 1135 | 166 | 14.6% |
| fasterrcnn, P1_random_image, 20260914 | 0.430 | 792 | 443 | 55.9% | 1074 | 133 | 12.4% |
| fasterrcnn, P1_random_image, 20260915 | 0.429 | 796 | 437 | 54.9% | 1059 | 126 | 11.9% |
| fasterrcnn, P2_event_disjoint, 20260911 | 0.272 | 180 | 104 | 57.8% | 907 | 236 | 26.0% |
| fasterrcnn, P2_event_disjoint, 20260912 | 0.251 | 193 | 103 | 53.4% | 1218 | 355 | 29.1% |
| fasterrcnn, P2_event_disjoint, 20260913 | 0.309 | 197 | 95 | 48.2% | 1049 | 256 | 24.4% |
| fasterrcnn, P2_event_disjoint, 20260914 | 0.253 | 168 | 96 | 57.1% | 1014 | 354 | 34.9% |
| fasterrcnn, P2_event_disjoint, 20260915 | 0.176 | 187 | 122 | 65.2% | 1190 | 466 | 39.2% |
| fasterrcnn, P3_camera_disjoint, 20260911 | 0.150 | 153 | 75 | 49.0% | 1340 | 655 | 48.9% |
| fasterrcnn, P3_camera_disjoint, 20260912 | 0.350 | 151 | 44 | 29.1% | 603 | 121 | 20.1% |
| fasterrcnn, P3_camera_disjoint, 20260913 | 0.196 | 183 | 58 | 31.7% | 889 | 199 | 22.4% |
| fasterrcnn, P3_camera_disjoint, 20260914 | 0.115 | 180 | 89 | 49.4% | 1643 | 881 | 53.6% |
| fasterrcnn, P3_camera_disjoint, 20260915 | 0.310 | 200 | 49 | 24.5% | 868 | 72 | 8.3% |
| fasterrcnn, P4_partner_lopo, 20260911 | 0.232 | 417 | 165 | 39.6% | 3321 | 1142 | 34.4% |
| fasterrcnn, P4_partner_lopo, 20260912 | 0.305 | 393 | 91 | 23.2% | 1729 | 181 | 10.5% |
| fasterrcnn, P4_partner_lopo, 20260913 | 0.273 | 82 | 12 | 14.6% | 449 | 56 | 12.5% |
| fasterrcnn, P5_temporal, 20260911 | 0.246 | 245 | 77 | 31.4% | 1497 | 486 | 32.5% |
| retinanet, P1_random_image, 20260911 | 0.397 | 807 | 757 | 93.8% | 1161 | 190 | 16.4% |
| retinanet, P1_random_image, 20260912 | 0.421 | 798 | 732 | 91.7% | 1137 | 167 | 14.7% |
| retinanet, P1_random_image, 20260913 | 0.374 | 789 | 734 | 93.0% | 1135 | 190 | 16.7% |
| retinanet, P1_random_image, 20260914 | 0.422 | 792 | 732 | 92.4% | 1074 | 147 | 13.7% |
| retinanet, P1_random_image, 20260915 | 0.414 | 796 | 740 | 93.0% | 1059 | 160 | 15.1% |
| retinanet, P2_event_disjoint, 20260911 | 0.354 | 180 | 165 | 91.7% | 907 | 279 | 30.8% |
| retinanet, P2_event_disjoint, 20260912 | 0.364 | 193 | 172 | 89.1% | 1218 | 444 | 36.5% |
| retinanet, P2_event_disjoint, 20260913 | 0.325 | 197 | 176 | 89.3% | 1049 | 335 | 31.9% |
| retinanet, P2_event_disjoint, 20260914 | 0.284 | 168 | 158 | 94.0% | 1014 | 523 | 51.6% |
| retinanet, P2_event_disjoint, 20260915 | 0.289 | 187 | 173 | 92.5% | 1190 | 466 | 39.2% |
| retinanet, P3_camera_disjoint, 20260911 | 0.236 | 153 | 134 | 87.6% | 1340 | 663 | 49.5% |
| retinanet, P3_camera_disjoint, 20260912 | 0.254 | 151 | 126 | 83.4% | 603 | 260 | 43.1% |
| retinanet, P3_camera_disjoint, 20260913 | 0.211 | 183 | 159 | 86.9% | 889 | 165 | 18.6% |
| retinanet, P3_camera_disjoint, 20260914 | 0.253 | 180 | 167 | 92.8% | 1643 | 706 | 43.0% |
| retinanet, P3_camera_disjoint, 20260915 | 0.231 | 200 | 164 | 82.0% | 868 | 201 | 23.2% |
| retinanet, P4_partner_lopo, 20260911 | 0.417 | 417 | 359 | 86.1% | 3321 | 1730 | 52.1% |
| retinanet, P4_partner_lopo, 20260912 | 0.303 | 393 | 289 | 73.5% | 1729 | 349 | 20.2% |
| retinanet, P4_partner_lopo, 20260913 | 0.300 | 82 | 39 | 47.6% | 449 | 149 | 33.2% |
| retinanet, P5_temporal, 20260911 | 0.360 | 245 | 159 | 64.9% | 1497 | 642 | 42.9% |
| yolov8n, P1_random_image, 20260911 | 0.356 | 807 | 743 | 92.1% | 1161 | 335 | 28.9% |
| yolov8n, P1_random_image, 20260912 | 0.299 | 798 | 744 | 93.2% | 1137 | 339 | 29.8% |
| yolov8n, P1_random_image, 20260913 | 0.351 | 789 | 733 | 92.9% | 1135 | 306 | 27.0% |
| yolov8n, P1_random_image, 20260914 | 0.284 | 792 | 748 | 94.4% | 1074 | 370 | 34.5% |
| yolov8n, P1_random_image, 20260915 | 0.310 | 796 | 743 | 93.3% | 1059 | 323 | 30.5% |
| yolov8n, P2_event_disjoint, 20260911 | 0.224 | 180 | 161 | 89.4% | 907 | 372 | 41.0% |
| yolov8n, P2_event_disjoint, 20260912 | 0.140 | 193 | 177 | 91.7% | 1218 | 610 | 50.1% |
| yolov8n, P2_event_disjoint, 20260913 | 0.121 | 197 | 169 | 85.8% | 1049 | 518 | 49.4% |
| yolov8n, P2_event_disjoint, 20260914 | 0.158 | 168 | 156 | 92.9% | 1014 | 535 | 52.8% |
| yolov8n, P2_event_disjoint, 20260915 | 0.132 | 187 | 169 | 90.4% | 1190 | 572 | 48.1% |
| yolov8n, P3_camera_disjoint, 20260911 | 0.046 | 153 | 127 | 83.0% | 1340 | 672 | 50.1% |
| yolov8n, P3_camera_disjoint, 20260912 | 0.025 | 151 | 117 | 77.5% | 603 | 384 | 63.7% |
| yolov8n, P3_camera_disjoint, 20260913 | 0.054 | 183 | 130 | 71.0% | 889 | 256 | 28.8% |
| yolov8n, P3_camera_disjoint, 20260914 | 0.054 | 180 | 151 | 83.9% | 1643 | 864 | 52.6% |
| yolov8n, P3_camera_disjoint, 20260915 | 0.117 | 200 | 141 | 70.5% | 868 | 182 | 21.0% |
| yolov8n, P4_partner_lopo, 20260911 | 0.147 | 417 | 318 | 76.3% | 3321 | 1830 | 55.1% |
| yolov8n, P4_partner_lopo, 20260912 | 0.097 | 393 | 253 | 64.4% | 1729 | 342 | 19.8% |
| yolov8n, P4_partner_lopo, 20260913 | 0.190 | 82 | 21 | 25.6% | 449 | 28 | 6.2% |
| yolov8n, P5_temporal, 20260911 | 0.194 | 245 | 159 | 64.9% | 1497 | 673 | 45.0% |
| yolov8s, P1_random_image, 20260911 | 0.321 | 807 | 749 | 92.8% | 1161 | 328 | 28.3% |
| yolov8s, P1_random_image, 20260912 | 0.372 | 798 | 746 | 93.5% | 1137 | 284 | 25.0% |
| yolov8s, P1_random_image, 20260913 | 0.338 | 789 | 742 | 94.0% | 1135 | 285 | 25.1% |
| yolov8s, P1_random_image, 20260914 | 0.331 | 792 | 749 | 94.6% | 1074 | 299 | 27.8% |
| yolov8s, P1_random_image, 20260915 | 0.385 | 796 | 741 | 93.1% | 1059 | 262 | 24.7% |
| yolov8s, P2_event_disjoint, 20260911 | 0.177 | 180 | 167 | 92.8% | 907 | 333 | 36.7% |
| yolov8s, P2_event_disjoint, 20260912 | 0.194 | 193 | 174 | 90.2% | 1218 | 515 | 42.3% |
| yolov8s, P2_event_disjoint, 20260913 | 0.233 | 197 | 176 | 89.3% | 1049 | 378 | 36.0% |
| yolov8s, P2_event_disjoint, 20260914 | 0.145 | 168 | 152 | 90.5% | 1014 | 554 | 54.6% |
| yolov8s, P2_event_disjoint, 20260915 | 0.127 | 187 | 172 | 92.0% | 1190 | 544 | 45.7% |
| yolov8s, P3_camera_disjoint, 20260911 | 0.050 | 153 | 134 | 87.6% | 1340 | 726 | 54.2% |
| yolov8s, P3_camera_disjoint, 20260912 | 0.012 | 151 | 118 | 78.1% | 603 | 326 | 54.1% |
| yolov8s, P3_camera_disjoint, 20260913 | 0.041 | 183 | 137 | 74.9% | 889 | 286 | 32.2% |
| yolov8s, P3_camera_disjoint, 20260914 | 0.058 | 180 | 160 | 88.9% | 1643 | 706 | 43.0% |
| yolov8s, P3_camera_disjoint, 20260915 | 0.103 | 200 | 140 | 70.0% | 868 | 219 | 25.2% |
| yolov8s, P4_partner_lopo, 20260911 | 0.159 | 417 | 341 | 81.8% | 3321 | 1527 | 46.0% |
| yolov8s, P4_partner_lopo, 20260912 | 0.059 | 393 | 277 | 70.5% | 1729 | 448 | 25.9% |
| yolov8s, P4_partner_lopo, 20260913 | 0.138 | 82 | 37 | 45.1% | 449 | 85 | 18.9% |
| yolov8s, P5_temporal, 20260911 | 0.118 | 245 | 159 | 64.9% | 1497 | 731 | 48.8% |

### S10.7 Matched-image AP: the same test images scored by models trained under two rules (post hoc)

| detector, rule, seed | shared test images | mAP@0.50, random-rule model | mAP@0.50, group-disjoint model | difference |
|---|---|---|---|---|
| fasterrcnn, P2_event_disjoint, 20260911 | 1359 | 0.304 | 0.111 | 0.192 |
| fasterrcnn, P2_event_disjoint, 20260912 | 1374 | 0.279 | 0.101 | 0.178 |
| fasterrcnn, P2_event_disjoint, 20260913 | 1405 | 0.261 | 0.102 | 0.159 |
| fasterrcnn, P2_event_disjoint, 20260914 | 1385 | 0.329 | 0.099 | 0.229 |
| fasterrcnn, P2_event_disjoint, 20260915 | 1358 | 0.311 | 0.099 | 0.212 |
| fasterrcnn, P3_camera_disjoint, 20260911 | 1162 | 0.294 | 0.070 | 0.224 |
| fasterrcnn, P3_camera_disjoint, 20260912 | 1025 | 0.386 | 0.048 | 0.338 |
| fasterrcnn, P3_camera_disjoint, 20260913 | 1487 | 0.270 | 0.020 | 0.250 |
| fasterrcnn, P3_camera_disjoint, 20260914 | 1297 | 0.323 | 0.061 | 0.262 |
| fasterrcnn, P3_camera_disjoint, 20260915 | 1299 | 0.213 | 0.019 | 0.193 |
| fasterrcnn, P5_temporal, 20260911 | 1430 | 0.238 | 0.046 | 0.192 |
| retinanet, P2_event_disjoint, 20260911 | 1359 | 0.824 | 0.598 | 0.227 |
| retinanet, P2_event_disjoint, 20260912 | 1374 | 0.769 | 0.545 | 0.223 |
| retinanet, P2_event_disjoint, 20260913 | 1405 | 0.809 | 0.593 | 0.216 |
| retinanet, P2_event_disjoint, 20260914 | 1385 | 0.811 | 0.582 | 0.230 |
| retinanet, P2_event_disjoint, 20260915 | 1358 | 0.809 | 0.585 | 0.224 |
| retinanet, P3_camera_disjoint, 20260911 | 1162 | 0.796 | 0.502 | 0.293 |
| retinanet, P3_camera_disjoint, 20260912 | 1025 | 0.863 | 0.505 | 0.358 |
| retinanet, P3_camera_disjoint, 20260913 | 1487 | 0.813 | 0.373 | 0.440 |
| retinanet, P3_camera_disjoint, 20260914 | 1297 | 0.802 | 0.484 | 0.319 |
| retinanet, P3_camera_disjoint, 20260915 | 1299 | 0.794 | 0.459 | 0.335 |
| retinanet, P5_temporal, 20260911 | 1430 | 0.768 | 0.384 | 0.384 |
| yolov8n, P2_event_disjoint, 20260911 | 1359 | 0.824 | 0.561 | 0.262 |
| yolov8n, P2_event_disjoint, 20260912 | 1374 | 0.777 | 0.519 | 0.258 |
| yolov8n, P2_event_disjoint, 20260913 | 1405 | 0.823 | 0.574 | 0.249 |
| yolov8n, P2_event_disjoint, 20260914 | 1385 | 0.806 | 0.543 | 0.263 |
| yolov8n, P2_event_disjoint, 20260915 | 1358 | 0.810 | 0.532 | 0.278 |
| yolov8n, P3_camera_disjoint, 20260911 | 1162 | 0.798 | 0.381 | 0.416 |
| yolov8n, P3_camera_disjoint, 20260912 | 1025 | 0.843 | 0.333 | 0.510 |
| yolov8n, P3_camera_disjoint, 20260913 | 1487 | 0.808 | 0.199 | 0.609 |
| yolov8n, P3_camera_disjoint, 20260914 | 1297 | 0.795 | 0.359 | 0.436 |
| yolov8n, P3_camera_disjoint, 20260915 | 1299 | 0.805 | 0.312 | 0.493 |
| yolov8n, P5_temporal, 20260911 | 1430 | 0.750 | 0.320 | 0.430 |
| yolov8s, P2_event_disjoint, 20260911 | 1359 | 0.826 | 0.590 | 0.237 |
| yolov8s, P2_event_disjoint, 20260912 | 1374 | 0.806 | 0.535 | 0.270 |
| yolov8s, P2_event_disjoint, 20260913 | 1405 | 0.839 | 0.596 | 0.243 |
| yolov8s, P2_event_disjoint, 20260914 | 1385 | 0.840 | 0.582 | 0.258 |
| yolov8s, P2_event_disjoint, 20260915 | 1358 | 0.832 | 0.583 | 0.249 |
| yolov8s, P3_camera_disjoint, 20260911 | 1162 | 0.804 | 0.461 | 0.343 |
| yolov8s, P3_camera_disjoint, 20260912 | 1025 | 0.862 | 0.370 | 0.492 |
| yolov8s, P3_camera_disjoint, 20260913 | 1487 | 0.828 | 0.251 | 0.576 |
| yolov8s, P3_camera_disjoint, 20260914 | 1297 | 0.821 | 0.420 | 0.401 |
| yolov8s, P3_camera_disjoint, 20260915 | 1299 | 0.825 | 0.326 | 0.499 |
| yolov8s, P5_temporal, 20260911 | 1430 | 0.747 | 0.333 | 0.413 |

### S10.8 The audit's sampling design

Cleaned harvest 4,915; eligible 1,744; drawn 182; removed before the freeze 23 (most-cited half 16, random half 7); frozen frame 159 (most-cited 72, random 87). The sampling script contains a step that would have added one named paper had the draw not selected it; the draw selected it in the most-cited half, so the step did not run.

| stratum (modality, years) | eligible records | most-cited drawn | random drawn |
|---|---|---|---|
| edge, 2020-21 | 20 | 2 | 2 |
| edge, 2022-23 | 51 | 2 | 3 |
| edge, 2024-26 | 132 | 7 | 7 |
| iot, 2020-21 | 46 | 2 | 3 |
| iot, 2022-23 | 79 | 4 | 4 |
| iot, 2024-26 | 151 | 8 | 8 |
| satellite, 2020-21 | 65 | 3 | 4 |
| satellite, 2022-23 | 90 | 4 | 5 |
| satellite, 2024-26 | 149 | 7 | 8 |
| uav, 2020-21 | 39 | 2 | 2 |
| uav, 2022-23 | 108 | 5 | 6 |
| uav, 2024-26 | 252 | 13 | 13 |
| vision, 2020-21 | 59 | 3 | 3 |
| vision, 2022-23 | 156 | 8 | 8 |
| vision, 2024-26 | 347 | 18 | 18 |

| coding | half | lacking a reconstructable mechanism | % | Wilson 95% CI |
|---|---|---|---|---|
| author_validation | top_cited | 38 of 51 | 74.5 | 61.1–84.5 |
| author_validation | random | 16 of 28 | 57.1 | 39.1–73.5 |
| author_validation | ALL | 54 of 79 | 68.4 | 57.5–77.6 |
| human_consensus | top_cited | 35 of 51 | 68.6 | 55.0–79.7 |
| human_consensus | random | 15 of 28 | 53.6 | 35.8–70.5 |
| human_consensus | ALL | 50 of 79 | 63.3 | 52.3–73.1 |
| author_validation | sampled_only | 54 of 79 | 68.4 | 57.5–77.6 |
| human_consensus | sampled_only | 50 of 79 | 63.3 | 52.3–73.1 |
| author_validation | design-weighted | of 79 | 58.4 | 42.4–73.9 (bootstrap) |
| human_consensus | design-weighted | of 79 | 55.1 | 41.0–69.2 (bootstrap) |

### S10.9 FLAME comparison under removals (post hoc)

| set | designated / substituted | medians | pairs favouring the substituting paper | probability of superiority | exact Mann–Whitney p | Hodges–Lehmann shift (95% CI) |
|---|---|---|---|---|---|---|
| base | 18 / 13 | 83.98 / 98.18 | 233 of 234 | 0.996 | 1.9e-08 | 13.17 (10.99 to 16.70) |
| minus_weak_evidence | 16 / 11 | 82.84 / 98.10 | 176 of 176 | 1.000 | 1.5e-07 | 14.36 (11.12 to 17.42) |
| minus_non_test_headline | 18 / 9 | 83.98 / 98.18 | 161 of 162 | 0.994 | 8.5e-07 | 13.09 (10.29 to 17.00) |
| minus_weak_and_non_test | 16 / 8 | 82.84 / 98.14 | 128 of 128 | 1.000 | 2.7e-06 | 14.00 (10.78 to 18.62) |

Removed: minus_weak_evidence: Treneska 2021, Dutta 2021, Wang 2023, Reis 2023; minus_non_test_headline: Wang 2023, Namburu 2023, Kurasinski 2023, Islam 2023; minus_weak_and_non_test: Treneska 2021, Dutta 2021, Wang 2023, Namburu 2023, Kurasinski 2023, Reis 2023, Islam 2023. Removing any single paper leaves at most one pair favouring the designated-protocol paper.
