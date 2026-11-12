"""Complete frozen x validated cross-tabulation for all 64 learned-model papers.

Reviewer point 6B: the eight reclassifications must reconcile exactly against the full table,
and the agreement between the two classifications must be reported as a statistic, not as a
bare concordance percentage.
"""
import json
import io
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

MAP = {
    "official_heldout": 1, "explicitly_random": 1, "group_disjoint": 1,
    "k_fold_random": 1, "cross_dataset": 1,
    "ratio_only_mechanism_unstated": 2, "augment_then_split": 2,
    "no_split_statement": 3, "internally_inconsistent": 4,
}
LBL = {1: "mechanism reported", 2: "ratio/counts only",
       3: "no partition statement", 4: "unresolved"}


def kappa(pairs):
    n = len(pairs)
    cats = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    if n == 0 or len(cats) < 2:
        return float("nan")
    po = sum(1 for a, b in pairs if a == b) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    return float("nan") if abs(1 - pe) < 1e-12 else (po - pe) / (1 - pe)


def main():
    val = json.load(io.open("corpus/fulltext_validation.json", encoding="utf-8"))
    A = {r["paper_id"]: r for r in
         json.load(io.open("corpus/raw_coding/coded_A_67.RAW.json", encoding="utf-8"))}
    per = val["per_paper"]

    rows = []
    for pid, rec in per.items():
        frozen_code = str(A[pid].get("split_protocol"))
        rows.append((pid, frozen_code, MAP[frozen_code], rec["category"]))

    assert len(rows) == 64, f"{len(rows)} rows, expected 64"

    # --- cross-tab on the mapped 4-category scale ---
    ct = Counter((f, v) for _, _, f, v in rows)
    print("CROSS-TABULATION — frozen model coding (rows) x full-text validation (columns)")
    print("=" * 84)
    print(f"{'frozen \\ validated':28s} " + " ".join(f"{LBL[c][:14]:>15s}" for c in (1, 2, 3, 4))
          + f" {'total':>7s}")
    for f in (1, 2, 3, 4):
        tot = sum(ct[(f, v)] for v in (1, 2, 3, 4))
        print(f"{LBL[f]:28s} " + " ".join(f"{ct[(f,v)]:15d}" for v in (1, 2, 3, 4))
              + f" {tot:7d}")
    print(f"{'total':28s} " + " ".join(f"{sum(ct[(f,v)] for f in (1,2,3,4)):15d}"
                                       for v in (1, 2, 3, 4))
          + f" {len(rows):7d}")

    agree = sum(ct[(c, c)] for c in (1, 2, 3, 4))
    off = len(rows) - agree
    k = kappa([(f, v) for _, _, f, v in rows])
    print(f"\n  on-diagonal (concordant) : {agree}/{len(rows)} = {100*agree/len(rows):.1f}%")
    print(f"  off-diagonal (reclassified): {off}")
    print(f"  Cohen's kappa, frozen vs validated: {k:.3f}")
    assert off == val["n_reclassified"], "reclassification count does not reconcile"
    print(f"  reconciles with the disclosed reclassification count: {val['n_reclassified']}")

    # --- the full frozen-code breakdown, so nothing is hidden by the 4-category mapping ---
    print("\n" + "=" * 84)
    print("BY ORIGINAL FROZEN CODE (pre-mapping), showing where each moved")
    print("=" * 84)
    bycode = {}
    for pid, code, f, v in rows:
        bycode.setdefault(code, Counter())[v] += 1
    for code in sorted(bycode):
        c = bycode[code]
        tot = sum(c.values())
        moved = tot - c[MAP[code]]
        print(f"  {code:32s} n={tot:2d}  -> " +
              ", ".join(f"cat{v}:{c[v]}" for v in (1, 2, 3, 4) if c[v]) +
              (f"   ({moved} moved)" if moved else "   (all stable)"))

    # --- the two headline quantities, reconciled ---
    frozen_e1 = sum(1 for _, code, _, _ in rows
                    if code in ("ratio_only_mechanism_unstated", "no_split_statement"))
    validated = sum(1 for _, _, _, v in rows if v in (2, 3))
    print("\n" + "=" * 84)
    print("HEADLINE RECONCILIATION")
    print("=" * 84)
    print(f"  frozen E1 (ratio_only + no_split_statement)   {frozen_e1}/64")
    print(f"  validated (categories 2 + 3)                  {validated}/64")
    print(f"  net change                                    {validated - frozen_e1:+d}")
    gained = [(p, c) for p, c, _, v in rows
              if v in (2, 3) and c not in ("ratio_only_mechanism_unstated", "no_split_statement")]
    lost = [(p, c) for p, c, _, v in rows
            if v not in (2, 3) and c in ("ratio_only_mechanism_unstated", "no_split_statement")]
    print(f"    entered the numerator: {len(gained)}  " +
          ", ".join(f"{p} ({c})" for p, c in gained))
    print(f"    left the numerator:    {len(lost)}  " +
          ", ".join(f"{p} ({c})" for p, c in lost))
    assert len(gained) - len(lost) == validated - frozen_e1, "numerator movement does not reconcile"
    print("  numerator movement reconciles exactly.")

    json.dump({"crosstab": {f"{f}_{v}": ct[(f, v)] for f in (1, 2, 3, 4) for v in (1, 2, 3, 4)},
               "concordant": agree, "reclassified": off, "kappa": round(k, 4),
               "frozen_numerator": frozen_e1, "validated_numerator": validated,
               "entered": [p for p, _ in gained], "left": [p for p, _ in lost]},
              io.open("corpus/crosstab_frozen_validated.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nwrote corpus/crosstab_frozen_validated.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
