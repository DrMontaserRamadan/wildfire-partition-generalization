#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the duplicate-pairs figure: the overlap result as images rather than as bars.

Figure 6 reports that 218 of FireNET's 502 images have a near-duplicate in DeepQuestAI, and that
none of the 275 cross-corpus pairs is byte-identical. Both are bar charts. A reader cannot see
from a bar what "near-duplicate, not byte-identical" means, and that distinction carries the
paper's recommendation that deduplication by file hash is insufficient.

This draws real confirmed pairs straight from the frozen taxonomy, with the measured perceptual
distance and cross-correlation under each, so the claim and the evidence sit together.

Pairs are chosen by a fixed rule, never by eye: the pairs that cross the two separately published
corpora, taken in the taxonomy's own order, one per distinct source image.
"""
import io
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#d8d7d2"
ORANGE = "#eb6834"

N_PAIRS = 5
TAX = json.load(io.open("corpus/contamination_taxonomy.json", encoding="utf-8"))
ROOTS = json.load(io.open("corpus/ds_roots.json", encoding="utf-8"))

SHORT = {"FireNET": "FireNET", "DeepQuestAI_FireSmoke": "DeepQuestAI Fire-Smoke",
         "DeepQuestAI_inference": "DeepQuestAI inference", "DFire_test": "D-Fire"}


def path_of(ds, rel):
    return os.path.join(ROOTS[ds], rel)


# Restricted to the one corpus pair the paper's claim is about: FireNET against DeepQuestAI
# Fire-Smoke, two corpora published by different parties that the field treats as independent.
# The taxonomy's cross-corpus set also contains DeepQuestAI's own two releases matched against
# each other, which are the same publisher and would not support the sentence this figure
# illustrates. One pair per distinct FireNET image, so the strip shows five separate
# duplications rather than one image matched five ways.
TOP, BOTTOM = "FireNET", "DeepQuestAI_FireSmoke"
seen, pairs = set(), []
for x in TAX:
    if {x["ds_a"], x["ds_b"]} != {TOP, BOTTOM}:
        continue
    # Normalise orientation so the top row is always FireNET.
    if x["ds_a"] == TOP:
        top_rel, bot_rel = x["a"], x["b"]
    else:
        top_rel, bot_rel = x["b"], x["a"]
    if top_rel in seen:
        continue
    if not (os.path.exists(path_of(TOP, top_rel))
            and os.path.exists(path_of(BOTTOM, bot_rel))):
        continue
    seen.add(top_rel)
    pairs.append({**x, "top_rel": top_rel, "bot_rel": bot_rel})
    if len(pairs) == N_PAIRS:
        break
assert len(pairs) == N_PAIRS, f"only {len(pairs)} drawable {TOP}/{BOTTOM} pairs found"

n_cross = sum(1 for x in TAX if {x["ds_a"], x["ds_b"]} == {TOP, BOTTOM})
n_bytes = sum(1 for x in TAX if {x["ds_a"], x["ds_b"]} == {TOP, BOTTOM}
              and x["identity"] == "exact_bytes")

fig = plt.figure(figsize=(12.0, 5.3), facecolor=SURFACE)
gs = fig.add_gridspec(3, N_PAIRS, height_ratios=[1.0, 1.0, 0.30],
                      hspace=0.10, wspace=0.06,
                      left=0.165, right=0.995, top=0.845, bottom=0.165)

for j, x in enumerate(pairs):
    for row, (ds, rel) in enumerate(((TOP, x["top_rel"]), (BOTTOM, x["bot_rel"]))):
        ax = fig.add_subplot(gs[row, j])
        ax.imshow(plt.imread(path_of(ds, rel)))
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color(GRID)
        if j == 0:
            ax.text(-0.030, 0.5, SHORT.get(ds, ds), transform=ax.transAxes,
                    ha="right", va="center", fontsize=8.6, color=INK)
    ax = fig.add_subplot(gs[2, j])
    ax.set_axis_off()
    ax.text(0.5, 0.74, f"Hamming {x['dham']}   NCC {x['ncc']:.3f}", transform=ax.transAxes,
            ha="center", va="center", fontsize=8.2, color=INK)
    ax.text(0.5, 0.26, "not byte-identical", transform=ax.transAxes,
            ha="center", va="center", fontsize=7.8, color=ORANGE, fontweight="bold")

fig.text(0.030, 0.940,
         "Five images that FireNET and DeepQuestAI Fire-Smoke both contain",
         fontsize=10.4, color=INK, fontweight="bold", ha="left")
fig.text(0.030, 0.890,
         "Each column is the same photograph in two separately published corpora. Neither "
         "repository references the other, and no file-hash check would report any of them.",
         fontsize=8.6, color=INK_2, ha="left")

fig.text(0.030, 0.030,
         f"Drawn from the {n_cross} confirmed pairs spanning these two corpora, in the taxonomy's own "
         f"order, one per distinct source image. Hamming is the distance between 64-bit "
         f"perceptual hashes;\nNCC is normalized cross-correlation. {n_bytes} of the {n_cross} "
         f"are byte-identical, which is why deduplication by file hash returns nothing across "
         f"them and reports a clean corpus.",
         fontsize=7.0, color=INK_2, va="bottom", ha="left")

fig.savefig("figures/figure_samples_duplicates.png", dpi=300, facecolor=SURFACE)
fig.savefig("figures/figure_samples_duplicates.pdf", facecolor=SURFACE)
print("wrote figures/figure_samples_duplicates.png / .pdf")
for x in pairs:
    print(f"  {SHORT[x['ds_a']]}:{x['a']}  <->  {SHORT[x['ds_b']]}:{x['b']}"
          f"   dham={x['dham']} ncc={x['ncc']:.4f}")
print(f"  {n_bytes} of {n_cross} cross-corpus pairs are byte-identical")
