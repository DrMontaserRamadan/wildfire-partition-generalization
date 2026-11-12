"""Full-corpus reliability on all 67 papers, and the variable classification.

Computed on the two INDEPENDENT codings. No adjudication, no consensus, no field is quietly
repaired. Classification thresholds were fixed in PRE_CODING_FREEZE.md §6 before any of these
papers was coded, so a field's class is determined by the rule, not chosen after seeing it.

Reports, per field: raw agreement, kappa where it is mathematically meaningful, disagreement
count, the category-transition matrix, disagreement involving the three absence states, and a
test for systematic directional disagreement between coders.
"""
import json
import io
import os
import sys
from collections import Counter, defaultdict
from math import comb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "scripts")
from agreement import norm, kappa  # noqa: E402  same code path as rounds 1 and 2

# carried metadata, judged by nobody; excluded for the same reason as in rounds 1 and 2
# `title` is copied from the shard, not judged; scoring it produced raw 0.49 purely because one
# instance omitted the key. Same class of defect as split_protocol_quote2 (F3).
METADATA = {"coder", "doi", "venue", "year", "publisher", "modality",
            "coding_convention", "coder_notes", "paper_id", "title"}
# P2: free text, not categories. Excluded from classification IN ADVANCE, not after seeing them.
FREE_TEXT = {"datasets_used", "split_stated_verbatim", "headline_metric",
             "target_hardware_named"}
ABSENCE = {"not_reported", "not_applicable", "unclear", "none_verifiable", "not_checked", ""}

THRESHOLD = 0.80  # unchanged since round 1


def binom_two_sided(k, n):
    """Exact two-sided sign test that directional disagreement is symmetric."""
    if n == 0:
        return 1.0
    p = sum(comb(n, i) for i in range(0, min(k, n - k) + 1)) / (2 ** n)
    return min(1.0, 2 * p)


def classify(raw, k, top_share):
    """The rule fixed in PRE_CODING_FREEZE.md §6. Applied mechanically."""
    skewed = top_share > 0.90
    if (k == k and k >= THRESHOLD) or (skewed and raw >= 0.90):
        return "PRIMARY-SAFE"
    if (k == k and k >= 0.60) or (k != k and raw >= 0.80):
        return "SECONDARY-QUALIFIED"
    if k == k and k >= 0.40:
        return "EXPLORATORY"
    return "UNRELIABLE-REMOVE"


def main():
    A = {r["paper_id"]: r for r in
         json.load(io.open("corpus/raw_coding/coded_A_67.RAW.json", encoding="utf-8"))}
    B = {r["paper_id"]: r for r in
         json.load(io.open("corpus/raw_coding/coded_B_67.RAW.json", encoding="utf-8"))}
    ids = sorted(set(A) & set(B))
    print(f"FULL-CORPUS RELIABILITY — {len(ids)} papers, two independent codings")
    print(f"Threshold kappa >= {THRESHOLD}, fixed before coding and unchanged since round 1.")
    print("=" * 100)

    # Evidence fields are excluded, not scored. The test must be `"_quote" in k`, not
    # `k.endswith("_quote")`: one instance emits `split_protocol_quote2` for papers needing a
    # second quote, and an endswith test would have scored that as a rubric variable present in
    # one coder and absent in the other — a fabricated total-disagreement field. Caught by a
    # completeness audit run before any substantive result was examined.
    def is_evidence(k):
        # `split_stated_verbatim_2` is a second verbatim quote, not a construct; the suffix
        # test alone missed it because the name ends in "_2".
        return ("_quote" in k or "_verbatim" in k or k.endswith("_evidence"))

    fields = []
    for i in ids:
        for k in list(A[i]) + list(B[i]):
            if k in METADATA or is_evidence(k) or k in fields:
                continue
            fields.append(k)

    # Shard membership. Role A is four distinct instances and so is role B, so the rater PAIR
    # changes between shards. Pooled kappa estimates agreement between the two PROCEDURES, not
    # between two individual raters; per-pair values are reported alongside so that
    # instance-level heterogeneity cannot hide inside a single pooled number.
    # See notes/CODER_ALLOCATION_DESIGN.md, written before any output was inspected.
    shard_of = {}
    for s in range(4):
        for r in json.load(io.open(f"corpus/shards/shard_{s}.json", encoding="utf-8")):
            shard_of[r["paper_id"]] = s

    results = {}
    for f in fields:
        pairs, dis = [], []
        per_shard = {s: [] for s in range(4)}
        for i in ids:
            a, b = norm(A[i].get(f)), norm(B[i].get(f))
            pairs.append((a, b))
            per_shard[shard_of[i]].append((a, b))
            if a != b:
                dis.append((i, a, b))
        raw = sum(1 for a, b in pairs if a == b) / len(pairs)
        kap = kappa(pairs)

        shard_raw = {s: (sum(1 for a, b in v if a == b) / len(v) if v else float("nan"))
                     for s, v in per_shard.items()}
        shard_kappa = {s: kappa(v) for s, v in per_shard.items()}
        vals = [v for v in shard_raw.values() if v == v]
        spread = (max(vals) - min(vals)) if vals else float("nan")
        heterogeneous = spread == spread and spread > 0.25
        marg = Counter(a for a, _ in pairs)
        top = marg.most_common(1)[0][1] / len(pairs)
        absence_only = sum(1 for _, a, b in dis if a in ABSENCE and b in ABSENCE)

        # systematic direction: is one coder consistently on one side of a 2-category split?
        trans = Counter((a, b) for _, a, b in dis)
        direction = None
        if trans:
            (a1, b1), n1 = trans.most_common(1)[0]
            n2 = trans.get((b1, a1), 0)
            if n1 + n2 >= 4:
                p = binom_two_sided(min(n1, n2), n1 + n2)
                if p < 0.05:
                    direction = (a1, b1, n1, n2, p)

        # The class is decided ONLY by the frozen rule. The heterogeneity flag is carried
        # into the report but deliberately does not alter the class.
        cls = "EXCLUDED (free text, P2)" if f in FREE_TEXT else classify(raw, kap, top)
        results[f] = {"raw": raw, "kappa": None if kap != kap else kap, "top_share": top,
                      "n_disagree": len(dis), "absence_only_disagreements": absence_only,
                      "class": cls,
                      "per_shard_raw": {s: (None if v != v else round(v, 4))
                                        for s, v in shard_raw.items()},
                      "per_shard_kappa": {s: (None if v != v else round(v, 4))
                                          for s, v in shard_kappa.items()},
                      "shard_spread": None if spread != spread else round(spread, 4),
                      "heterogeneous": bool(heterogeneous),
                      "transitions": {f"{a} -> {b}": n for (a, b), n in
                                      trans.most_common()},
                      "direction": (None if direction is None else
                                    {"a": direction[0], "b": direction[1], "n_ab": direction[2],
                                     "n_ba": direction[3], "p": direction[4]}),
                      "marginal": dict(marg.most_common()),
                      "disagreements": dis}

    order = {"PRIMARY-SAFE": 0, "SECONDARY-QUALIFIED": 1, "EXPLORATORY": 2,
             "UNRELIABLE-REMOVE": 3, "EXCLUDED (free text, P2)": 4}
    print(f"\n{'field':34s} {'raw':>5s} {'kappa':>7s} {'top':>5s} {'dis':>4s} {'abs':>4s}  class")
    print("-" * 100)
    for f in sorted(results, key=lambda x: (order[results[x]["class"]], -results[x]["raw"])):
        r = results[f]
        ks = "    n/a" if r["kappa"] is None else f"{r['kappa']:7.3f}"
        print(f"{f:34s} {r['raw']:5.2f} {ks} {r['top_share']:5.2f} {r['n_disagree']:4d} "
              f"{r['absence_only_disagreements']:4d}  {r['class']}")

    print("\n" + "=" * 100)
    print("PER-SHARD-PAIR AGREEMENT — role A is 4 instances, role B is 4 instances")
    print("The pooled figure above estimates agreement between two PROCEDURES, not two raters.")
    print("=" * 100)
    print(f"{'field':34s} {'pair0':>7s} {'pair1':>7s} {'pair2':>7s} {'pair3':>7s} "
          f"{'spread':>7s}  flag")
    print("-" * 100)
    het = []
    for f in sorted(results, key=lambda x: -(results[x]["shard_spread"] or 0)):
        r = results[f]
        if r["class"] == "EXCLUDED (free text, P2)":
            continue
        if (r["shard_spread"] or 0) < 0.01 and not r["n_disagree"]:
            continue  # perfect everywhere; nothing to expose
        cells = " ".join(f"{(r['per_shard_raw'][s] if r['per_shard_raw'][s] is not None else 0):7.2f}"
                         for s in range(4))
        flag = "HETEROGENEOUS" if r["heterogeneous"] else ""
        if r["heterogeneous"]:
            het.append(f)
        print(f"{f:34s} {cells} {(r['shard_spread'] or 0):7.2f}  {flag}")
    print(f"\n  {len(het)} field(s) flagged HETEROGENEOUS (per-pair raw agreement spans > 0.25).")
    print("  The flag does NOT change the class — the frozen rule decides that. It is carried")
    print("  so no pooled statistic is read as more stable than it is.")
    if het:
        print("  flagged: " + ", ".join(het))

    print("\n" + "=" * 100)
    print("CLASSIFICATION SUMMARY")
    print("=" * 100)
    byc = Counter(r["class"] for r in results.values())
    for c in sorted(byc, key=lambda x: order[x]):
        print(f"  {c:28s} {byc[c]:3d}")
        for f in sorted(results):
            if results[f]["class"] == c:
                print(f"      {f}")

    print("\n" + "=" * 100)
    print("SYSTEMATIC DIRECTIONAL DISAGREEMENT (sign test, p < 0.05)")
    print("=" * 100)
    any_dir = False
    for f in sorted(results):
        d = results[f]["direction"]
        if d:
            any_dir = True
            print(f"  {f:32s} A={d['a'][:18]:18s} B={d['b'][:18]:18s} "
                  f"{d['n_ab']}x vs {d['n_ba']}x reversed, p={d['p']:.4f}")
    if not any_dir:
        print("  none detected — disagreements are not systematically one-directional")

    print("\n" + "=" * 100)
    print("CATEGORY TRANSITIONS for fields that are not PRIMARY-SAFE")
    print("=" * 100)
    for f in sorted(results):
        r = results[f]
        if r["class"] in ("PRIMARY-SAFE", "EXCLUDED (free text, P2)") or not r["transitions"]:
            continue
        print(f"\n  [{f}]  raw {r['raw']:.2f}  {r['class']}")
        for t, n in list(r["transitions"].items())[:8]:
            print(f"      {n:3d}x  {t}")

    json.dump({"n_papers": len(ids), "threshold": THRESHOLD,
               "fields": {f: {k: v for k, v in r.items() if k != "disagreements"}
                          for f, r in results.items()},
               "disagreements": {f: r["disagreements"] for f, r in results.items()
                                 if r["disagreements"]}},
              io.open("corpus/reliability_67.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nwrote corpus/reliability_67.json")


if __name__ == "__main__":
    main()
