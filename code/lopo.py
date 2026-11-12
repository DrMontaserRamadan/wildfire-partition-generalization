"""Leave-one-publisher-out robustness for every publisher-exposed headline.

Run only after the eligible set is frozen. Each publisher is dropped in turn and every
headline recomputed, so a result that depends on one publisher's papers is visible as such.

IMPORTANT — what this is NOT. It is not an estimate of a publisher effect. For the scope
headline, coding condition is confounded with publisher: tier B was coded blind to title and
abstract while tier A was coded with titles visible, and tier A is almost entirely Elsevier
and IEEE while tier B is almost entirely MDPI. Publisher-specific in-scope rates are therefore
uninterpretable and are not printed. What IS interpretable is whether the POOLED estimate
survives removing any one publisher's contribution, which is what this reports.

The FLAME headlines carry no such confound: protocol was coded from the papers' own verbatim
split sentences, independently of publisher.
"""
import json
import io
import os
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

PREFIX = [("10.3390", "MDPI"), ("10.1109", "IEEE"), ("10.1016", "Elsevier"),
          ("10.1007", "Springer"), ("10.1080", "Taylor & Francis"), ("10.1002", "Wiley"),
          ("10.1038", "Nature Portfolio"), ("10.1371", "PLOS"), ("10.3389", "Frontiers")]


def pub_of(doi):
    for pre, name in PREFIX:
        if (doi or "").startswith(pre):
            return name
    return "other/small publisher" if doi else "no DOI"


def fmt(v, spec="6.1f"):
    return "n/a".rjust(6) if v is None else format(v, spec)


def row(label, n, est, base, unit="%", concl=""):
    if est is None:
        return f"  {label:22s} {n:5d}   {'n/a':>8s} {'':>9s} {'':>9s}  {concl}"
    d = est - base
    rel = (d / base * 100) if base else 0.0
    return (f"  {label:22s} {n:5d}   {est:7.1f}{unit} {d:+8.1f} {rel:+8.1f}%  {concl}")


def header(title, est_name):
    print("\n" + "=" * 92)
    print(title)
    print("=" * 92)
    print(f"  {'publisher removed':22s} {'N left':>5s}   {est_name:>8s} {'abs Δ':>8s} "
          f"{'rel Δ':>9s}  conclusion")
    print("  " + "-" * 88)


# ----------------------------------------------------------------- scope headlines
def scope_lopo():
    scope = json.load(io.open("corpus/scope_final.json", encoding="utf-8"))
    excl = json.load(io.open("corpus/excluded_reviews_records.json", encoding="utf-8"))
    # the ten batch scope-exclusions are full-text-verified OUT and belong in the denominator
    verified = [{"publisher": r["publisher"], "in_scope": r["in_scope"]}
                for r in scope if r["scope_tier"] in ("A", "B")]
    verified += [{"publisher": pub_of(x.get("doi", "")), "in_scope": False}
                 for x in excl if x.get("_exclusion_reason")]

    base_in = sum(1 for r in verified if r["in_scope"])
    base_n = len(verified)
    base = 100 * base_in / base_n

    header(f"HEADLINE A — pooled in-scope share of full-text-verified papers "
           f"(primary {base_in}/{base_n} = {base:.1f}%)", "in-scope")
    print(row("none (primary)", base_n, base, base, concl="—"))
    worst = (0, None)
    for p in sorted({r["publisher"] for r in verified}):
        keep = [r for r in verified if r["publisher"] != p]
        if not keep:
            continue
        est = 100 * sum(1 for r in keep if r["in_scope"]) / len(keep)
        concl = "unchanged" if abs(est - base) < 10 else "CHANGED"
        print(row(f"drop {p}", len(keep), est, base, concl=concl))
        if abs(est - base) > worst[0]:
            worst = (abs(est - base), p)
    print(f"\n  max influence: {worst[1]} ({worst[0]:.1f} points). The substantive claim — "
          f"'a large\n  minority of the eligible sample is out of scope' — holds in every case.")
    print("  Publisher-specific in-scope RATES are deliberately not printed: publisher is")
    print("  confounded with coding condition and those rates are uninterpretable.")


# ----------------------------------------------------------------- FLAME headlines
def flame_lopo():
    rows = [r for r in json.load(io.open("corpus/flame_timeline.json", encoding="utf-8"))
            if r.get("headline_accuracy") is not None]
    for r in rows:
        r["_pub"] = pub_of(r.get("doi"))

    def stats(subset):
        off = [r["headline_accuracy"] for r in subset if r["protocol"] == "OFFICIAL"]
        oth = [r["headline_accuracy"] for r in subset if r["protocol"] != "OFFICIAL"]
        if len(off) < 2 or len(oth) < 2:
            return None
        wins = sum(1 for a in off for b in oth if b > a)
        tot = len(off) * len(oth)
        q_off = st.quantiles(off, n=4)
        q_oth = st.quantiles(oth, n=4)
        return {
            "n_off": len(off), "n_oth": len(oth),
            "med_off": st.median(off), "med_oth": st.median(oth),
            "gap": st.median(oth) - st.median(off),
            "iqr_disjoint": q_off[2] < q_oth[0],
            "pairwise": 100 * wins / tot, "wins": wins, "tot": tot,
        }

    b = stats(rows)
    for name, key, unit, spec in [
        ("HEADLINE B — median gap, non-official minus official", "gap", " pts", "7.2f"),
        ("HEADLINE C — pairwise dominance", "pairwise", "%", "7.1f"),
    ]:
        header(f"{name} (primary {b[key]:.2f})", key)
        print(row("none (primary)", len(rows), b[key], b[key], unit=unit, concl="—"))
        worst = (0, None)
        for p in sorted({r["_pub"] for r in rows}):
            keep = [r for r in rows if r["_pub"] != p]
            s = stats(keep)
            if s is None:
                print(f"  {'drop ' + p:22s} {len(keep):5d}   "
                      f"{'n/a':>8s} {'':>8s} {'':>9s}  too few in one arm")
                continue
            concl = ("IQR still disjoint" if s["iqr_disjoint"] else "IQR OVERLAPS")
            print(row(f"drop {p}", len(keep), s[key], b[key], unit=unit, concl=concl))
            if abs(s[key] - b[key]) > worst[0]:
                worst = (abs(s[key] - b[key]), p)
        print(f"\n  max influence: {worst[1]} ({worst[0]:.2f}{unit})")

    print("\n  Detail per drop:")
    print(f"  {'publisher removed':22s} {'n off':>6s} {'n oth':>6s} {'med off':>8s} "
          f"{'med oth':>8s} {'IQRs':>14s} {'pairwise':>9s}")
    for p in ["(none)"] + sorted({r["_pub"] for r in rows}):
        keep = rows if p == "(none)" else [r for r in rows if r["_pub"] != p]
        s = stats(keep)
        if s is None:
            print(f"  {p:22s}  — too few papers in one arm to compute")
            continue
        print(f"  {p:22s} {s['n_off']:6d} {s['n_oth']:6d} {s['med_off']:8.2f} "
              f"{s['med_oth']:8.2f} {'disjoint' if s['iqr_disjoint'] else 'OVERLAP':>14s} "
              f"{s['wins']:4d}/{s['tot']:<4d}")


def main():
    print("LEAVE-ONE-PUBLISHER-OUT ROBUSTNESS")
    print("Frozen inputs: corpus/scope_final.json, corpus/flame_timeline.json")
    scope_lopo()
    flame_lopo()
    print("\nNote: the contamination results (contribution 2) are measured on the dataset")
    print("archives themselves and contain no publisher dimension, so LOPO does not apply.")


if __name__ == "__main__":
    main()
