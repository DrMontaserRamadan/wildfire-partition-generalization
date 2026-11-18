"""Sensitivity of the FLAME protocol comparison (ESWA panel, 2026-11-18). POST HOC.

Base comparison, as in the manuscript: the 31 FLAME-record papers that report a headline
accuracy, 18 on the designated test set (OFFICIAL) against 13 that substituted a partition of
their own (every other protocol code). Reported here for the base set and for four removals:
  - the authors' own paper (Ramadan 2024);
  - papers whose evidence is not a full text read for this record (abstract only, secondary
    sources only, or a prior pass not re-read);
  - papers whose headline is not a held-out test figure (validation, training, cross-validation);
  - all three removals together.
For each: medians, the count of paper pairs in which the substituting paper reports more, the
probability of superiority (= pairs / all pairs, ties counted half), the exact Mann-Whitney p, and
the Hodges-Lehmann shift with its distribution-free confidence interval.
"""
import io
import json
import os

import numpy as np
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = "corpus/eswa_flame_sensitivity_2026-11-18.json"


def hl_ci(x, y, alpha=0.05):
    d = np.sort(np.subtract.outer(np.asarray(y), np.asarray(x)).ravel())
    m, n = len(x), len(y)
    # Moses / Lehmann interval from the Mann-Whitney null distribution (normal approximation)
    z = stats.norm.ppf(1 - alpha / 2)
    k = int(np.floor(m * n / 2 - z * np.sqrt(m * n * (m + n + 1) / 12)))
    k = max(k, 0)
    return float(np.median(d)), float(d[k]), float(d[len(d) - k - 1])


def compare(rows):
    off = [r["headline_accuracy"] for r in rows if r["protocol"] == "OFFICIAL"]
    sub = [r["headline_accuracy"] for r in rows if r["protocol"] != "OFFICIAL"]
    pairs = len(off) * len(sub)
    wins = sum((s > o) + 0.5 * (s == o) for s in sub for o in off)
    u = stats.mannwhitneyu(sub, off, alternative="two-sided", method="exact" if pairs <= 400 else "auto")
    hl, lo, hi = hl_ci(off, sub)
    return {"n_official": len(off), "n_substituted": len(sub),
            "median_official": float(np.median(off)), "median_substituted": float(np.median(sub)),
            "pairs": pairs, "pairs_substituted_higher": wins,
            "prob_superiority": wins / pairs, "mann_whitney_p": float(u.pvalue),
            "hodges_lehmann_shift": hl, "hl_ci95": [lo, hi]}


def main():
    rows = [r for r in json.load(io.open("corpus/flame_timeline.json", encoding="utf-8"))
            if r.get("headline_accuracy") is not None]
    assert len(rows) == 31, len(rows)

    def own(r):
        return "10.1016/j.iot.2024.101248" in str(r.get("doi"))

    def weak_evidence(r):
        e, v = str(r.get("evidence_source")).lower(), str(r.get("verification")).lower()
        return ("abstract" in e and "full text" not in e) or "not retrieved" in e or \
               "not re-verified" in v or "partially verified" in v or "not independently" in v

    def not_test(r):
        k = str(r.get("accuracy_kind")).lower()
        return any(w in k for w in ("validation", "training accuracy", "cross-validation"))

    sets = {"base": rows,
            "minus_own_paper": [r for r in rows if not own(r)],
            "minus_weak_evidence": [r for r in rows if not weak_evidence(r)],
            "minus_non_test_headline": [r for r in rows if not not_test(r)],
            "minus_all_three": [r for r in rows if not (own(r) or weak_evidence(r) or not_test(r))]}
    out = {"_note": __doc__,
           "removed": {k: [f"{r['first_author']} {r['year']}" for r in rows if r not in v] for k, v in sets.items()}}
    for k, v in sets.items():
        out[k] = compare(v)
        c = out[k]
        print(f"{k:25s} n={c['n_official']}/{c['n_substituted']} med {c['median_official']:.2f} vs "
              f"{c['median_substituted']:.2f}  {c['pairs_substituted_higher']:.1f}/{c['pairs']} "
              f"PS={c['prob_superiority']:.3f} p={c['mann_whitney_p']:.2g} HL={c['hodges_lehmann_shift']:.2f} "
              f"[{c['hl_ci95'][0]:.2f},{c['hl_ci95'][1]:.2f}]")
    for k, v in out["removed"].items():
        if v:
            print("  removed in", k, ":", v)
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
