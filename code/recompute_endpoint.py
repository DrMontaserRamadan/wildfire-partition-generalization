"""Recompute the primary endpoint over the enlarged learned-model population.

The endpoint is the share of learned-model papers whose full text gives no reconstructable
allocation mechanism: categories 2 and 3 over the whole population, with category 4 kept in the
denominator and out of the numerator, exactly as the frozen validation defined it.

Two populations are reported separately and then together, because they are not interchangeable:
the 64 papers already validated, and the papers added after hand retrieval recovered full texts
that automated retrieval could not reach. The added papers have NO frozen model code, so the
frozen 38/64 figure cannot be extended and is reported only on its original population.
"""
import io
import json
import os
from math import sqrt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

Z = 1.959963984540054


def wilson(k, n):
    """Wilson score interval, the same one the frozen analysis uses."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def block(name, cats):
    n = len(cats)
    dist = {c: sum(1 for x in cats if x == c) for c in (1, 2, 3, 4)}
    k = dist[2] + dist[3]
    lo, hi = wilson(k, n)
    k2, n2 = k, n - dist[4]
    lo2, hi2 = wilson(k2, n2)
    print(f"\n{name}")
    print(f"  categories: mechanism {dist[1]} | ratio/counts only {dist[2]} | "
          f"no statement {dist[3]} | unresolved {dist[4]}")
    print(f"  lacking a reconstructable mechanism: {k} of {n} = {100*k/n:.1f}% "
          f"[{100*lo:.1f}-{100*hi:.1f}]")
    print(f"  excluding unresolved from the denominator: {k2} of {n2} = {100*k2/n2:.1f}% "
          f"[{100*lo2:.1f}-{100*hi2:.1f}]")
    # Store full precision. Rounding here and formatting to one decimal later rounds twice, and
    # 54/79 = 68.354% came out of that pipeline as 68.3 instead of 68.4.
    return dict(n=n, k=k, pct=100 * k / n, ci=[100 * lo, 100 * hi],
                distribution=dist,
                excl_unresolved=dict(k=k2, n=n2, pct=100 * k2 / n2,
                                     ci=[100 * lo2, 100 * hi2]))


def main():
    old = json.load(io.open("corpus/fulltext_validation.json", encoding="utf-8"))
    old_cats = [d["category"] for d in old["per_paper"].values()]
    new = json.load(io.open("corpus/validation_incoming_codes.json", encoding="utf-8"))
    new_cats = [d["category"] for d in new["per_paper"].values()]
    # Papers recovered in the second sweep: previously excluded on their abstracts, found to be
    # in scope once read at full text. Same hand-retrieval route, so they belong with the others.
    exc = json.load(io.open("corpus/validation_exclcheck_codes.json", encoding="utf-8"))
    new_cats += [d["category"] for d in exc["per_paper"].values()]

    assert len(old_cats) == 64, len(old_cats)

    a = block("ALREADY VALIDATED (unchanged, reported as the original record)", old_cats)
    b = block("HAND RETRIEVED (papers automated retrieval could not reach, plus two recovered from the abstract-only exclusions)", new_cats)
    c = block("COMBINED (the recomputed primary endpoint)", old_cats + new_cats)

    # do the two populations differ? two-proportion z test, reported not interpreted
    p1, n1 = a["k"] / a["n"], a["n"]
    p2, n2 = b["k"] / b["n"], b["n"]
    pool = (a["k"] + b["k"]) / (n1 + n2)
    se = sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / se if se else float("nan")
    print(f"\ndifference between the two populations: {100*(p2-p1):+.1f} points, z = {z:.2f}")
    print("  the newly retrieved papers are the ones automated retrieval failed on, so this is a")
    print("  measurement about retrievability, not a second sample from the same frame.")

    print(f"\nfrozen model coding stays on its own population: {old['frozen_E1']} of 64 = "
          f"{old['frozen_pct']:.1f}%. The added papers carry no frozen code, so that figure "
          f"cannot be extended.")

    out = dict(validated_original=a, newly_retrieved=b, combined=c,
               z_two_proportion=round(z, 3),
               frozen_model_coding=dict(k=old["frozen_E1"], n=64, pct=old["frozen_pct"],
                                        note="not extended: the added papers have no frozen code"))
    json.dump(out, io.open("corpus/endpoint_recomputed.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
