"""The five pre-specified sensitivity analyses, as one matrix, plus the falsification tests.

Rows are estimands. Columns are the primary specification and the five sensitivities fixed in
PRE_CODING_FREEZE.md §8. Every cell is computed whether or not the result is convenient, and
the summary marks direction preserved, material magnitude change, and conclusion changed.

No sixth sensitivity is added here. Anything run later must be labelled post-hoc.
"""
import json
import io
import os
import sys
from math import sqrt
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "scripts")
import reported_fractions as RF  # noqa: E402
from prevalence import ESTIMANDS, wilson  # noqa: E402  same definitions, not re-specified

MATERIAL = 10.0  # percentage points; fixed here before the matrix is inspected

A = {r["paper_id"]: r for r in
     json.load(io.open("corpus/raw_coding/coded_A_67.RAW.json", encoding="utf-8"))}
B = {r["paper_id"]: r for r in
     json.load(io.open("corpus/raw_coding/coded_B_67.RAW.json", encoding="utf-8"))}
rel = json.load(io.open("corpus/reliability_67.json", encoding="utf-8"))["fields"]
scope = {r["paper_id"]: r for r in
         json.load(io.open("corpus/scope_final.json", encoding="utf-8"))}
ids = sorted(set(A) & set(B))

PREFIX = [("10.3390", "MDPI"), ("10.1109", "IEEE"), ("10.1016", "Elsevier"),
          ("10.1007", "Springer"), ("10.1038", "Nature Portfolio"), ("10.1371", "PLOS"),
          ("10.3389", "Frontiers")]


def pub_of(pid):
    return scope.get(pid, {}).get("publisher", "unknown")


def rate(pool, pred, coder):
    pool = [i for i in pool]
    if not pool:
        return None, 0, 0
    k = sum(1 for i in pool if pred(coder[i]))
    return 100.0 * k / len(pool), k, len(pool)


def main():
    popsA = RF.coding_populations(A)
    popsB = RF.coding_populations(B)

    print("SENSITIVITY MATRIX — five pre-specified specifications")
    print(f"Material threshold: {MATERIAL:.0f} percentage points, fixed before inspection.")
    print("=" * 124)
    print(f"{'id':4s} {'primary':>9s} {'coderB':>9s} {'agreed':>9s} {'unclear-in':>11s} "
          f"{'contested':>10s} {'LOPO range':>16s} {'maxdev':>7s}  {'flags'}")
    print("-" * 124)

    rows = []
    for eid, label, pop, driver, pred, status in ESTIMANDS:
        poolA = sorted(popsA[pop])
        primary, k, n = rate(poolA, pred, A)

        # 1. coder choice
        vB, _, _ = rate(sorted(popsB[pop]), pred, B)
        agreed = [i for i in poolA if i in popsB[pop]
                  and str(A[i].get(driver)) == str(B[i].get(driver))]
        vAg, _, _ = rate(agreed, pred, A)

        # 2. `unclear` counted into the numerator
        def pred_unclear_in(r):
            return pred(r) or str(r.get(driver, "")).strip().lower() == "unclear"
        vUn, _, _ = rate(poolA, pred_unclear_in, A)

        # 3. contested scope cases — the 9 flagged in the scope layer, dropped from the pool
        contested = {p for p in poolA if scope.get(p, {}).get("contested")}
        vCon, _, _ = rate([i for i in poolA if i not in contested], pred, A)

        # 4. leave-one-publisher-out
        lopo = {}
        for pub in sorted({pub_of(i) for i in poolA}):
            keep = [i for i in poolA if pub_of(i) != pub]
            if len(keep) >= 10:
                v, _, _ = rate(keep, pred, A)
                lopo[pub] = v
        lo, hi = (min(lopo.values()), max(lopo.values())) if lopo else (None, None)
        worst_pub = max(lopo, key=lambda p: abs(lopo[p] - primary)) if lopo else None

        # 5. modality strata — descriptive only, no test
        strata = {}
        for m in sorted({scope.get(i, {}).get("modality") for i in poolA}):
            sub = [i for i in poolA if scope.get(i, {}).get("modality") == m]
            if sub:
                v, kk, nn = rate(sub, pred, A)
                strata[m] = (round(v, 1), kk, nn)

        cells = [v for v in [vB, vAg, vUn, vCon] + list(lopo.values()) if v is not None]
        maxdev = max(abs(c - primary) for c in cells) if cells else 0.0
        direction_ok = all((c > 50) == (primary > 50) for c in cells) if primary is not None else True
        flags = []
        if maxdev > MATERIAL:
            flags.append("MATERIAL")
        if not direction_ok:
            flags.append("DIRECTION")
        lr = f"{lo:.1f}-{hi:.1f}" if lo is not None else "n/a"
        print(f"{eid:4s} {primary:8.1f}% {vB:8.1f}% {(vAg if vAg is not None else float('nan')):8.1f}% "
              f"{vUn:10.1f}% {vCon:9.1f}% {lr:>16s} {maxdev:6.1f}  {','.join(flags)}")

        rows.append({"id": eid, "label": label, "population": pop, "driver": driver,
                     "numerator": k, "denominator": n, "primary": round(primary, 2),
                     "ci95": [round(100 * x, 2) for x in wilson(k, n)],
                     "reliability_class": rel.get(driver, {}).get("class"),
                     "kappa": rel.get(driver, {}).get("kappa"),
                     "sens": {"coderB": round(vB, 2),
                              "agreed_only": None if vAg is None else round(vAg, 2),
                              "unclear_in": round(vUn, 2),
                              "contested_dropped": round(vCon, 2),
                              "lopo": {p: round(v, 2) for p, v in lopo.items()},
                              "lopo_max_influence": worst_pub},
                     "modality_strata": strata,
                     "max_deviation_pp": round(maxdev, 2),
                     "direction_preserved": bool(direction_ok),
                     "material_change": bool(maxdev > MATERIAL)})

    n_mat = sum(1 for r in rows if r["material_change"])
    print(f"\n  {n_mat} of {len(rows)} estimands show a deviation above {MATERIAL:.0f} pp "
          f"under any specification.")

    # ---------------------------------------------------------------- falsification
    print("\n" + "=" * 124)
    print("PRE-DECLARED FALSIFICATION TESTS (PRE_CODING_FREEZE.md §9)")
    print("=" * 124)
    by = {r["id"]: r for r in rows}
    sp_k = rel.get("split_protocol", {}).get("kappa")
    tests = [
        ("E1 low -> ratio-without-mechanism does not generalise; withdraw ledger claim B2",
         by["E1"]["primary"], lambda v: v >= 30,
         f"E1 = {by['E1']['primary']:.1f}% (CI {by['E1']['ci95'][0]:.1f}-{by['E1']['ci95'][1]:.1f})"),
        ("E5 or E6 high -> no field-deployment gap; drop the operational-metrics contribution",
         max(by["E5"]["primary"], by["E6"]["primary"]), lambda v: v <= 40,
         f"E5 = {by['E5']['primary']:.1f}%, E6 = {by['E6']['primary']:.1f}%"),
        ("E9 non-trivial -> the duplicate-check claim weakens",
         by["E9"]["primary"], lambda v: v <= 20,
         f"E9 = {by['E9']['primary']:.1f}%"),
        ("reliability on 67 materially worse than on 15 -> round 2 was a small-sample artefact",
         sp_k, lambda v: v is not None and v >= 0.80,
         f"split_protocol kappa = {sp_k:.3f} on 67 (was 1.000 on 15); threshold 0.80"),
    ]
    for desc, val, ok, detail in tests:
        verdict = "SUPPORTED" if ok(val) else "FALSIFIED"
        print(f"  [{verdict:9s}] {desc}")
        print(f"              {detail}")

    json.dump({"material_threshold_pp": MATERIAL, "estimands": rows},
              io.open("corpus/sensitivity_matrix.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nwrote corpus/sensitivity_matrix.json")


if __name__ == "__main__":
    main()
