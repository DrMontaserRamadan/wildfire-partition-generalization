"""Compare the full-text validation of the central construct against the frozen model coding.

The frozen coding is preserved untouched. This is validation, not recoding: where the two
disagree, the validated classification governs, because it rests on the complete article rather
than on a quota-limited excerpt.

Validation categories, fixed by the reviewer before the pass:
  1 mechanism reported   2 ratio/counts only   3 no partition statement   4 unresolved
"""
import json
import io
import os
from math import sqrt
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
Z = 1.959963984540054


def wilson(k, n):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


# frozen code -> expected validation category
MAP = {
    "official_heldout": 1, "explicitly_random": 1, "group_disjoint": 1,
    "k_fold_random": 1, "cross_dataset": 1,
    "ratio_only_mechanism_unstated": 2, "augment_then_split": 2,
    "no_split_statement": 3, "internally_inconsistent": 4,
}


def main():
    packet = json.load(io.open("corpus/fulltext_validation_packet.json", encoding="utf-8"))
    idx = {i: r["paper_id"] for i, r in enumerate(packet)}
    A = {r["paper_id"]: r for r in
         json.load(io.open("corpus/raw_coding/coded_A_67.RAW.json", encoding="utf-8"))}

    val = {}
    for line in io.open("corpus/validation/ALL.tsv", encoding="utf-8"):
        line = line.rstrip("\n")
        if not line:
            continue
        i, cat, reason = line.split("\t", 2)
        val[idx[int(i)]] = (int(cat), reason)

    assert len(val) == 64, f"{len(val)} validated, expected 64"

    dist = Counter(c for c, _ in val.values())
    print("FULL-TEXT VALIDATION OF THE CENTRAL CONSTRUCT")
    print("=" * 92)
    print(f"  papers validated: {len(val)} (all learned-model papers)")
    print("  source: complete stored full text, not the coding excerpt\n")
    LBL = {1: "mechanism reported", 2: "ratio/counts only",
           3: "no partition statement", 4: "unresolved"}
    for c in (1, 2, 3, 4):
        print(f"  {c}  {LBL[c]:26s} {dist[c]:3d}")

    lacking = dist[2] + dist[3]
    n = len(val)
    lo, hi = wilson(lacking, n)
    print(f"\n  NO RECONSTRUCTABLE ALLOCATION MECHANISM (2+3): "
          f"{lacking}/{n} = {100*lacking/n:.1f}%  95% CI {100*lo:.1f}-{100*hi:.1f}")
    n2 = n - dist[4]
    lo2, hi2 = wilson(lacking, n2)
    print(f"  excluding the {dist[4]} unresolved:              "
          f"{lacking}/{n2} = {100*lacking/n2:.1f}%  95% CI {100*lo2:.1f}-{100*hi2:.1f}")
    lo3, hi3 = wilson(lacking + dist[4], n)
    print(f"  counting unresolved as lacking:          "
          f"{lacking+dist[4]}/{n} = {100*(lacking+dist[4])/n:.1f}%  "
          f"95% CI {100*lo3:.1f}-{100*hi3:.1f}")

    # ---- agreement with the frozen coding ----
    print("\n" + "=" * 92)
    print("AGREEMENT WITH THE FROZEN MODEL CODING")
    print("=" * 92)
    agree, changed = 0, []
    for pid, (cat, reason) in val.items():
        frozen = str(A[pid].get("split_protocol"))
        expected = MAP.get(frozen)
        if expected == cat:
            agree += 1
        else:
            changed.append((pid, frozen, expected, cat, reason))
    print(f"  concordant: {agree}/{len(val)} = {100*agree/len(val):.1f}%")
    print(f"  reclassified by full-text validation: {len(changed)}\n")
    for pid, frozen, exp, cat, reason in sorted(changed, key=lambda r: r[1]):
        print(f"  {pid}  frozen={frozen} (->cat {exp})  validated=cat {cat}")
        print(f"      {reason[:150]}")

    # ---- effect on the headline ----
    print("\n" + "=" * 92)
    print("EFFECT ON THE PRIMARY ESTIMAND")
    print("=" * 92)
    frozen_e1 = sum(1 for pid in val if str(A[pid].get("split_protocol"))
                    in ("ratio_only_mechanism_unstated", "no_split_statement"))
    flo, fhi = wilson(frozen_e1, n)
    print(f"  frozen E1     {frozen_e1}/{n} = {100*frozen_e1/n:.1f}%  "
          f"95% CI {100*flo:.1f}-{100*fhi:.1f}")
    print(f"  validated     {lacking}/{n} = {100*lacking/n:.1f}%  "
          f"95% CI {100*lo:.1f}-{100*hi:.1f}")
    print(f"  difference    {100*lacking/n - 100*frozen_e1/n:+.1f} percentage points")
    print("\n  The validated figure governs. The frozen figure is disclosed alongside it.")

    json.dump({"n": n, "distribution": {str(k): v for k, v in dist.items()},
               "lacking_mechanism": lacking,
               "validated_pct": round(100 * lacking / n, 2),
               "validated_ci": [round(100 * lo, 2), round(100 * hi, 2)],
               "excl_unresolved": {"k": lacking, "n": n2,
                                   "pct": round(100 * lacking / n2, 2),
                                   "ci": [round(100 * lo2, 2), round(100 * hi2, 2)]},
               "frozen_E1": frozen_e1,
               "frozen_pct": round(100 * frozen_e1 / n, 2),
               "concordance": round(100 * agree / len(val), 2),
               "n_reclassified": len(changed),
               "reclassified": [{"paper_id": p, "frozen": f, "frozen_cat": e,
                                 "validated_cat": c, "reason": r}
                                for p, f, e, c, r in changed],
               "per_paper": {p: {"category": c, "reason": r} for p, (c, r) in val.items()}},
              io.open("corpus/fulltext_validation.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nwrote corpus/fulltext_validation.json")


if __name__ == "__main__":
    main()
