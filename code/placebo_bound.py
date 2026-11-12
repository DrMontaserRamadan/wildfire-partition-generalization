"""Bound the contribution of the duplicated images, without claiming equivalence from a null test.

The draft previously said that removing the duplicated training images was "indistinguishable"
from removing a size-matched random subset, citing t = -0.014, p = 0.989. That is an equivalence
claim resting on a non-significant test, which is exactly the inference this paper argues against
elsewhere. A large p value means the data do not separate the arms; it does not mean the arms are
the same.

Two honest options exist. One is a TOST at a pre-specified margin. No such margin was fixed in
advance, so adopting one now would be a post-hoc choice of the kind this paper criticises, and the
margin that happens to clear 0.05 would be selected by the result. The other is to report the
confidence interval on the difference and let it carry the bound directly. We take the second.

The interval is reported for both contrasts. The TOST values are printed for completeness and are
labelled post-hoc wherever they appear; they are not the basis of any claim in the manuscript.
"""
import io
import json
import os
import statistics as st
import sys
from math import sqrt

from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def welch(a, b):
    ma, mb = st.mean(a), st.mean(b)
    va, vb = st.variance(a), st.variance(b)
    na, nb = len(a), len(b)
    se = sqrt(va / na + vb / nb)
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    return ma - mb, se, (ma - mb) / se, df


def main():
    runs = json.load(io.open("corpus/confound_control_results.json", encoding="utf-8"))
    arms = {}
    for r in runs:
        arms.setdefault(r["mode"], []).append(r["gap"])

    assert sorted(arms) == ["full", "no_twins", "random"], sorted(arms)
    assert all(len(v) == 10 for v in arms.values()), "expected 10 seeds per arm"

    print("PLACEBO BOUND - contribution of the duplicated images to the recall gap")
    print("=" * 82)
    for k in ("full", "no_twins", "random"):
        v = arms[k]
        print(f"  {k:9s} n={len(v)}  mean gap {100*st.mean(v):5.2f} pp   sd {100*st.stdev(v):4.2f}")

    out = {"arms": {k: {"n": len(v), "mean_gap_pp": round(100 * st.mean(v), 3),
                        "sd_pp": round(100 * st.stdev(v), 3)} for k, v in arms.items()},
           "contrasts": {}}

    print()
    for lab, a, b in (("no_twins_vs_random", "no_twins", "random"),
                      ("no_twins_vs_full", "no_twins", "full")):
        d, se, t, df = welch(arms[a], arms[b])
        p = 2 * stats.t.sf(abs(t), df)
        crit = stats.t.ppf(0.975, df)
        lo, hi = 100 * (d - crit * se), 100 * (d + crit * se)
        print(f"  {lab}")
        print(f"     difference {100*d:+.2f} pp   t {t:+.4f}   df {df:.1f}   p {p:.4f}")
        print(f"     95% CI [{lo:+.2f}, {hi:+.2f}] pp   <- this is the claim")
        # post-hoc only, printed so the record is complete; not used in the manuscript
        tost = {f"{int(100*m)}pp": round(max(stats.t.sf((d + m) / se, df),
                                             stats.t.cdf((d - m) / se, df)), 4)
                for m in (0.02, 0.05, 0.10)}
        print(f"     post-hoc TOST (not claimed): {tost}")
        out["contrasts"][lab] = {"diff_pp": round(100 * d, 3), "t": round(t, 4),
                                 "df": round(df, 1), "p": round(p, 4),
                                 "ci95_pp": [round(lo, 2), round(hi, 2)],
                                 "tost_posthoc_not_claimed": tost}

    gap = st.mean(arms["full"])
    widest = max(abs(x) for x in out["contrasts"]["no_twins_vs_random"]["ci95_pp"])
    print()
    print(f"  mean gap with the full training pool: {100*gap:.1f} pp")
    print(f"  widest bound on the twins' contribution: {widest:.1f} pp "
          f"= {100*widest/(100*gap):.1f}% of the gap")
    out["gap_pp"] = round(100 * gap, 2)
    out["bound_pp"] = round(widest, 2)
    out["bound_share_of_gap_pct"] = round(100 * widest / (100 * gap), 1)
    out["claim"] = ("The interval bounds the duplicated images' contribution at about three "
                    "percentage points of a thirty-three-point gap. No equivalence is asserted "
                    "from a non-significant test.")

    json.dump(out, io.open("corpus/placebo_bound.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nwrote corpus/placebo_bound.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
