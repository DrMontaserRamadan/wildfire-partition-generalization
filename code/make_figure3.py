"""Figure 3 — FLAME protocol separation, rebuilt as a distribution and a rank statistic.

The original design was a scatter over publication date with two fitted trend lines. That
design is dead, and the data killed it:

  - both slopes are NEGATIVE (-0.95 and -0.30 points/year, R2 0.125 and 0.064), so a rising
    cloud was never there to draw;
  - the two "clean populations" overlap — one official-protocol paper scores above one
    non-official paper — and the separation shrank monotonically under verification,
    8 points -> 4 points -> overlapping;
  - the drift is not sequential: the first non-official paper appeared nine days after an
    official-protocol one, so there is no before-and-after to put on a time axis.

What survives is not a trend. It is a difference in distribution and an almost complete rank
dominance, and those are what this figure now draws. Panel B is included specifically so the
single counter-example is visible rather than buried in a p-value.

Palette validated with the dataviz validator (light surface): blue/orange, worst adjacent
CVD deltaE 24.7 protan, 33.6 normal-vision, all six checks PASS. Protocol is additionally
encoded by marker shape, so the figure survives greyscale printing.
"""
import json
import io
import os
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

OFFICIAL_BLUE = "#2a78d6"
OTHER_ORANGE = "#eb6834"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#d8d7d2"
SURFACE = "#fcfcfb"

# non-official protocols, each with its own marker so hue is never the only encoding
MARKERS = {
    "RANDOM_RESPLIT": "s",
    "SUBSET_OF_UNCLEAR_PROVENANCE": "^",
    "INTERNALLY_INCONSISTENT": "D",
    "K_FOLD_POOLED": "v",
}
LABELS = {
    "RANDOM_RESPLIT": "random re-split",
    "SUBSET_OF_UNCLEAR_PROVENANCE": "subset, provenance unclear",
    "INTERNALLY_INCONSISTENT": "internally inconsistent",
    "K_FOLD_POOLED": "k-fold over a pooled set",
}


def load():
    rows = json.load(io.open("corpus/flame_timeline.json", encoding="utf-8"))
    have = [r for r in rows if r.get("headline_accuracy") is not None]
    off = [r for r in have if r["protocol"] == "OFFICIAL"]
    oth = [r for r in have if r["protocol"] != "OFFICIAL"]
    return off, oth


def jitter(n, spread=0.26):
    """Deterministic symmetric jitter — no RNG, so the figure is byte-reproducible."""
    if n == 1:
        return [0.0]
    return [spread * (2 * i / (n - 1) - 1) for i in range(n)]


def panel_a(ax, off, oth):
    hi = max(off, key=lambda r: r["headline_accuracy"])
    lo = min(oth, key=lambda r: r["headline_accuracy"])

    # the overlap band, drawn behind everything so the two markers sit inside it
    ax.axvspan(lo["headline_accuracy"] - 0.4, hi["headline_accuracy"] + 0.4,
               ymin=0.23, ymax=0.77, color=INK_2, alpha=0.08, lw=0, zorder=0)

    for row, group, colour in ((1, off, OFFICIAL_BLUE), (0, oth, OTHER_ORANGE)):
        vals = sorted(group, key=lambda r: r["headline_accuracy"])
        for dy, r in zip(jitter(len(vals)), vals):
            m = "o" if r["protocol"] == "OFFICIAL" else MARKERS.get(r["protocol"], "x")
            ax.plot(r["headline_accuracy"], row + dy, marker=m, ms=7, mfc=colour,
                    mec=SURFACE, mew=1.2, ls="none", zorder=3)
        v = [r["headline_accuracy"] for r in group]
        q1, med, q3 = st.quantiles(v, n=4)
        ax.plot([q1, q3], [row + 0.46, row + 0.46], lw=5, color=colour, alpha=0.35,
                solid_capstyle="butt", zorder=2)
        ax.plot([med, med], [row + 0.42, row + 0.50], lw=2.5, color=colour, zorder=4)
        label = f"median {med:.2f}   ·   IQR {q1:.1f}–{q3:.1f}"
        # right-align the upper band's label so it cannot run off the right edge
        if med > 95:
            ax.text(102.5, row + 0.58, label, ha="right", va="bottom",
                    fontsize=8.5, color=INK)
        else:
            ax.text(med, row + 0.58, label, ha="center", va="bottom",
                    fontsize=8.5, color=INK)

    # caption kept entirely left of the 76.23 rule so the two never cross
    ax.annotate(
        f"the bands overlap here —\n{hi['first_author']} {hi['headline_accuracy']:.2f} WITH the "
        f"official\nsplit beats {lo['first_author']} {lo['headline_accuracy']:.2f} without it",
        xy=(lo["headline_accuracy"] - 0.4, -0.30), xytext=(60.6, -0.55),
        fontsize=7.8, color=INK_2, ha="left", va="center",
        arrowprops=dict(arrowstyle="->", color=INK_2, lw=0.9, shrinkA=6, shrinkB=3,
                        connectionstyle="arc3,rad=-0.12"))

    ax.axvline(76.23, color=INK_2, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.annotate("76.23 — the dataset authors'\nown test-set result",
                xy=(76.23, 1.62), xytext=(64.5, 1.62), fontsize=7.8, color=INK_2,
                ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=INK_2, lw=0.9, shrinkA=2, shrinkB=2))

    ax.set_yticks([0, 1])
    ax.set_yticklabels([f"NOT the official split\n(n = {len(oth)})",
                        f"OFFICIAL camera-disjoint\ntest set  (n = {len(off)})"],
                       fontsize=8.5, color=INK)
    ax.set_xlabel("reported headline accuracy on FLAME (%)", fontsize=9, color=INK)
    ax.set_xlim(60, 103)
    ax.set_ylim(-0.95, 1.95)
    ax.set_title("A.  Two distributions, not a trend — association, not an estimated effect",
                 fontsize=10, color=INK, loc="left", pad=8)


def panel_b(ax, off, oth):
    o = sorted((r["headline_accuracy"] for r in off))
    n = sorted((r["headline_accuracy"] for r in oth))
    wins = losses = 0
    for i, a in enumerate(o):
        for j, b in enumerate(n):
            higher = b > a
            wins += higher
            losses += not higher
            ax.add_patch(plt.Rectangle(
                (j, i), 0.88, 0.88,
                facecolor=OTHER_ORANGE if higher else OFFICIAL_BLUE,
                alpha=0.85 if higher else 1.0, edgecolor=SURFACE, lw=0.8))
            if not higher:
                ax.annotate("the one\nexception", xy=(j + 0.44, i + 0.44),
                            xytext=(j - 4.2, i + 4.0), fontsize=7.8, color=INK,
                            ha="center",
                            arrowprops=dict(arrowstyle="->", color=INK, lw=0.9))
    ax.set_xlim(-0.4, len(n) + 0.2)
    ax.set_ylim(-0.4, len(o) + 0.2)
    ax.set_aspect("equal")
    ax.set_xlabel(f"each non-official paper  (n = {len(n)})", fontsize=8.5, color=INK_2)
    ax.set_ylabel(f"each official-protocol paper  (n = {len(o)})", fontsize=8.5, color=INK_2)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(f"B.  Every pairwise comparison: {wins} of {wins + losses} favour the\n"
                 f"     non-official paper ({100 * wins / (wins + losses):.1f}%) — a rank\n"
                 f"     statistic, not an effect size",
                 fontsize=10, color=INK, loc="left", pad=8)
    return wins, wins + losses


def panel_c(ax):
    """Within-paper controls where the DATA is held constant and only the protocol moves."""
    clean = [
        ("Shamsoshoara 2021\nthe dataset's own authors", 76.23, 94.31,
         "official test set", "their own validation split"),
        ("Zachariadis 2023\nsame team, same model", 73.16, 90.10,
         "official replication", "after merge and re-split"),
    ]
    for k, (label, a, b, la, lb) in enumerate(clean):
        y = len(clean) - 1 - k
        ax.annotate("", xy=(b, y), xytext=(a, y),
                    arrowprops=dict(arrowstyle="-|>", color=INK_2, lw=1.6, shrinkA=6,
                                    shrinkB=6))
        ax.plot(a, y, "o", ms=9, mfc=OFFICIAL_BLUE, mec=SURFACE, mew=1.3, zorder=3)
        ax.plot(b, y, "s", ms=9, mfc=OTHER_ORANGE, mec=SURFACE, mew=1.3, zorder=3)
        ax.text(a - 1.4, y, f"{a:.2f}", ha="right", va="center", fontsize=8.5, color=INK)
        ax.text(b + 1.4, y, f"{b:.2f}", ha="left", va="center", fontsize=8.5, color=INK)
        ax.text(a - 1.4, y - 0.26, la, ha="right", va="top", fontsize=7, color=INK_2)
        ax.text(b + 1.4, y - 0.26, lb, ha="left", va="top", fontsize=7, color=INK_2)
        ax.text(58.5, y, label, ha="left", va="center", fontsize=8, color=INK)
        ax.text((a + b) / 2, y + 0.16, f"+{b - a:.2f} points", ha="center", va="bottom",
                fontsize=7.5, color=INK_2)
    ax.set_xlim(57, 104)
    ax.set_ylim(-0.62, len(clean) - 0.30)
    ax.set_yticks([])
    ax.set_xlabel("accuracy (%)", fontsize=9, color=INK)
    ax.set_title("C.  Same paper, same data, protocol moved", fontsize=10, color=INK,
                 loc="left", pad=8)


def main():
    off, oth = load()
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": GRID,
                         "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})

    fig = plt.figure(figsize=(11.2, 10.2))
    gs = fig.add_gridspec(3, 2, height_ratios=[1.15, 1.55, 0.80],
                          width_ratios=[1.35, 1], hspace=0.75, wspace=0.18)
    ax_a = fig.add_subplot(gs[0, :])
    ax_b = fig.add_subplot(gs[1, 0])
    ax_l = fig.add_subplot(gs[1, 1])
    ax_c = fig.add_subplot(gs[2, :])

    panel_a(ax_a, off, oth)
    wins, total = panel_b(ax_b, off, oth)
    panel_c(ax_c)

    for ax in (ax_a, ax_c):
        ax.grid(axis="x", color=GRID, lw=0.7)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.tick_params(colors=INK_2, labelsize=8.5)

    # legend panel: identity is never carried by colour alone
    ax_l.axis("off")
    handles = [Line2D([], [], marker="o", ls="none", ms=8, mfc=OFFICIAL_BLUE,
                      mec=SURFACE, mew=1.2, label="official camera-disjoint test set")]
    for p, m in MARKERS.items():
        if any(r["protocol"] == p for r in oth):
            handles.append(Line2D([], [], marker=m, ls="none", ms=8, mfc=OTHER_ORANGE,
                                  mec=SURFACE, mew=1.2, label=LABELS[p]))
    ax_l.legend(handles=handles, loc="upper left", frameon=False, fontsize=8.5,
                labelcolor=INK, title="split protocol, as stated by the paper",
                title_fontsize=8.5, alignment="left")
    ax_l.text(0.0, 0.44,
              "What this figure does NOT show\n"
              "\n"
              "No trend line. Both fitted slopes are negative\n"
              "(−0.95 and −0.30 points/year, R² 0.125 and\n"
              "0.064) and the drift is not sequential.\n"
              "\n"
              "No causal claim. Authors choose their own\n"
              "protocol, so architecture, team, year and venue\n"
              "move with that choice and this design cannot\n"
              "separate them. A and B are ASSOCIATION; C is\n"
              "the only identified comparison, at n = 2.",
              transform=ax_l.transAxes, fontsize=7.6, color=INK_2, va="top")

    fig.suptitle("Papers that set aside FLAME's official split report far higher accuracy",
                 fontsize=12.5, color=INK, x=0.055, ha="left", y=0.985)
    fig.text(0.055, 0.012,
             "This is an observational comparison across published papers, not an experiment. "
             "It shows that reported accuracy and stated split protocol travel together; it "
             "does not establish that the protocol\ncauses the difference, and no publisher, "
             "venue or author effect is estimated or implied. Panel C excludes five further "
             "within-paper pairs because each reports its second number on a DIFFERENT dataset, "
             "confounding\nprotocol with dataset. Panel A plots every paper individually; no "
             "value is aggregated away.",
             fontsize=7.4, color=INK_2, ha="left", va="bottom")

    os.makedirs("figures", exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"figures/figure3_protocol_separation.{ext}", dpi=300,
                    bbox_inches="tight", facecolor=SURFACE)

    off_v = [r["headline_accuracy"] for r in off]
    oth_v = [r["headline_accuracy"] for r in oth]
    print("figures/figure3_protocol_separation.png / .pdf")
    print(f"  official     n={len(off_v):2d}  median {st.median(off_v):.2f}  "
          f"IQR {st.quantiles(off_v, n=4)[0]:.2f}-{st.quantiles(off_v, n=4)[2]:.2f}")
    print(f"  not official n={len(oth_v):2d}  median {st.median(oth_v):.2f}  "
          f"IQR {st.quantiles(oth_v, n=4)[0]:.2f}-{st.quantiles(oth_v, n=4)[2]:.2f}")
    print(f"  pairwise     {wins}/{total} = {100 * wins / total:.1f}% favour non-official")
    print(f"  overlap      max official {max(off_v):.2f} > min non-official {min(oth_v):.2f}")


if __name__ == "__main__":
    main()
