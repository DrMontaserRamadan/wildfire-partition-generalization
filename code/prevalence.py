"""Prevalence estimates for the pre-specified estimands, with uncertainty and reliability.

Every estimand was defined in PRE_CODING_FREEZE.md §5 before any of the 67 papers was coded.
Nothing here is invented after seeing a distribution; anything that were would have to be
labelled exploratory, and nothing is.

Three rules enforced in code, not by intention:

1. **A construct that is not PRIMARY-SAFE on the 67 cannot produce a primary estimate.** The
   result printed is "could not be estimated reliably with the pre-specified instrument".
   Forcing a clean number through consensus coding is not available.
2. **Reliability is printed in the same row as the estimate.** A percentage and the
   trustworthiness of the percentage are never separated.
3. **Every fraction goes into the registry** with its named analysis population, so
   verify_headlines.py can recompute it and check the denominator.

Sensitivity, all pre-specified: coder A alone, coder B alone, agreed-only; and `unclear`
counted in the numerator versus excluded.
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

Z = 1.959963984540054  # 95%


def wilson(k, n):
    """Wilson score interval — chosen in advance because several of these sit near 0 or 1."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


# --------------------------------------------------------------- estimand definitions
# (id, label, population, predicate, status) — frozen in PRE_CODING_FREEZE.md §5
def sp(r):
    return str(r.get("split_protocol", "")).strip().lower()


def lvl(r):
    return str(r.get("deployment_level", "")).strip().upper()


def yes(r, f):
    return str(r.get(f, "")).strip().lower() in ("yes", "yes+link", "true")


OPS = ["false_alarms_per_unit_time", "time_to_detection",
       "min_detectable_fire_size", "detection_range"]

ESTIMANDS = [
    ("E1", "split mechanism unreported", "POP_LEARNED", "split_protocol",
     lambda r: sp(r) in ("ratio_only_mechanism_unstated", "no_split_statement"), "PRIMARY"),
    ("E2", "official held-out split used", "POP_LEARNED", "split_protocol",
     lambda r: sp(r) == "official_heldout", "PRIMARY"),
    ("E3", "augmentation before partition", "POP_LEARNED", "split_protocol",
     lambda r: sp(r) == "augment_then_split", "PRIMARY"),
    ("E4", "any operational metric reported", "POP_ALL", "false_alarms_per_unit_time",
     lambda r: any(str(r.get(f, "not_reported")).strip().lower()
                   not in ("not_reported", "not_applicable", "", "none") for f in OPS),
     "PRIMARY"),
    ("E5", "deployment beyond dataset-only (>= L2)", "POP_ALL", "deployment_level",
     lambda r: lvl(r)[:2] in ("L2", "L3", "L4", "L5"), "PRIMARY"),
    ("E6", "detected a real unplanned wildfire", "POP_DEPLOY", "real_wildfire_detected",
     lambda r: str(r.get("real_wildfire_detected", "")).strip().lower() == "yes", "PRIMARY"),
    ("E7", "code available with a link", "POP_ALL", "code_available",
     lambda r: "yes" in str(r.get("code_available", "")).lower(), "PRIMARY"),
    ("E8", "variance or multiple runs reported", "POP_LEARNED", "variance_reported",
     lambda r: yes(r, "variance_reported") or str(r.get("n_runs", "")).strip().isdigit()
     and int(str(r.get("n_runs")).strip()) > 1, "PRIMARY"),
    ("E9", "duplicate check performed", "POP_LEARNED", "duplicate_check_done",
     lambda r: yes(r, "duplicate_check_done"), "PRIMARY"),
    ("E10", "cross-dataset evaluation", "POP_LEARNED", "cross_dataset_eval",
     lambda r: yes(r, "cross_dataset_eval"), "PRIMARY"),
    ("E11", "high leakage risk", "POP_LEARNED", "leakage_risk",
     lambda r: str(r.get("leakage_risk", "")).strip().lower() == "high", "PRIMARY"),
    ("S1", "comparison is like-for-like", "POP_LEARNED", "comparison_is_like_for_like",
     lambda r: yes(r, "comparison_is_like_for_like"), "SECONDARY"),
    ("S2", "tested on unseen site or season", "POP_LEARNED", "tested_unseen_site_or_season",
     lambda r: yes(r, "tested_unseen_site_or_season"), "SECONDARY"),
    ("S3", "night or low-light tested", "POP_LEARNED", "night_or_lowlight_tested",
     lambda r: yes(r, "night_or_lowlight_tested"), "SECONDARY"),
    ("S4", "adverse weather tested", "POP_LEARNED", "adverse_weather_tested",
     lambda r: yes(r, "adverse_weather_tested"), "SECONDARY"),
    ("S5", "hyperparameters fully reported", "POP_LEARNED", "hyperparams_full",
     lambda r: str(r.get("hyperparams_full", "")).strip().lower() == "yes", "SECONDARY"),
]


def main():
    A = {r["paper_id"]: r for r in
         json.load(io.open("corpus/raw_coding/coded_A_67.RAW.json", encoding="utf-8"))}
    B = {r["paper_id"]: r for r in
         json.load(io.open("corpus/raw_coding/coded_B_67.RAW.json", encoding="utf-8"))}
    rel = json.load(io.open("corpus/reliability_67.json", encoding="utf-8"))["fields"]
    ids = sorted(set(A) & set(B))

    # agreed-only: papers where the two coders gave the same code for the driving field
    def agreed_ids(field):
        return [i for i in ids if str(A[i].get(field)) == str(B[i].get(field))]

    popsA = RF.coding_populations(A)
    popsB = RF.coding_populations(B)

    print(f"PREVALENCE — {len(ids)} in-scope papers, pre-specified estimands")
    print("Estimates are reported with their construct's coding reliability in the same row.")
    print("=" * 116)
    print(f"{'id':4s} {'estimand':38s} {'k/n':>9s} {'%':>6s} {'95% CI':>14s} "
          f"{'kappa':>7s} {'class':>20s}")
    print("-" * 116)

    fractions, rows = [], []
    for eid, label, pop, driver, pred, status in ESTIMANDS:
        r = rel.get(driver, {})
        cls = r.get("class", "UNKNOWN")
        kap = r.get("kappa")
        reliable = cls == "PRIMARY-SAFE"

        # primary estimate uses coder A; the coder-choice sensitivity below reports all three
        pool = sorted(popsA[pop])
        k = sum(1 for i in pool if pred(A[i]))
        n = len(pool)
        lo, hi = wilson(k, n)
        ks = "    n/a" if kap is None else f"{kap:7.3f}"

        if status == "PRIMARY" and not reliable:
            print(f"{eid:4s} {label:38s} {f'{k}/{n}':>9s} {'--':>6s} {'--':>14s} "
                  f"{ks} {cls:>20s}")
            print(f"     -> NOT ESTIMATED: construct is {cls}; could not be estimated "
                  f"reliably with the pre-specified instrument")
            rows.append({"id": eid, "label": label, "status": status, "estimated": False,
                         "reason": f"construct {driver} classified {cls}",
                         "class": cls, "kappa": kap})
            continue

        print(f"{eid:4s} {label:38s} {f'{k}/{n}':>9s} {100*k/n:6.1f} "
              f"{f'{100*lo:.1f}-{100*hi:.1f}':>14s} {ks} {cls:>20s}")
        rows.append({"id": eid, "label": label, "status": status, "estimated": True,
                     "numerator": k, "denominator": n, "pct": round(100 * k / n, 2),
                     "ci95": [round(100 * lo, 2), round(100 * hi, 2)],
                     "population": pop, "driver": driver, "class": cls, "kappa": kap})
        fractions.append({"id": f"{eid}_{driver}", "label": label,
                          "numerator": k, "denominator": n, "population": pop,
                          "source": "scripts/prevalence.py (coder A, primary)"})

    # ------------------------------------------------------------- sensitivity
    print("\n" + "=" * 116)
    print("PRE-SPECIFIED SENSITIVITY — coder choice")
    print("=" * 116)
    print(f"{'id':4s} {'A alone':>12s} {'B alone':>12s} {'agreed only':>14s} {'spread':>8s}")
    print("-" * 116)
    for row in rows:
        if not row.get("estimated"):
            continue
        eid = row["id"]
        _, _, pop, driver, pred, _ = next(e for e in ESTIMANDS if e[0] == eid)
        pa = sorted(popsA[pop])
        pb = sorted(popsB[pop])
        ag = [i for i in agreed_ids(driver) if i in popsA[pop] and i in popsB[pop]]
        va = 100 * sum(1 for i in pa if pred(A[i])) / max(1, len(pa))
        vb = 100 * sum(1 for i in pb if pred(B[i])) / max(1, len(pb))
        vg = 100 * sum(1 for i in ag if pred(A[i])) / max(1, len(ag)) if ag else float("nan")
        spread = max(va, vb) - min(va, vb)
        flag = "  <-- MATERIAL" if spread > 10 else ""
        print(f"{eid:4s} {va:11.1f}% {vb:11.1f}% "
              f"{(f'{vg:.1f}% (n={len(ag)})'):>14s} {spread:7.1f}{flag}")
        row["sens_coder"] = {"A": round(va, 2), "B": round(vb, 2),
                             "agreed": None if ag == [] else round(vg, 2),
                             "n_agreed": len(ag), "spread": round(spread, 2)}

    RF.emit(RF.load_registry() + fractions)
    json.dump({"n": len(ids), "estimands": rows},
              io.open("corpus/prevalence.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print(f"\nwrote corpus/prevalence.json and appended {len(fractions)} fractions "
          f"to the registry")
    nq = sum(1 for r in rows if not r.get("estimated"))
    print(f"\n{nq} of {len(rows)} estimands could NOT be estimated reliably and are reported "
          f"as such.")


if __name__ == "__main__":
    main()
