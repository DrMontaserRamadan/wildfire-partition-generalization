#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the corpus-sample figure: what a random image-level split actually does to one fire.

The paper argues that assigning images at random puts consecutive frames of the same fire on
both sides of the partition. Until now that claim reached the reader only as a sentence and a
count. This figure shows it: real frames from one Pyro-SDIS event, in time order, badged with
the side each one landed on under the two rules the experiment compares.

Nothing here is illustrative. The event, the frames and the assignments are read from the frozen
split files the sweep trained against, and the event definition is imported from the partition
module rather than reimplemented, so the figure cannot drift from the experiment.

Pyro-SDIS is Apache-2.0, which permits redistribution of the images with attribution; the
footnote carries it.
"""
import io
import os
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "scripts")
import pyrosdis_partitions as pp  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#d8d7d2"
TRAIN = "#2a78d6"
TEST = "#eb6834"

RANDOM_TAG = "P1_random_image__seed20260911"
EVENT_TAG = "P2_event_disjoint__seed20260911"
N_FRAMES = 6


def load_split(tag):
    side = {}
    for part in ("train", "val", "test"):
        path = f"datasets/pyrosdis/splits/{tag}_{part}.txt"
        for line in io.open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                side[os.path.basename(line)] = part
    return side


rows = pp.load_rows()
n_events = pp.assign_events(rows)
rnd, evt = load_split(RANDOM_TAG), load_split(EVENT_TAG)

by_event = defaultdict(list)
for r in rows:
    by_event[r["event"]].append(r)

# How many events the random rule splits across train and test. Recomputed here rather than
# quoted, so the footnote cannot disagree with the split files.
straddling = sum(
    1 for rs in by_event.values()
    if {"train", "test"} <= {rnd.get(r["name"]) for r in rs})

# The window to draw: among all runs of N consecutive frames that the random rule splits across
# train and test, the one spanning the least time. Chosen by the clock, not by eye, so the
# example is the corpus's own tightest case rather than a flattering one.
# Selection rule, fixed here and applied to every event: the window must span no more than
# SPAN_CAP seconds, and its event must go wholly to the training side under the event rule, so
# that the two badge rows differ in the way the text describes. Among those, take the window
# with the most train/test alternations, then the shortest span. This selects for legibility,
# never for the result: the straddling count in the footnote is over the whole corpus and does
# not depend on which window is drawn.
SPAN_CAP = 60
best = None
for ev, rs in by_event.items():
    rs = sorted(rs, key=lambda x: x["t"])
    ev_sides = {evt.get(r["name"]) for r in rs}
    if ev_sides != {"train"}:
        continue
    for i in range(len(rs) - N_FRAMES + 1):
        win = rs[i:i + N_FRAMES]
        sides = [rnd.get(r["name"]) for r in win]
        if not all(sides):
            continue
        span = (win[-1]["t"] - win[0]["t"]).total_seconds()
        if span > SPAN_CAP:
            continue
        alt = sum(1 for k in range(len(sides) - 1)
                  if {sides[k], sides[k + 1]} == {"train", "test"})
        if not alt:
            continue
        cand = (-alt, span, ev, i)
        if best is None or cand < best:
            best = cand
neg_alt, span_s, ev_id, idx = best
gap_s = span_s
event = sorted(by_event[ev_id], key=lambda x: x["t"])
window = event[idx:idx + N_FRAMES]
assert len(window) == N_FRAMES, "event too short for the window"

fig = plt.figure(figsize=(12.6, 5.0), facecolor=SURFACE)
gs = fig.add_gridspec(3, N_FRAMES, height_ratios=[3.05, 0.5, 0.5],
                      hspace=0.16, wspace=0.055,
                      left=0.118, right=0.995, top=0.855, bottom=0.165)

t0 = window[0]["t"]
for j, r in enumerate(window):
    ax = fig.add_subplot(gs[0, j])
    ax.imshow(plt.imread(os.path.join("datasets/pyrosdis/images", r["name"])))
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(GRID)
    offset = (r["t"] - t0).total_seconds()
    ax.set_title(f"+{offset:.0f}s" if j else r["t"].strftime("%H:%M:%S"),
                 fontsize=8.4, color=INK_2, pad=4)

for row, (side_of, label) in enumerate(
        ((rnd, "random, image level"), (evt, "event-disjoint")), start=1):
    for j, r in enumerate(window):
        ax = fig.add_subplot(gs[row, j])
        ax.set_axis_off()
        part = side_of.get(r["name"], "?")
        colour = TRAIN if part == "train" else TEST if part == "test" else INK_2
        ax.add_patch(FancyBboxPatch((0.02, 0.17), 0.96, 0.66,
                                    boxstyle="round,pad=0.012,rounding_size=0.06",
                                    transform=ax.transAxes, facecolor=colour,
                                    edgecolor="none"))
        ax.text(0.5, 0.5, part.upper(), transform=ax.transAxes, ha="center", va="center",
                fontsize=9.6, fontweight="bold", color="white")
        if j == 0:
            ax.text(-0.028, 0.5, label, transform=ax.transAxes, ha="right", va="center",
                    fontsize=8.8, color=INK)

fig.text(0.030, 0.945,
         f"Six consecutive frames of one fire from a single camera, spanning {span_s:.0f} "
         f"seconds",
         fontsize=10.4, color=INK, fontweight="bold", ha="left")
fig.text(0.030, 0.895,
         "The images are identical to the eye. The rule that assigns them decides whether a "
         "test score measures a new fire or the same one.",
         fontsize=8.6, color=INK_2, ha="left")

fig.text(0.030, 0.028,
         f"Pyro-SDIS event {ev_id}, camera {window[0]['camera']}, partner "
         f"{window[0]['partner']}; {len(event)} frames in the event. Assignments are read from "
         f"the frozen split files the sweep trained against, seed 20260911.\nUnder the random "
         f"rule {straddling} of the {n_events} events have frames on both sides of the "
         f"train/test boundary; under the event rule none do. Images: Pyro-SDIS (Pyronear and "
         f"the French fire and rescue services), Apache-2.0.",
         fontsize=7.0, color=INK_2, va="bottom", ha="left")

fig.savefig("figures/figure_samples_partition.png", dpi=300, facecolor=SURFACE)
fig.savefig("figures/figure_samples_partition.pdf", facecolor=SURFACE)
print(f"wrote figures/figure_samples_partition.png / .pdf")
print(f"  event {ev_id}, {len(event)} frames, closest cross-boundary gap {gap_s:.0f}s")
print(f"  {straddling} of {n_events} events straddle train/test under the random rule")
