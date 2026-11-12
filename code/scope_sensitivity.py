"""Sensitivity of every scope-dependent headline to the nine contested cases.

The contested cases are kept at their original independent classification. This script does
not re-decide them; it reports how far each headline moves if all of them were decided the
other way. A conclusion that survives both bounds is robust. A conclusion that does not is
reported as dependent on those calls, not resolved by picking the favourable one.

Two separate uncertainty sources are reported, because they are different things:
  - CONTESTED (9): judgment calls the coder recorded as arguable at the time of coding.
  - UNCLEAR (6): abstracts that never state a setting. All four of these that could be
    checked against full text turned out to be OUT, so the lower bound is the likely truth.

Denominators are printed with every percentage. There is no bare percentage in the output.
"""
import json
import io
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# Why each case is contested. Typed, because the TYPE is the finding: these are not nine
# one-off judgment calls, they are seven recurring ambiguities in the scope construct itself.
CONTEST_TYPE = {
    "W4312250248": ("benchmark-with-baselines vs method paper",
                    "S3: a dataset paper that also reports detection baselines. If a benchmark "
                    "release counts as a primary method study, IN; if not, OUT."),
    "W4399361386": ("benchmark-with-baselines vs method paper",
                    "S3: same ambiguity as FLAME2, coded the same way for consistency."),
    "W3119132889": ("wildland framing, non-wildland use stated",
                    "S1: motivated by wildfires, but the stated deployment is a camera embedded "
                    "in a vehicle; the abstract never establishes wildland imagery."),
    "W4394697163": ("wildland framing, general-fire evaluation data",
                    "S1: titled and framed as wildfire detection, evaluated on the Foggia "
                    "dataset, which is general fire video rather than wildland-specific."),
    "W3176110204": ("active detection vs burned-area mapping",
                    "S2: titled 'Wildfire Detection', but the workflow is repeatedly described "
                    "as detection of fire-AFFECTED AREAS, with burned-area framing throughout."),
    "W3180371431": ("measures detection but proposes no method",
                    "S2: wildland fire, and detection latency is the measured quantity, but the "
                    "paper corroborates an existing detector rather than contributing one."),
    "W3204651913": ("system described, no evaluation reported",
                    "Evidence insufficiency: a forest fire detection system is described and "
                    "no evaluation of it is reported anywhere in the abstract."),
    "W4396670524": ("document type unresolvable from the abstract",
                    "S3: titled 'An Analysis of' and reads like a survey, but describes a built "
                    "device. Only the full text could settle it, and we do not have it."),
    "W7198168751": ("DATA DEFECT: no abstract exists",
                    "The abstract field holds a bibliographic citation string, not an abstract. "
                    "The decision rests on the title alone, which is the very failure mode this "
                    "paper documents in others."),
}


def main():
    scope = json.load(io.open("corpus/scope_final.json", encoding="utf-8"))
    cal = json.load(io.open("corpus/scope_calibration.json", encoding="utf-8"))
    by_id = {r["paper_id"]: r for r in scope}

    contested = [r for r in scope if r.get("contested")]
    unclear = [r for r in scope if r["scope_code"] == "UNCLEAR"]
    assert len(contested) == 9, f"expected 9 contested, found {len(contested)}"

    print("=" * 78)
    print("WHY EACH CASE IS CONTESTED")
    print("=" * 78)
    for t, group in sorted(Counter(CONTEST_TYPE[r["paper_id"]][0] for r in contested).items(),
                           key=lambda kv: -kv[1]):
        print(f"\n[{group}x] {t}")
        for r in contested:
            if CONTEST_TYPE[r["paper_id"]][0] == t:
                print(f"   tier {r['scope_tier']}  currently "
                      f"{'IN ' if r['in_scope'] else 'OUT'}  {r['title'][:62]}")
                print(f"      {CONTEST_TYPE[r['paper_id']][1]}")

    print(f"\nOf the nine, {sum(1 for r in contested if r['in_scope'])} are currently IN and "
          f"{sum(1 for r in contested if not r['in_scope'])} OUT, so the bounds are asymmetric.")
    print(f"{sum(1 for r in contested if r['scope_tier'] == 'C')} of 9 are tier C "
          f"(abstract only) and therefore affect the SCREENED estimate, not the "
          f"full-text-verified denominator.")

    # ---- the decision rule, stated before the numbers ----
    print("\n" + "=" * 78)
    print("PRE-SPECIFIED PRIMARY DECISION RULE")
    print("=" * 78)
    print("A paper is in scope only if S1 (wildland), S2 (detection is the contribution) and")
    print("S3 (primary article) are all satisfied. A BORDERLINE suffix records that the coder")
    print("judged the call arguable; it does not change the verdict. UNCLEAR is never folded")
    print("into IN. This rule was fixed in notes/SCOPE_SCREEN_RUBRIC.md before any coding.")

    # The ten papers excluded on scope in the author-supplied batch were REMOVED from
    # UNIVERSE_FROZEN, so scope_final.json holds 159, not the 169 originally eligible. Those
    # ten had their full text read and were found out of scope: they are full-text-verified
    # out-of-scope papers and they belong in this denominator. Omitting them computes 67/101
    # and understates the out-of-scope rate by six points. This is the same denominator error
    # that put Elsevier and IEEE at 100% earlier in the session, in a different disguise.
    excluded = json.load(io.open("corpus/excluded_reviews_records.json", encoding="utf-8"))
    n_batch_scope_exclusions = sum(1 for x in excluded if x.get("_exclusion_reason"))

    def counts(flip_contested=None, flip_unclear=None):
        """Return (verified_in, verified_n, screened_in) over the PRE-EXCLUSION frame."""
        v_in, v_n, c_in = 0, n_batch_scope_exclusions, 0  # the ten enter as verified OUT
        for r in scope:
            inscope = r["in_scope"]
            if flip_contested is not None and r.get("contested"):
                inscope = flip_contested
            if flip_unclear is not None and r["scope_code"] == "UNCLEAR":
                inscope = flip_unclear
            if r["scope_tier"] in ("A", "B"):
                v_n += 1
                v_in += inscope
            else:
                c_in += inscope
        return v_in, v_n, c_in

    scenarios = [
        ("PRIMARY (rule as pre-specified)", None, None),
        ("all 9 contested -> OUT", False, None),
        ("all 9 contested -> IN", True, None),
        ("all 6 UNCLEAR -> IN", None, True),
        ("contested OUT and UNCLEAR OUT (hard lower)", False, False),
        ("contested IN and UNCLEAR IN (hard upper)", True, True),
    ]

    print("\n" + "=" * 78)
    print("HEADLINE 1 — in-scope share among FULL-TEXT-VERIFIED papers")
    print("=" * 78)
    print(f"{'scenario':44s} {'in/n':>10s} {'%':>7s} {'abs Δ':>7s} {'rel Δ':>8s}")
    base_v, base_n, _ = counts()
    base_pct = 100 * base_v / base_n
    rows = []
    for name, fc, fu in scenarios:
        v, n, _ = counts(fc, fu)
        pct = 100 * v / n
        rows.append((name, v, n, pct, pct - base_pct))
        print(f"{name:44s} {f'{v}/{n}':>10s} {pct:6.1f}% {pct - base_pct:+6.1f} "
              f"{(pct - base_pct) / base_pct * 100 if base_pct else 0:+7.1f}%")

    lo = min(r[3] for r in rows)
    hi = max(r[3] for r in rows)
    print(f"\n  BOUNDS: in-scope {lo:.1f}% to {hi:.1f}% of {base_n} verified papers")
    print(f"  i.e. OUT OF SCOPE {100 - hi:.1f}% to {100 - lo:.1f}%")
    print(f"  Substantive conclusion — 'a large minority of the eligible sample is out of "
          f"scope' — {'SURVIVES' if 100 - hi > 25 else 'DOES NOT SURVIVE'} both bounds.")

    print("\n" + "=" * 78)
    print("HEADLINE 2 — total in-scope estimate, BOTH denominators stated")
    print("=" * 78)
    print(f"  initially eligible candidate corpus (screened in) : "
          f"{159 + n_batch_scope_exclusions}")
    print(f"  frame after the batch scope exclusions            : 159")
    print(f"  the two differ by the {n_batch_scope_exclusions} papers removed on scope in the "
          f"author-supplied batch.")
    ppv_lo = cal["unclear_as_OUT"]["ppv"]
    ppv_hi = cal["unclear_as_IN"]["ppv"]
    print(f"tier C is abstract-only, so its contribution is discounted by the calibrated PPV")
    print(f"(PPV {ppv_lo:.3f} with UNCLEAR out, {ppv_hi:.3f} with UNCLEAR in).")
    print(f"\n{'scenario':44s} {'verified':>9s} {'screened':>9s} {'total':>13s}")
    tot_lo, tot_hi = None, None
    for name, fc, fu in scenarios:
        v, n, c = counts(fc, fu)
        ppv = ppv_hi if fu else ppv_lo
        t = v + c * ppv
        tot_lo = t if tot_lo is None else min(tot_lo, t)
        tot_hi = t if tot_hi is None else max(tot_hi, t)
        print(f"{name:44s} {v:9d} {c * ppv:9.1f} {t:9.1f}/169")
    N0 = 159 + n_batch_scope_exclusions
    print(f"\n  BOUNDS: {tot_lo:.0f} to {tot_hi:.0f} papers in scope")
    print(f"    of the {N0} initially eligible candidate corpus : "
          f"{100 * tot_lo / N0:.0f}% to {100 * tot_hi / N0:.0f}%   <- REPORT THIS")
    print(f"    of the 159 post-batch frame                   : "
          f"{100 * tot_lo / 159:.0f}% to {100 * tot_hi / 159:.0f}%")
    print("    The second silently credits us with the ten we had already caught.")

    print("\n" + "=" * 78)
    print("HEADLINE 3 — the coding corpus (papers with usable full text AND in scope)")
    print("=" * 78)
    for name, fc, fu in scenarios[:3]:
        v, n, _ = counts(fc, fu)
        print(f"{name:44s} {v:3d} papers available to code")
    print("\n  Only 2 of the 9 contested cases are tier A/B, so the coding corpus moves by")
    print("  at most one paper in either direction.")

    out = {
        "contested": {r["paper_id"]: {
            "title": r["title"], "tier": r["scope_tier"], "code": r["scope_code"],
            "in_scope_primary": r["in_scope"],
            "contest_type": CONTEST_TYPE[r["paper_id"]][0],
            "contest_reason": CONTEST_TYPE[r["paper_id"]][1]} for r in contested},
        "unclear_ids": [r["paper_id"] for r in unclear],
        "verified_bounds_pct": [lo, hi],
        "verified_primary": [base_v, base_n],
        "total_bounds_of_159": [tot_lo, tot_hi],
        "scenarios": [{"name": n, "in": v, "n": nn, "pct": p} for n, v, nn, p, _ in rows],
    }
    json.dump(out, io.open("corpus/scope_sensitivity.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nwrote corpus/scope_sensitivity.json")


if __name__ == "__main__":
    main()
