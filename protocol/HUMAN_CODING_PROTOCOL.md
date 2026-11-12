# Human double-coding protocol for the central construct

This addresses construct validity, which is a separate question from novelty. Every prevalence
figure in the manuscript rests on codes produced by language-model instances. Reliability between
two such instances establishes that the procedure is repeatable; it does not establish that the
construct is what a human expert would code. Only humans can answer that, and until they do, the
central estimate carries an unquantified validity assumption.

## What is being coded

One variable only. Coders are not asked to reproduce the full instrument.

> **Does the paper state a rule by which specific observations were assigned to the training and
> evaluation partitions, such that a reader could reconstruct the assignment?**

Four categories, identical to those used in the full-text validation:

1. **Mechanism reported** — an allocation rule is stated (random assignment, k-fold, a named
   official split, or assignment by some group such as fire, video, camera, site or date).
2. **Ratio or counts only** — proportions or subset sizes are given, with no rule for which
   observations went where.
3. **No partition statement** — the paper does not describe a train/evaluation partition at all.
4. **Unresolved** — the text is internally inconsistent, or defers the partition to another work.

Categories 2 and 3 together form the numerator of the central estimand.

## Sample

**All 64 learned-model papers.** The user's minimum was 30 randomly selected; the full set is
preferred and is what is planned, because 64 is small enough to be tractable and a census removes
sampling variability from an already contested estimate. If coder availability forces a reduction,
the fallback is 30 drawn by seeded random selection from the 64, with the seed recorded before
selection, and the reduction documented as a deviation.

## Blinding

Blinding is about what a coder can see, not what they are told to ignore.

Each coder receives a packet containing, per paper: the paper identifier, and the complete article
text. Nothing else. Specifically absent from the packet:

- the model-produced codes, for either role;
- the validated classification;
- the headline prevalence figure of 64.1%, or any other prevalence figure;
- the manuscript, the claim ledger, and any file naming a result;
- any indication of how other coders classified the same paper;
- the categories' numerator membership — the packet does not say that 2 and 3 are the ones that
  count.

Coders work independently and do not communicate until both submissions are frozen. The instruction
sheet states the four categories and the decision rule, and nothing about what any result is
expected to be.

## Sequence, and what gets frozen when

1. Instruction sheet and packets built, hashed, and recorded in `EVIDENCE_MANIFEST.json`.
2. Human A codes all papers. Submission frozen and hashed **before** A sees anything else.
3. Human B codes all papers independently. Submission frozen and hashed.
4. Only then are A and B compared. Disagreements are listed.
5. Consensus round: A and B resolve disagreements together, producing a consensus code. The
   pre-consensus codes remain frozen and are reported regardless of what consensus concludes.
6. Only then is any comparison made against the model codes or the validated classification.

Step 2 and 3 freezing is the load-bearing part. A code that can be revised after seeing the other
coder's answer is not an independent observation.

## What will be reported

All of the following, whatever they show:

| comparison | statistic |
|---|---|
| human A vs human B, pre-consensus | raw agreement, Cohen's κ, and the full 4×4 cross-tabulation |
| human A vs the validated classification | raw agreement, κ |
| human B vs the validated classification | raw agreement, κ |
| human consensus vs the validated classification | raw agreement, κ, and the disagreement list |
| human consensus prevalence | numerator/denominator and Wilson interval, beside the 41/64 = 64.1% |

The κ paradox applies here as it does elsewhere in this project: with skewed marginals a high raw
agreement can accompany a low κ. Both are reported together, and where the marginals are skewed the
reading is stated explicitly rather than left to the reader.

## Rules fixed in advance

**If human consensus disagrees materially with the validated classification, the human figure
governs and the manuscript's headline changes.** The threshold for material is the same 10
percentage points already fixed for the sensitivity analyses. The model-derived figure is not
protected, and the earlier instruction on this project applies unchanged: if the number moves, use
the validated result rather than defending the existing headline.

**Human–human disagreement carries no pre-assigned meaning.** An earlier version of this protocol
stated that a low human–human κ would be direct evidence for the paper's central claim. That was
wrong, and it is withdrawn: it assigned a favourable reading to a result before the result existed,
which is the same move this project has refused everywhere else.

> Human–human disagreement will not be interpreted a priori as supporting either the
> reporting-gap hypothesis or instrument failure. Its pattern will be examined against the frozen
> rubric, and raw human classifications will be preserved and reported before consensus.

Low agreement admits at least three readings — the source papers are genuinely ambiguous, the rubric
is ambiguous, or both — and they are distinguished by where the disagreements fall, not by
assumption. If disagreement concentrates on one category boundary, that points at the rubric; if it
is spread across papers that differ in how they describe their partitions, that points at the
source texts. The disagreement structure is reported either way.

**Coders are named and their role disclosed.** Where a language model produced codes, the model is
named in the manuscript. The same standard applies to human coders: their role, expertise and
independence from the analysis are stated.

## Who the coders should be

Two people with enough machine-learning background to read a methods section, and no involvement in
this project's analysis. They must not be the manuscript's authors: an author who knows the headline
cannot be blind to it. This is the one requirement that cannot be satisfied internally, and it is
the item most likely to delay the submission — which is why it is being arranged in parallel with
the experiment rather than after it.
