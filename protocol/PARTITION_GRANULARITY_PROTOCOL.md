# Partition-granularity protocol

Frozen design for the experimental extension. Nothing in this document may be changed after the
hash is recorded without a dated entry in `notes/AUDIT_TRAIL.md` stating what changed and why.

The question: **when the corpus, the learning procedure and the metric are held fixed, how does the
granularity of the evaluation partition affect (a) absolute performance and (b) which model appears
best?**

Two estimand families, kept separate throughout: score sensitivity and ranking sensitivity.

---

## 1. Scope, and what this design refuses to do

The experiment is run on **Pyro-SDIS only**. M4SFWD was specified as a second corpus conditional on
its licence and clip-group structure being verified. Both failed verification and it is excluded;
the reasoning is in `NOVELTY_AUDIT_PARTITION_EXPERIMENT.md`, which also records that an earlier
version of this project's own notes asserted M4SFWD's grouping as established while the same table
marked it unverified.

No grouping used here is inferred from image content. Every rung comes from a typed column the
dataset distributes.

Ranking reversal is **not** a success condition. Section 9 states in advance what each possible
outcome means, and the stability outcome is written up as a finding rather than a failure.

---

## 2. Corpus

Pyro-SDIS, `huggingface.co/datasets/pyronear/pyro-sdis`, Apache-2.0.

Measured directly from the distributed parquet shards, not from the dataset card:

| quantity | value |
|---|---|
| images | 33,636 (official train 29,537 + val 4,099) |
| images with at least one smoke box | 28,137 (83.65%) |
| images with no box (negatives) | 5,499 |
| boxes | 32,109 |
| cameras | 40 |
| partners (operating organisations) | 3 — `sdis-07` 17,766, `force-06` 13,768, `sdis-77` 2,102 |
| date range | 2024-01-01 to 2024-09-22, 8 distinct months, one calendar year |
| cameras under more than one partner | 0 |

Two properties of the shipped split are themselves reportable:

- The official train/val split is **not camera-disjoint and not partner-disjoint**: 23 of its 24
  validation cameras also appear in training.
- It ships no test set.

These are direct measurements and are reported as such. Whether the shipped split therefore behaves
like a random image-level split with respect to capture provenance is an interpretation that goes
beyond what has been measured, and it is not asserted here. The controlled experiment is what
establishes the consequence.

---

## 3. The granularity ladder

Nested, coarsening at each step, verified in code rather than asserted:

```
image (33,636)  <  event (892)  <  camera (40)  <  partner (3)
```

An **event** is a maximal run of images from one camera with no gap exceeding **30 minutes**.
Pyro-SDIS is a wildfire-watch network, so a detection yields a burst of frames from a single camera
over a short window; that burst is the natural unit between the frame and the camera. At a 30-minute
gap there are 892 events, median 21 images, **no singletons**. The threshold is fixed here and is
not tuned later; sensitivity to it is pre-specified in section 8.

Nesting was checked explicitly: every event lies within exactly one camera, and every camera within
exactly one partner. Both pass. Had either failed, the ladder framing would be false and the
experiment would not run.

### Protocols

All protocols re-partition the same pooled 33,636 images at the same 70/10/20 target, so the
allocation rule is the only thing that varies. Comparing against the shipped 88/12 split would
confound the rule with the training-set size.

| id | protocol | grouping unit | replicates | rationale |
|---|---|---|---|---|
| P1 | random image-level | none | 5 seeds | the prevailing practice, and the split-noise floor |
| P2 | event-disjoint | event (892) | 5 seeds | no burst spans the boundary |
| P3 | camera-disjoint | camera (40) | 5 seeds | transfer to an unseen camera |
| P4 | partner leave-one-out | partner (3) | 3 folds | transfer to an unseen operating organisation |
| P5 | temporal | chronological | 1 (deterministic) | short-horizon drift **within one fire season** |

P5 is reported alongside the ladder but is **not a rung**: it cuts across the hierarchy rather than
coarsening it. With only eight months inside one year it cannot speak to across-season
generalisation, and it will be described as short-horizon drift and nothing more.

P4 is **secondary and exploratory, not a primary estimand.** Three groups cannot produce a 70/10/20
split at all — attempting it empties an arm — so P4 is leave-one-partner-out with the remaining two
partners divided train/validation at the event level. Its folds are not comparable to each other:
held-out test sizes run from 2,102 (6.2%) to 17,766 (52.8%). No site-level conclusion will rest on
P4 alone.

### Measured properties of each protocol

From `corpus/pyrosdis_partitions.json`. Leakage counts are groups appearing in both train and test.

| protocol | train n | test n | event leak | camera leak | class-prevalence spread |
|---|---|---|---|---|---|
| P1 random | 23,545 | 6,728 | **833–844 of 892** | 37–40 | 0.53–1.18 pp |
| P2 event | 23,502–23,549 | 6,718–6,836 | 0 | 27–32 | 1.46–5.80 pp |
| P3 camera | 21,995–26,414 | 5,203–7,552 | 0 | 0 | 4.29–13.22 pp |
| P4 partner | 13,836–27,562 | 2,102–17,766 | 0 | 0 | 5.60–14.75 pp |
| P5 temporal | 23,545 | 6,728 | 0 | 18 | 9.08 pp |

Two things to read off this table before any model is trained.

**Under P1, between 833 and 844 of the 892 events have images in both the training and the test
arm**, across the five replicates: 93.4% to 94.6%. Stated as a measurement, this is the count of
event groups straddling the train/test boundary under random image-level assignment, at a 30-minute
event definition, on this corpus. What that crossing does to measured performance is the question
the experiment answers; it is not assumed here.

**Class prevalence separates monotonically as the rung coarsens** — roughly 1 pp at the image
level, up to 13 pp at the camera level and 15 pp at the partner level. This is not a nuisance to be
removed. Group-disjoint splitting *necessarily* changes composition, and pretending otherwise would
misdescribe the intervention. It is measured, reported per replicate, and handled under section 8.

---

## 4. Task and metric

Single-class smoke **object detection**, the dataset's native task. One task only; no metric is
pooled across corpora, because there is no second corpus.

- Primary metric: **mAP@0.50** on the held-out test arm.
- Secondary, reported always: mAP@0.50:0.95, precision, recall at the operating point that
  maximises F1 on the validation arm.

The operating point is chosen on validation, never on test.

---

## 5. Models

Four, fixed before any result is seen, chosen for architectural diversity rather than a leaderboard,
and constrained by an 8 GB RTX 2070:

| model | family | stage | anchors |
|---|---|---|---|
| YOLOv8n | YOLO | one-stage | anchor-free |
| YOLOv8s | YOLO | one-stage | anchor-free |
| RetinaNet ResNet50-FPN | torchvision | one-stage | anchor-based |
| Faster R-CNN MobileNetV3-Large-FPN | torchvision | two-stage | anchor-based |

YOLOv8n and YOLOv8s share a family deliberately: a capacity contrast within one architecture is the
comparison most likely to be close enough for ranking to move, and a ladder that only ever reorders
distant models would say little.

**No model may be added after results are seen**, and in particular none may be added because the
ordering looks too stable. If the four prove uniformly separated, that is the finding.

---

## 6. Training, held fixed across every run

| setting | value |
|---|---|
| image size | 416 × 416 |
| epochs | 25 |
| batch size | 16 (reduced per model only if it will not fit in 8 GB, and recorded) |
| optimiser | SGD, momentum 0.937, weight decay 5 × 10⁻⁴ |
| learning rate | 0.01 with cosine decay |
| warmup | 3 epochs |
| augmentation | horizontal flip only |
| pretrained weights | COCO, identical for every arm |
| early stopping | none — fixed budget, so compute cannot vary with protocol |

Augmentation is deliberately minimal. Mosaic and copy-paste synthesise composites across images,
which would blur the very partition boundaries under test.

**Matched training-set size.** Every run subsamples its training arm to a common N, drawn with that
replicate's seed, so a score difference can never be attributed to one protocol simply having more
data. Two values are pre-specified:

- **N = 21,995** for P1, P2, P3 and P5, the smallest training arm among those protocols.
- P4 is analysed separately at **N = 13,836**, its own smallest fold, and is never pooled with the
  others in a size-matched comparison.

---

## 7. Estimands

Fixed before training. E1 is score sensitivity; E2–E4 are ranking sensitivity.

**E1 — absolute performance shift.** For each model *m* and protocol *P*, Δ(m, P) = mAP@0.50 under
*P* minus mAP@0.50 under P1, the random baseline. Reported per model with a confidence interval
across replicates, and as a distribution over replicates rather than a single number.

**E2 — ranking concordance.** For each ordered pair of protocols, Kendall's τ between the four
models' rank vectors, plus the identity of the top model and the full order under each.

**E3 — pairwise reversal rate.** Over all 6 model pairs, a reversal is A > B under protocol X and
A < B under protocol Y. Reported as reversed / comparable pairs. **Ties are not reversals.** A pair
is counted comparable only if the two models' replicate-mean mAP differs by more than the
split-noise floor defined below; pairs within the floor are reported as indeterminate and counted in
neither numerator nor denominator, with the indeterminate count always stated.

**E4 — winner instability.** Whether the identity of the best model changes across protocols, and
in what fraction of replicates each model holds rank 1.

### The split-noise floor

P1 is replicated 5 times purely to establish how much rank movement arises from the split lottery
alone. The floor is the maximum absolute difference in replicate-mean mAP between any two P1
replicates for the same model. **Any rank movement at a coarser rung smaller than this floor is not
a finding and will not be reported as one.** Without this, a two-place move is indistinguishable
from fold randomness, and a reviewer will say so.

---

## 8. Statistical analysis

The design is **paired**: the same model, seed and training budget are observed under every
protocol. Independent-sample Welch tests are therefore not appropriate and are not used.

- E1: linear mixed model with mAP as outcome, protocol as a fixed effect, and random intercepts for
  model and replicate. Report estimated marginal means with 95% confidence intervals and the
  protocol effect size. P values are reported but do not carry the argument.
- E2: Kendall's τ per protocol pair with a bootstrap interval over replicates.
- E3/E4: exact binomial intervals on the reversal and winner-change proportions.
- Every effect is reported with an interval. No claim rests on a threshold crossing.
- **No equivalence claim will be drawn from a non-significant test.** If ranking proves stable, that
  is stated as an interval bounding the movement, following the correction already applied to the
  placebo analysis in the main manuscript.

### Pre-specified sensitivity analyses

1. Event-gap threshold at 15 and 60 minutes as well as 30, to show the event rung is not an artefact
   of one cut-off.
2. Unmatched training size, to show what the size control changes.
3. mAP@0.50:0.95 substituted for mAP@0.50 as the ranking metric.
4. P4 excluded entirely, since its folds are not comparable.
5. Each partner removed in turn from the pooled analysis.

### Confound recording

Changing granularity necessarily changes training-set size, class prevalence, camera composition and
image redundancy. For every partition, the following are recorded **before** any interpretation:
train/val/test counts, positive rate per arm, number of cameras and events per arm, box counts, date
range per arm, and the leakage counts already tabulated. Where an effect could plausibly be explained
by prevalence rather than granularity, that is stated rather than adjusted away. No balancing
procedure will be added after results because one protocol looks harder.

---

## 9. What each outcome would mean

Declared before training so that none can be reinterpreted afterwards.

**Supports the contribution.** Absolute performance falls monotonically as the rung coarsens, and
rank movement at coarser rungs exceeds the split-noise floor, with at least one winner change.
Reading: partition choice alters both reported performance and which model appears superior.

**Partially supports, and is still a finding.** Scores move materially with granularity while rank
order largely survives. Reading: partition provenance strongly affects reported performance while
comparative ranking is more robust than absolute scores. This is the outcome the prior literature
most leads us to expect, and it is written up as a result, not a disappointment.

**Weakens or falsifies.** Neither scores nor ranking move beyond the split-noise floor. Reading: on
this corpus, granularity does not materially affect either estimand, and the experimental hypothesis
is not supported. This is reported with the same prominence as any other outcome, and the audit half
of the paper stands on its own regardless.

**Would invalidate the design rather than answer it.** If prevalence differences track the score
differences closely enough that granularity cannot be separated from composition, the honest report
is that the two are confounded in this corpus by construction, not a claim about granularity.

The honest prior, from the novelty audit, is **partial stability rather than reversal**: spatial
cross-validation preserved model ordering in arXiv:2509.12051, the protocol effect proved
architecture-independent in arXiv:2605.06359, and Kendiukhov's reversal rates sit far below the
permutation null. The design is powered and pre-registered for a stability profile, not for a flip.

---

## 10. Novelty position

The ladder design is **borrowed, not new**, and the manuscript will say so in the paragraph that
introduces it. Multi-rung protocol gradients already exist in arXiv:2605.06359, arXiv:2608.01820 and
`10.3390/brainsci16080873`; per-rung rank correlations in arXiv:2608.30175; rank displacement under
a grouping change with ten models in arXiv:2609.01786. The audit-plus-experiment pairing is occupied
five times over, including Kapoor and Narayanan in our own target journal.

What remains unoccupied, and the only claim that will be made:

> On wildfire smoke-detection imagery, with corpus, preprocessing and model family held fixed, no
> published study advances the partition unit through four nested levels of capture provenance that
> the corpus itself distributes — image, event, camera, partner site — reporting rank-stability
> statistics at every level rather than for a single protocol contrast, and reads the resulting
> stability profile against a coded audit of how that same detection literature reports its own
> partition mechanism.

The word "first" is not used. The closest fire-domain work, `10.3390/rs17223756`, is cited and
distinguished: it varies two spatially blocked protocols for burn-severity regression, reports a
change in the best model without quantifying ranking stability, and includes no random-split
reference. arXiv:2608.11985 is distinguished by name in the granularity figure caption, since its
ladder is over the evaluation pairing unit rather than the split unit.

---

## 11. Compute budget

RTX 2070, 8 GB. Runs = 4 models × (5 + 5 + 5 + 3 + 1 partitions) = **76 training runs**.

At 416 px, N ≈ 22,000, 25 epochs, the YOLO runs are estimated at 35–50 minutes and the torchvision
detectors at 60–90 minutes, giving roughly **60–90 GPU-hours**, or three to four days of continuous
running. This is an estimate, not a measurement; a single timed pilot run per model is the first
action after this protocol is approved, and if the measured cost exceeds the estimate materially the
reduction is pre-specified here as: drop P1/P2/P3 replicates from 5 to 3, which yields 4 × 13 = 52
runs. Replicates are cut before models, protocols or epochs, and never after seeing results.
