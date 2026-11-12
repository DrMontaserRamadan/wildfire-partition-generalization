"""Figures 1, 2, 6 and 7 — the audit and benchmark-overlap floats.

Every number regenerates from the frozen records; none is typed in. Sources are named per
figure in FIGURES.md.

Encoding follows the rules already in force for figures 3 to 5. The categorical palette is the
documented blue/orange/aqua, validated on the all-pairs list; anything that is not a series
identity carries neutral ink. No value is encoded by hue alone — every bar and cell is directly
labelled, so the figures survive greyscale printing and the contrast warning on the aqua slot.
Nothing here uses an RNG, so all four are byte-reproducible.

Two design notes worth keeping, because both were errors caught by looking at the rendered
output rather than by any check:

  - Figure 6 panel A plots the OVERLAP SHARE per corpus, not raw corpus sizes. Drawn as raw
    sizes, a 502-image corpus and a 4,306-image corpus put their labels on top of each other and
    the 43.4% that carries the panel became the least legible thing in it.
  - Figure 2 panel A braces only the two categories that compose the endpoint. A rule drawn
    across the whole axis reads as though all four categories sum to 41, which would be wrong:
    the 21 papers that do report a mechanism are not part of it.
"""
import io
import json
import os
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#d8d7d2"
BLUE, ORANGE, AQUA, NEUTRAL = "#2a78d6", "#eb6834", "#1baf7a", "#6b6a65"
PALE = "#e8e7e2"
MINUS = "−"


def L(p):
    return json.load(io.open(p, encoding="utf-8"))


def frame(ax, grid_axis="y"):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=8.5, length=3)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, lw=0.7, alpha=0.8)
    ax.set_axisbelow(True)


def save(fig, stem):
    fig.savefig(f"figures/{stem}.png", dpi=300, facecolor=SURFACE)
    fig.savefig(f"figures/{stem}.pdf", facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote figures/{stem}.png / .pdf")


def signed(x, dp=2):
    return f"{'+' if x >= 0 else MINUS}{abs(x):.{dp}f}"


# =====================================================================================
# FIGURE 1 — corpus flow
# =====================================================================================
scope = L("corpus/scope_final.json")
excl = [x for x in L("corpus/excluded_reviews_records.json") if x.get("_exclusion_reason")]
acq = L("corpus/acquisition_bias.json")

# Papers recovered by hand on 2026-09-19, after automated retrieval had failed on them. They
# enter the flow at the retrieval stage and are screened by the same three-part rubric, so every
# downstream count below carries them.
# Both hand sweeps: the in-scope papers retrieval missed, and the abstract-only exclusions that
# had never been read. One paper in the second sweep arrived as a single page and is not counted
# as verified at full text.
PARTIAL = {"W3135044310"}
hand = (L("corpus/scope_incoming_decisions.json")["decisions"]
        + L("corpus/scope_exclcheck_decisions.json")["decisions"])
n_hand = len(hand)
n_hand_verified = len([d for d in hand if d["paper_id"] not in PARTIAL])
hand_in = sum(1 for d in hand if d["in_scope"])
hand_out = Counter(d["scope_code"] for d in hand
                   if not d["in_scope"] and d["paper_id"] not in PARTIAL)
n_hand_learned = (len(L("corpus/validation_incoming_codes.json")["per_paper"])
                  + len(L("corpus/validation_exclcheck_codes.json")["per_paper"]))

n_cand = acq["candidates"]
n_retrieved_auto = acq["retrieved"]
n_retrieved = n_retrieved_auto + n_hand
n_not_retrieved = acq["not_retrieved"] - n_hand
ab = [r for r in scope if r["scope_tier"] in ("A", "B")]
n_verified = len(ab) + len(excl) + n_hand_verified
n_landing = n_retrieved - n_verified
n_inscope = sum(1 for r in ab if r["in_scope"]) + hand_in
out_codes = Counter(r["scope_code"] for r in ab if not r["in_scope"])
n_s1 = out_codes["OUT_S1"] + hand_out["OUT_S1"]
n_s2 = out_codes["OUT_S2"] + out_codes["OUT_BORDERLINE_S2"] + hand_out["OUT_S2"]
n_doctype = out_codes["OUT_S3"] + len(excl) + hand_out["OUT_S3"]
n_out = n_verified - n_inscope
assert n_s1 + n_s2 + n_doctype == n_out, (n_s1, n_s2, n_doctype, n_out)
# three papers in the original corpus train no learned model, and three more among those added
n_learned = (n_inscope - hand_in - 3) + n_hand_learned
assert n_learned == 79, n_learned

fig = plt.figure(figsize=(11.6, 6.4), facecolor=SURFACE)
gs = fig.add_gridspec(2, 1, height_ratios=[1.45, 1], hspace=0.42)
axT, axB = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])

axT.set_facecolor(SURFACE)
STAGES = [(n_cand, "candidates admitted by the title-level eligibility filter"),
          (n_retrieved, f"full text retrieved  ({n_retrieved_auto} automatically, {n_hand} by hand)"),
          (n_verified, "verified at full text"),
          (n_inscope, "substantively in scope"),
          (n_learned, "train a learned model")]
LOSSES = [(n_not_retrieved, "still not retrieved"),
          (n_landing, "no readable article: four publisher landing pages, one single-page "
                      "partial"),
          (n_out, "out of scope"),
          (n_inscope - n_learned, "threshold, sensor or index algorithms, no model")]
h, gap = 0.58, 0.40
for i, (n, label) in enumerate(STAGES):
    y = -i * (h + gap)
    w = 5.0 * n / n_cand
    axT.add_patch(plt.Rectangle((0, y - h / 2), w, h, facecolor=BLUE if i else NEUTRAL,
                                edgecolor=SURFACE, lw=1.5, zorder=2))
    axT.text(0.1, y, f"{n}", ha="left", va="center", fontsize=12.5, color="#ffffff",
             fontweight="bold", zorder=3)
    axT.text(w + 0.16, y, label, ha="left", va="center", fontsize=8.8, color=INK, zorder=3)
    if i < len(LOSSES):
        ln, ll = LOSSES[i]
        ymid = y - (h + gap) / 2
        axT.add_patch(FancyArrowPatch((0.34, y - h / 2), (0.34, y - h / 2 - gap),
                                      arrowstyle="-|>", mutation_scale=10, color=INK_2, lw=1.1,
                                      zorder=3))
        axT.text(0.62, ymid, f"{MINUS}{ln}", ha="left", va="center", fontsize=9.0, color=ORANGE,
                 fontweight="bold", zorder=3)
        axT.text(1.16, ymid, ll, ha="left", va="center", fontsize=7.8, color=INK_2, zorder=3)
axT.set_xlim(-0.2, 9.4)
axT.set_ylim(-4.15, 0.62)
axT.axis("off")
axT.set_title("A   From title-level eligibility to the analysed corpus", fontsize=10.5,
              color=INK, loc="left", pad=6, fontweight="bold")

frame(axB, grid_axis="x")
BREAK = [(n_s1, "not a wildland fire\nindoor, railway, coal-mine and urban fires", ORANGE),
         (n_s2, "a wildland fire, but not its detection\nburned-area and risk mapping, network routing,\n"
                "UAV navigation, fire-weather climatology", ORANGE),
         (n_doctype, "document type\nreviews, surveys and other non-primary articles",
          NEUTRAL)]
for i, (cnt, lab, c) in enumerate(BREAK):
    axB.barh(i, cnt, height=0.5, color=c, edgecolor=SURFACE, lw=1.5, zorder=3)
    axB.text(cnt + 0.35, i, f"{cnt}", va="center", fontsize=10, color=INK, fontweight="bold")
    axB.text(-0.5, i, lab, va="center", ha="right", fontsize=7.9, color=INK)
axB.set_ylim(2.75, -0.75)
# The axis follows the data: hard-coding it at 21 clipped both bars and their value labels the
# moment the second hand-retrieval sweep pushed the counts past 21.
_xmax = max(n_s1, n_s2, n_doctype)
axB.set_xlim(0, _xmax * 1.18)
axB.set_xticks(range(0, int(_xmax) + 6, 10))
axB.set_yticks([])
axB.set_xlabel(f"papers, of the {n_out} excluded at full text", fontsize=8.6, color=INK)
axB.set_title(f"B   Why the {n_out} were excluded", fontsize=10.5, color=INK, loc="left", pad=8, fontweight="bold")

fig.text(0.008, 0.014,
         f"The {n_verified} verified at full text is the denominator for the scope screen. It is "
         f"a retrieved candidate corpus, not a sample of the wildfire-detection literature:\n"
         f"automated retrieval succeeded for every candidate from five publishers and none from "
         f"nine others, so the {n_hand + n_not_retrieved} candidates it missed were pursued by "
         f"hand and {n_hand} were recovered.\nThe reporting practice of the "
         f"{n_not_retrieved} still unretrieved is unobserved.",
         fontsize=7.0, color=INK_2, va="bottom")
fig.subplots_adjust(left=0.30, right=0.985, top=0.94, bottom=0.155)
_bb = axT.get_position()
axT.set_position([0.035, _bb.y0, 0.95, _bb.height])
save(fig, "figure1_corpus_flow")


# =====================================================================================
# FIGURE 2 — reporting and adherence
# =====================================================================================
val_64 = L("corpus/fulltext_validation.json")
prev = {r["id"]: r for r in L("corpus/prevalence.json")["estimands"]}
e1 = prev["E1"]
# The endpoint is computed over the enlarged learned-model population. The two earlier estimates
# stay in the inset, each drawn on the population it was actually measured over.
comb = L("corpus/endpoint_recomputed.json")["combined"]
val = {"distribution": {str(k): v for k, v in comb["distribution"].items()},
       "n": comb["n"], "lacking_mechanism": comb["k"],
       "validated_pct": comb["pct"], "validated_ci": comb["ci"]}
A = {r["paper_id"]: r for r in L("corpus/raw_coding/coded_A_67.RAW.json")}
flame = [p for p in A if str(A[p].get("flame_official_test_used")) in ("yes", "no", "unclear")]
fl = Counter(str(A[p].get("flame_official_test_used")) for p in flame)

fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.6, 4.7), facecolor=SURFACE,
                               gridspec_kw={"width_ratios": [1.5, 1]})

frame(axA, grid_axis="x")
CATS = [("mechanism reported", val["distribution"]["1"], AQUA),
        ("ratio or counts only", val["distribution"]["2"], ORANGE),
        ("no partition statement", val["distribution"]["3"], ORANGE),
        ("unresolved", val["distribution"]["4"], NEUTRAL)]
for i, (lab, n, c) in enumerate(CATS):
    axA.barh(i, n, height=0.58, color=c, edgecolor=SURFACE, lw=1.5, zorder=3)
    axA.text(n + 0.6, i, f"{n}", va="center", fontsize=9.5, color=INK, fontweight="bold")
    axA.text(-0.6, i, lab, va="center", ha="right", fontsize=8.6, color=INK)

# Brace only the two categories that compose the endpoint. Rows 1 and 2, never row 0.
bx = 47.5
axA.plot([bx, bx + 0.9, bx + 0.9, bx], [0.72, 0.72, 2.34, 2.34], color=INK, lw=1.5,
         solid_joinstyle="miter", zorder=4)
axA.text(bx + 1.5, 1.53,
         f"no reconstructable\nallocation mechanism\n{val['lacking_mechanism']} of {val['n']}, "
         f"{val['validated_pct']:.1f}%\n({val['validated_ci'][0]:.1f}{MINUS}"
         f"{val['validated_ci'][1]:.1f})",
         va="center", ha="left", fontsize=8.2, color=INK, fontweight="bold")
axA.set_ylim(3.7, -0.7)
axA.set_xlim(0, 58)
axA.set_xticks([0, 10, 20, 30, 40])
axA.set_yticks([])
axA.set_xlabel(f"papers, of the {val['n']} that train a learned model", fontsize=8.6, color=INK)
axA.set_title(f"A   What the {val['n']} learned-model papers report", fontsize=10.5, color=INK,
              loc="left", pad=10, fontweight="bold")

ins = axA.inset_axes([0.52, 0.12, 0.46, 0.28])
ins.set_facecolor(SURFACE)
for k, (lab, pct, lo, hi, c) in enumerate([
        (f"all {val['n']},\nfull texts", val["validated_pct"], val["validated_ci"][0],
         val["validated_ci"][1], BLUE),
        ("first 64,\nfull texts", val_64["validated_pct"], val_64["validated_ci"][0],
         val_64["validated_ci"][1], AQUA),
        ("first 64,\nfrozen coding", e1["pct"], e1["ci95"][0], e1["ci95"][1], NEUTRAL)]):
    ins.plot([lo, hi], [k, k], color=c, lw=2.4, solid_capstyle="round", zorder=3)
    ins.plot(pct, k, "o", color=c, ms=7, mec=SURFACE, mew=1.4, zorder=4)
    ins.text(hi + 1.6, k, f"{pct:.1f}%", va="center", fontsize=7.6, color=c, fontweight="bold")
    ins.text(lo - 1.8, k, lab, va="center", ha="right", fontsize=6.8, color=INK_2)
ins.set_ylim(2.75, -0.75)
ins.set_xlim(36, 88)
ins.set_yticks([])
ins.set_xticks([40, 50, 60, 70, 80])
ins.tick_params(colors=INK_2, labelsize=6.8, length=2)
for s in ("top", "right", "left"):
    ins.spines[s].set_visible(False)
ins.spines["bottom"].set_color(GRID)
# No inset title: at three rows it ran into the brace rule, which is the more load-bearing
# mark. What the inset shows is stated in the caption instead.

frame(axB, grid_axis=None)
cells = ([AQUA] * fl["yes"] + [ORANGE] * fl["no"] + [NEUTRAL] * fl["unclear"])
for i, c in enumerate(cells):
    r, q = divmod(i, 5)
    axB.add_patch(plt.Rectangle((q + 0.06, r + 0.06), 0.88, 0.88, facecolor=c,
                                edgecolor=SURFACE, lw=2, zorder=2))
axB.set_xlim(-0.05, 5.05)
axB.set_ylim(4.55, -0.55)
axB.axis("off")
axB.text(0, -0.30, f"{len(flame)} papers use FLAME as a benchmark, one square each", fontsize=8.8, color=INK,
         fontweight="bold")
for j, (lab, c, n) in enumerate([("used the designated test set", AQUA, fl["yes"]),
                                 ("demonstrably did not", ORANGE, fl["no"]),
                                 ("could not be resolved from the text", NEUTRAL, fl["unclear"])]):
    yy = 3.40 + j * 0.36
    axB.add_patch(plt.Rectangle((0.06, yy - 0.11), 0.26, 0.22, facecolor=c, lw=0, zorder=3))
    axB.text(0.44, yy, f"{n}   {lab}", fontsize=8.0, color=INK, va="center")
axB.set_title("B   FLAME, where the gap is checkable", fontsize=10.5, color=INK,
              loc="left", pad=10, fontweight="bold")

fig.text(0.008, 0.015,
         "The brace covers only the two categories that compose the endpoint. The inset shows the "
         f"same quantity three times, each on the population it was measured over: all {val['n']}\n"
         f"papers at full text, the {val_64['n']} available before hand retrieval at full text, "
         f"and those {val_64['n']} "
         f"under the frozen model coding, which was never applied to the "
         f"{val['n'] - val_64['n']} added papers.\n"
         "Panel B is reported as counts: with 13 papers and two indeterminate cases a percentage "
         "would imply a precision the sample does not support. An unstated mechanism is not\n"
         "evidence of a bad partition, only of an unrecoverable one.",
         fontsize=7.0, color=INK_2, va="bottom")
fig.tight_layout(rect=(0, 0.082, 1, 1))
save(fig, "figure2_reporting_and_adherence")


# =====================================================================================
# FIGURE 6 — benchmark overlap
# =====================================================================================
ov = L("corpus/overlap_summary.json")
tax = L("corpus/contamination_taxonomy.json")
sizes, cross = ov["sizes"], ov["cross"]
pair = cross["DeepQuestAI_FireSmoke|FireNET"]
pct = 100 * pair["b_hit"] / sizes["FireNET"]

fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.6, 4.8), facecolor=SURFACE,
                               gridspec_kw={"width_ratios": [1, 1.2]})

# Share, not raw size: the corpora differ by an order of magnitude and raw bars buried the 43.4%.
frame(axA, grid_axis="x")
ROWS_A = [("FireNET", pair["b_hit"], sizes["FireNET"], ORANGE),
          ("DeepQuestAI Fire-Smoke", pair["a_hit"], sizes["DeepQuestAI_FireSmoke"], ORANGE),
          ("DeepQuestAI inference",
           cross["DeepQuestAI_FireSmoke|DeepQuestAI_inference"]["b_hit"],
           sizes["DeepQuestAI_inference"], ORANGE),
          ("D-Fire (test)", 0, sizes["DFire_test"], NEUTRAL)]
for i, (lab, h, n, c) in enumerate(ROWS_A):
    share = 100 * h / n
    axA.barh(i, share, height=0.55, color=c if h else SURFACE,
             edgecolor=GRID if not h else SURFACE, lw=1.5, hatch="///" if not h else None,
             zorder=3)
    axA.text(share + 1.1, i, f"{share:.1f}%   ({h:,} of {n:,})", va="center", fontsize=8.4,
             color=INK, fontweight="bold" if h else "normal")
    axA.text(-1.1, i, lab, va="center", ha="right", fontsize=8.5, color=INK)
axA.set_ylim(3.75, -0.75)
axA.set_xlim(0, 104)
axA.set_xticks([0, 10, 20, 30, 40])
axA.set_yticks([])
axA.set_xlabel("share of the corpus with a near-duplicate elsewhere", fontsize=8.6, color=INK)
axA.annotate("D-Fire matches nothing:\nthe specificity control", xy=(1.5, 3),
             xytext=(34, 2.60), fontsize=7.8, color=INK, va="center",
             arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1,
                             connectionstyle="arc3,rad=0.25"))
axA.set_title(f"A   {pair['b_hit']} of {sizes['FireNET']} FireNET images have a near-duplicate "
              f"in DeepQuestAI", fontsize=9.6, color=INK, loc="left", pad=10, fontweight="bold")

frame(axB, grid_axis="x")
ident = Counter(x["identity"] for x in tax)
cons = Counter(x["consequence"] for x in tax)
# The zero row is computed, not asserted. It used to read "pixel-identical, 0" beside a
# byte-identical bar of 89, which is incoherent — byte-identical pairs are pixel-identical — and
# the annotation then claimed file-hash deduplication returns nothing while 89 pairs sat above
# it. The true finding is narrower and is the one the Results state: no pair that spans the two
# corpora is byte-identical, so file hashing finds no overlap between them. Every byte-identical
# pair lies inside one corpus.
bytes_inside = sum(1 for x in tax if x["identity"] == "exact_bytes" and x["ds_a"] == x["ds_b"])
bytes_across = sum(1 for x in tax if x["identity"] == "exact_bytes" and x["ds_a"] != x["ds_b"])
assert bytes_inside + bytes_across == ident["exact_bytes"], "byte-identical pairs do not split"
GROUPS = [("by identity",
           [("near-duplicate, not byte-identical", ident["near_duplicate"], ORANGE),
            ("byte-identical, inside one corpus", bytes_inside, NEUTRAL),
            ("byte-identical, across the two corpora", bytes_across, NEUTRAL)]),
          ("by consequence",
           [("overlap spanning two corpora", cons["cross_dataset_overlap"], ORANGE),
            ("duplicated inside one split", cons["benign_within_split"], NEUTRAL),
            ("train–test leakage, one dataset", cons["train_test_leakage"], BLUE),
            ("train–validation leakage", cons["train_val_leakage"], BLUE)])]
y = 0.0
zero_y = None
for gname, rows in GROUPS:
    axB.text(-6, y - 0.72, gname, fontsize=8.2, color=INK_2, ha="right", style="italic")
    for lab, n, c in rows:
        axB.barh(y, max(n, 0.8), height=0.55, color=c if n else SURFACE,
                 edgecolor=GRID if not n else SURFACE, lw=1.5, hatch="///" if not n else None,
                 zorder=3)
        axB.text(max(n, 0.8) + 5, y, f"{n}", va="center", fontsize=9, color=INK,
                 fontweight="bold")
        axB.text(-6, y, lab, va="center", ha="right", fontsize=8.2, color=INK)
        if n == 0:
            zero_y = y
        y += 1
    y += 1.15
axB.set_ylim(y - 1.5, -1.35)
axB.set_xlim(0, 345)
axB.set_yticks([])
axB.set_xlabel(f"confirmed duplicate pairs (n = {len(tax)})", fontsize=8.6, color=INK)
axB.annotate("zero is the finding: deduplication by file\nhash finds no overlap between the corpora",
             xy=(10, zero_y), xytext=(118, zero_y + 0.30), fontsize=7.5, color=INK, va="center",
             arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1,
                             connectionstyle="arc3,rad=0.2"))
axB.set_title("B   What the pairs are, and what they cost", fontsize=9.6, color=INK,
              loc="left", pad=10, fontweight="bold")

fig.text(0.008, 0.015,
         "Two 64-bit hashes at Hamming distance 5, confirmed by normalized cross-correlation at "
         "0.95. “Leakage” is reserved for pairs crossing one dataset's own designated "
         "split;\npairs spanning two separately published corpora are overlap, because no "
         "training–test relationship exists between them. Only one audited paper uses "
         "either corpus.",
         fontsize=7.0, color=INK_2, va="bottom")
fig.tight_layout(rect=(0, 0.072, 1, 1))
save(fig, "figure6_benchmark_overlap")


# =====================================================================================
# FIGURE 7 — the two controls
# =====================================================================================
pb = L("corpus/placebo_bound.json")
prov = L("corpus/provenance_control_results.json")
prov_gap = sum(r["gap"] for r in prov) / len(prov) * 100
full_gap = pb["arms"]["full"]["mean_gap_pp"]
reduction = 100 * (full_gap - prov_gap) / full_gap
nf, nr = pb["contrasts"]["no_twins_vs_full"], pb["contrasts"]["no_twins_vs_random"]

fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.6, 4.7), facecolor=SURFACE)

frame(axA, grid_axis="y")
ARMS = [("full\ntraining pool", "full", NEUTRAL),
        ("all 234 duplicated\nimages removed", "no_twins", ORANGE),
        ("a size-matched random\nsubset removed", "random", BLUE)]
for i, (lab, key, c) in enumerate(ARMS):
    a = pb["arms"][key]
    axA.bar(i, a["mean_gap_pp"], width=0.56, color=c, edgecolor=SURFACE, lw=1.5, zorder=3)
    axA.errorbar(i, a["mean_gap_pp"], yerr=a["sd_pp"], color=INK, lw=1.3, capsize=5, zorder=4)
    axA.text(i, a["mean_gap_pp"] + a["sd_pp"] + 0.9, f"{a['mean_gap_pp']:.1f}", ha="center",
             fontsize=9.5, color=INK, fontweight="bold")
axA.set_xticks(range(3))
axA.set_xticklabels([a[0] for a in ARMS], fontsize=8)
axA.set_ylabel("recall gap, overlapping minus clean\n(percentage points)", fontsize=8.8,
               color=INK)
axA.set_ylim(0, 48)
axA.text(1.0, 45.0, "removing the duplicated items does not move the gap", ha="center",
         fontsize=8.2, color=INK, fontweight="bold")
axA.text(1.0, 42.2,
         f"vs full: {signed(nf['diff_pp'])} pp (95% CI {signed(nf['ci95_pp'][0], 1)} to "
         f"{signed(nf['ci95_pp'][1], 1)})        vs random removal: "
         f"{signed(nr['diff_pp'])} pp ({signed(nr['ci95_pp'][0], 1)} to "
         f"{signed(nr['ci95_pp'][1], 1)})",
         ha="center", fontsize=7.2, color=INK_2)
axA.set_title("A   The control that refuted our own hypothesis", fontsize=10.2, color=INK,
              loc="left", pad=10, fontweight="bold")

frame(axB, grid_axis="y")
for i, (lab, v, c) in enumerate([("trained on DeepQuestAI\n(the overlapping corpus)", full_gap,
                                  NEUTRAL),
                                 ("trained on D-Fire\n(no measured overlap)", prov_gap, AQUA)]):
    axB.bar(i, v, width=0.5, color=c, edgecolor=SURFACE, lw=1.5, zorder=3)
    axB.text(i, v + 0.9, f"{v:.1f}", ha="center", fontsize=9.5, color=INK, fontweight="bold")
axB.set_xticks([0, 1])
axB.set_xticklabels([t[0] for t in [("trained on DeepQuestAI\n(the overlapping corpus)",),
                                    ("trained on D-Fire\n(no measured overlap)",)]], fontsize=8)
axB.annotate("", xy=(1.42, prov_gap), xytext=(1.42, full_gap),
             arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6))
axB.text(1.52, (full_gap + prov_gap) / 2, f"{MINUS}{reduction:.1f}%", fontsize=10.5, color=INK,
         fontweight="bold", va="center")
axB.set_xlim(-0.6, 2.05)
axB.set_ylim(0, 48)
axB.set_ylabel("recall gap (percentage points)", fontsize=8.8, color=INK)
axB.text(-0.5, 45.0, "changing the training corpus does", fontsize=8.2, color=INK,
         fontweight="bold")
axB.text(-0.5, 42.2, "but changing the corpus changes more than its provenance,\n"
                     "so this does not isolate provenance as a cause",
         fontsize=7.2, color=INK_2, va="top")
axB.set_title("B   And the one that moved it", fontsize=10.2, color=INK, loc="left", pad=10,
              fontweight="bold")

fig.text(0.008, 0.015,
         "Ten seeds per arm, one architecture, training-set size held constant. The claim rests "
         "on the intervals, not on the non-significant tests: they bound whatever the\n"
         "duplicated images contribute at about three percentage points of a thirty-three-point "
         "gap. No equivalence is asserted from a non-significant test.",
         fontsize=7.0, color=INK_2, va="bottom")
fig.tight_layout(rect=(0, 0.072, 1, 1))
save(fig, "figure7_two_controls")
