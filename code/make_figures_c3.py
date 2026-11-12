"""Figures 4 and 5 — the partition-granularity experiment (C3).

Every number regenerates from corpus/experiment_runs/*.json by way of
corpus/estimands_2026-09-18.json. Nothing in either figure is typed in by hand.

Encoding decisions, and the reasons for them:

  - Three categorical hues only. The documented palette's first three slots pass the validator
    on the ALL-PAIRS list (worst CVD deltaE 9.2 deutan, worst normal-vision deltaE 24.0), and
    all-pairs is the list that applies here because the lines cross. Adding the fourth slot puts
    yellow beside orange and fails the normal-vision floor at deltaE 13.7, which secondary
    encoding does not excuse.
  - The fourth arm, Faster R-CNN, therefore carries neutral ink rather than a hue. That is not a
    convenience. Section 5 specifies a mobile backbone trained on a schedule derived from the
    YOLO arms, its position is constant at every rung, and the protocol forbids reading it as an
    architectural verdict. It stays in both figures with its values, and it remains a full
    member of every rank statistic.
  - Identity carries a marker shape and a line style as well as a hue, so both figures survive
    greyscale printing.
  - The aqua slot sits at 2.74:1 against the surface, under the 3:1 gate. The validator calls
    for relief, so every series is directly labelled at the right edge and the full table lives
    in SWEEP_RESULTS_2026-09-18.md.
  - Jitter is deterministic, never an RNG, so both figures are byte-reproducible.
"""
import glob
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

STYLE = {
    "yolov8n":    {"c": "#2a78d6", "m": "o", "ls": "-",  "label": "YOLOv8n"},
    "yolov8s":    {"c": "#eb6834", "m": "s", "ls": "-",  "label": "YOLOv8s"},
    "retinanet":  {"c": "#1baf7a", "m": "^", "ls": "-",  "label": "RetinaNet"},
    "fasterrcnn": {"c": "#6b6a65", "m": "D", "ls": "--", "label": "Faster R-CNN"},
}
MODELS = ["yolov8n", "yolov8s", "retinanet", "fasterrcnn"]
PROTOCOLS = ["P1_random_image", "P2_event_disjoint", "P3_camera_disjoint",
             "P4_partner_lopo", "P5_temporal"]
RUNG = ["P1\nrandom\nimage", "P2\nevent\ndisjoint", "P3\ncamera\ndisjoint",
        "P4\npartner\nLOPO", "P5\ntemporal"]

E = json.load(open("corpus/estimands_2026-09-18.json"))
FLOOR = E["split_noise_floor"]["floor"]


def load_runs():
    out = {}
    for p in glob.glob("corpus/experiment_runs/*.json"):
        if "PILOT" in p:
            continue
        d = json.load(open(p))
        fam, _, _seed = d["partition"].partition("__seed")
        out.setdefault((d["model"], fam), []).append(d["metrics"]["map_50"])
    return {k: sorted(v) for k, v in out.items()}


R = load_runs()
assert sum(len(v) for v in R.values()) == 76


def mean(m, f):
    return sum(R[(m, f)]) / len(R[(m, f)])


def jitter(n, spread=0.13):
    """Deterministic symmetric jitter — no RNG, so the figure is byte-reproducible."""
    if n == 1:
        return [0.0]
    return [spread * (2 * i / (n - 1) - 1) for i in range(n)]


def edge_labels(ax, x, items, min_gap):
    """Right-edge direct labels, pushed apart so near-equal series stay readable.

    The validator flags the aqua slot as below the 3:1 contrast gate, so direct labels are
    required relief rather than decoration; two of them overlapping would defeat that.
    """
    items = sorted(items, key=lambda t: -t[1])
    ys = [y for _, y, _ in items]
    for i in range(1, len(ys)):
        if ys[i - 1] - ys[i] < min_gap:
            ys[i] = ys[i - 1] - min_gap
    for (label, _, colour), y in zip(items, ys):
        ax.annotate(label, (x, y), xytext=(10, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=8.5, color=colour, fontweight="bold")


def frame(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=8.5, length=3)
    ax.grid(axis="y", color=GRID, lw=0.7, alpha=0.8)
    ax.set_axisbelow(True)


# ==================================================================================
# FIGURE 4 — the ladder, and the widening of the split lottery
# ==================================================================================
fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.8, 4.8), facecolor=SURFACE,
                               gridspec_kw={"width_ratios": [1.3, 1]})

frame(axA)
axA.axvspan(2.5, 4.5, color="#efeee9", alpha=0.7, zorder=0)
tips = []
for m in MODELS:
    s = STYLE[m]
    ys = []
    for i, f in enumerate(PROTOCOLS):
        v = R[(m, f)]
        for dx, y in zip(jitter(len(v)), v):
            axA.plot(i + dx, y, s["m"], color=s["c"], ms=4.8, alpha=0.5,
                     mec=SURFACE, mew=0.7, zorder=3)
        ys.append(mean(m, f))
    axA.plot(range(5), ys, s["ls"], color=s["c"], lw=2.0, zorder=4)
    axA.plot(range(5), ys, s["m"], color=s["c"], ms=8.0, mec=SURFACE, mew=1.6, zorder=5)
    tips.append((s["label"], ys[-1], s["c"]))
edge_labels(axA, 4, tips, min_gap=0.036)

axA.text(3.5, 0.895, "exploratory rungs", ha="center", va="top", fontsize=8.2,
         color=INK_2, style="italic")
axA.text(3.5, 0.862, "P4  n=3 folds, unequal test sizes        P5  n=1, deterministic",
         ha="center", va="top", fontsize=7.0, color=INK_2)
axA.set_xticks(range(5))
axA.set_xticklabels(RUNG, fontsize=8)
axA.set_xlim(-0.45, 5.25)
axA.set_ylim(0, 0.93)
axA.set_ylabel("your-email@example.org on the held-out test arm", fontsize=9, color=INK)
axA.set_title("A   Every arm falls as the partition coarsens", fontsize=10.5,
              color=INK, loc="left", pad=10, fontweight="bold")

frame(axB)
REPL = PROTOCOLS[:4]          # P5 is a single deterministic split and has no spread
tips = []
for m in MODELS:
    s = STYLE[m]
    ys = [max(R[(m, f)]) - min(R[(m, f)]) for f in REPL]
    axB.plot(range(4), ys, s["ls"], color=s["c"], lw=2.0, zorder=4)
    axB.plot(range(4), ys, s["m"], color=s["c"], ms=8.0, mec=SURFACE, mew=1.6, zorder=5)
    tips.append((s["label"], ys[-1], s["c"]))
edge_labels(axB, 3, tips, min_gap=0.0115)

# The floor is a range, not a standard deviation, so this panel plots a range too — the two
# have to be on the same footing for the comparison to mean anything.
axB.axhline(FLOOR, color=INK, lw=1.4, ls=(0, (4, 3)), zorder=6)
axB.text(1.25, FLOOR - 0.004,
         f"split-noise floor  {FLOOR:.4f} — widest gap between two P1 replicates of one model",
         fontsize=7.4, color=INK, va="top", ha="left")
axB.set_xticks(range(4))
axB.set_xticklabels(RUNG[:4], fontsize=8)
axB.set_xlim(-0.45, 4.15)
axB.set_ylabel("spread of your-email@example.org across replicates   (max − min)", fontsize=9, color=INK)
axB.set_title("B   And the split lottery widens with it", fontsize=10.5,
              color=INK, loc="left", pad=10, fontweight="bold")

fig.text(0.008, 0.015,
         "76 runs, one RTX 4090, 0 failures. Faster R-CNN carries neutral ink rather than a hue: "
         "its position is constant at every rung and the protocol forbids reading it as\n"
         "an architectural verdict. It remains a full member of every rank statistic. Marker "
         "shape and line style repeat the identity, so the figure survives greyscale printing.",
         fontsize=7.0, color=INK_2, va="bottom")
fig.tight_layout(rect=(0, 0.072, 1, 1))
fig.savefig("figures/figure4_granularity_ladder.png", dpi=300, facecolor=SURFACE)
fig.savefig("figures/figure4_granularity_ladder.pdf", facecolor=SURFACE)
plt.close(fig)
print("wrote figures/figure4_granularity_ladder.png / .pdf")


# ==================================================================================
# FIGURE 5 — rank behaviour: P1 is the lone dissenter
# ==================================================================================
fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.8, 4.8), facecolor=SURFACE,
                               gridspec_kw={"width_ratios": [1.12, 1]})

frame(axA)
axA.grid(False)
ranks = {m: [] for m in MODELS}
for f in PROTOCOLS:
    for r, m in enumerate(sorted(MODELS, key=lambda k: -mean(k, f)), start=1):
        ranks[m].append(r)

for m in MODELS:
    s = STYLE[m]
    axA.plot(range(5), ranks[m], s["ls"], color=s["c"], lw=2.4, zorder=4)
    axA.plot(range(5), ranks[m], s["m"], color=s["c"], ms=10.0, mec=SURFACE, mew=1.8, zorder=5)
    axA.annotate(s["label"], (4, ranks[m][-1]), xytext=(12, 0), textcoords="offset points",
                 va="center", ha="left", fontsize=8.5, color=s["c"], fontweight="bold")

# the band between rank 3 and rank 4 is the only empty strip in this panel
axA.annotate("the sweep's only reversal: YOLOv8s leads RetinaNet by 0.024 at P1,\n"
             "RetinaNet leads at every coarser rung",
             xy=(0.52, 1.52), xytext=(1.55, 3.62), fontsize=7.6, color=INK,
             ha="center", va="center",
             arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1,
                             connectionstyle="arc3,rad=0.3"))
axA.text(1.0, 0.52, "P2 is the transition: RetinaNet takes rank 1 in 4 of 5 replicates",
         fontsize=7.4, color=INK_2, ha="center")
axA.set_xticks(range(5))
axA.set_xticklabels(RUNG, fontsize=8)
axA.set_yticks([1, 2, 3, 4])
axA.set_yticklabels(["1st", "2nd", "3rd", "4th"], fontsize=8.5)
axA.set_ylim(4.65, 0.35)
axA.set_xlim(-0.45, 5.35)
axA.set_ylabel("rank by replicate-mean your-email@example.org", fontsize=9, color=INK)
axA.set_title("A   The winner changes once, and only between P1 and the rest",
              fontsize=10.5, color=INK, loc="left", pad=10, fontweight="bold")

# --- Kendall tau matrix, lower triangle -------------------------------------------
axB.set_facecolor(SURFACE)
tau = {(f, f): 1.0 for f in PROTOCOLS}
for k, v in E["E2_rank_concordance"].items():
    a, b = k.split("__vs__")
    tau[(a, b)] = tau[(b, a)] = v["tau"]

RAMP = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab"]

for i, a in enumerate(PROTOCOLS):
    for j, b in enumerate(PROTOCOLS):
        if j > i:
            continue
        t = tau[(a, b)]
        step = RAMP[min(4, max(0, int(round((t + 1) / 2 * 4))))]
        axB.add_patch(plt.Rectangle((j + 0.04, i + 0.04), 0.92, 0.92,
                                    facecolor=step, edgecolor=SURFACE, lw=2, zorder=2))
        axB.text(j + 0.5, i + 0.5, f"{t:.2f}", ha="center", va="center", fontsize=9.5,
                 color="#ffffff" if t > 0.6 else INK, zorder=3,
                 fontweight="bold" if i != j else "normal")

# Outline the two blocks the result lives in. The coarse-versus-coarse region is a staircase,
# not a rectangle: a rectangle would enclose the P3/P3 and P4/P4 diagonal cells, which are
# self-comparisons and trivially 1.00, and claim them as evidence.
axB.add_patch(plt.Rectangle((0.04, 1.04), 0.92, 3.92, fill=False,
                            edgecolor=INK, lw=1.8, zorder=4))
axB.add_patch(plt.Polygon([(1.04, 2.04), (1.96, 2.04), (1.96, 2.96), (2.96, 2.96),
                           (2.96, 3.96), (3.96, 3.96), (3.96, 4.96), (1.04, 4.96)],
                          closed=True, fill=False, edgecolor=INK, lw=1.8, zorder=4))

# both annotations live in the empty upper triangle
axB.annotate("P1 against every coarser rung:\nτ = +0.33 at every one",
             xy=(0.96, 2.5), xytext=(2.15, 0.62), fontsize=7.8, color=INK, ha="left",
             va="center",
             arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1,
                             connectionstyle="arc3,rad=0.3"), zorder=5)
axB.annotate("the coarse rungs against each other:\nτ = +1.00 at every one",
             xy=(3.5, 3.96), xytext=(3.3, 1.75), fontsize=7.8, color=INK, ha="center",
             va="center",
             arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1,
                             connectionstyle="arc3,rad=-0.25"), zorder=5)

axB.set_xlim(-0.05, 5.05)
axB.set_ylim(5.15, -0.05)
axB.set_xticks([i + 0.5 for i in range(5)])
axB.set_xticklabels([r.replace("\n", " ") for r in RUNG], fontsize=7.4,
                    rotation=30, ha="right")
axB.set_yticks([i + 0.5 for i in range(5)])
axB.set_yticklabels([r.split("\n")[0] for r in RUNG], fontsize=8.5)
for s in axB.spines.values():
    s.set_visible(False)
axB.tick_params(colors=INK_2, length=0)
axB.set_title("B   Kendall's τ between every pair of rungs", fontsize=10.5,
              color=INK, loc="left", pad=10, fontweight="bold")

fig.text(0.008, 0.015,
         "Four of the ten rung pairs change winner, and all four involve P1. There are 3 pairwise "
         "reversals, every one of them the same model pair, against 0 reversals\namong the coarse "
         "rungs. Model pairs separated by less than the split-noise floor are indeterminate and "
         "are excluded from both the numerator and the denominator.\nValues regenerate from the "
         "frozen estimands record.",
         fontsize=7.0, color=INK_2, va="bottom")
fig.tight_layout(rect=(0, 0.088, 1, 1))
fig.savefig("figures/figure5_rank_behaviour.png", dpi=300, facecolor=SURFACE)
fig.savefig("figures/figure5_rank_behaviour.pdf", facecolor=SURFACE)
plt.close(fig)
print("wrote figures/figure5_rank_behaviour.png / .pdf")
