"""Acquisition-bias audit: how do retrieved and unretrieved candidates differ?

111 of 169 candidates were verified at full text. If retrieval is associated with year,
publisher or open-access status, the 67-paper corpus is not a random subset of the frame and
the estimate carries a selection component that must be stated rather than assumed away.
"""
import json
import io
import os
import csv
from collections import Counter
from math import sqrt

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
    return (100 * max(0.0, c - h), 100 * min(1.0, c + h))


def main():
    rows = list(csv.DictReader(io.open("corpus/retrieval_table.csv", encoding="utf-8")))
    excl = [x for x in json.load(io.open("corpus/excluded_reviews_records.json",
                                         encoding="utf-8")) if x.get("_exclusion_reason")]

    # Every prefix that appears in the frame gets its own row. An earlier version of this list
    # stopped at nine publishers and swept IET, CSIRO, BMC, Hindawi, Copernicus and IOP into
    # "other/small", which made the manuscript's hand-built table disagree with this one: the
    # draft named eight zero-retrieval publishers and its rows summed to 166, not 169. One table
    # governs now, and the totals are asserted below.
    PREFIX = [("10.3390", "MDPI"), ("10.1109", "IEEE"), ("10.1016", "Elsevier"),
              ("10.1007", "Springer"), ("10.1080", "Taylor & Francis"),
              ("10.1002", "Wiley"), ("10.1049", "IET (Wiley)"),
              ("10.1038", "Nature Portfolio"), ("10.1371", "PLOS"),
              ("10.3389", "Frontiers"), ("10.1071", "CSIRO"),
              ("10.1186", "BMC/SpringerOpen"), ("10.1155", "Hindawi (Wiley)"),
              ("10.5194", "Copernicus"), ("10.1088", "IOP")]

    def pub(doi):
        for p, n in PREFIX:
            if (doi or "").startswith(p):
                return n
        return "other/small" if doi else "no DOI"

    # the ten batch scope-exclusions were retrieved too; include them on the retrieved side
    cand = [{"year": int(r["year"]), "pub": r["publisher"], "oa": r["open_access"] == "True",
             "got": r["fulltext_obtained"] == "True"} for r in rows]
    cand += [{"year": int(x["year"]), "pub": pub(x.get("doi", "")),
              "oa": bool(x.get("oa")), "got": True} for x in excl]

    got = [c for c in cand if c["got"]]
    miss = [c for c in cand if not c["got"]]
    assert len(cand) == 169, f"candidate frame is {len(cand)}, expected 169"
    assert len(got) == 115, f"retrieved is {len(got)}, expected 115"
    print("ACQUISITION-BIAS AUDIT")
    print("=" * 78)
    print(f"  candidate corpus            {len(cand)}")
    print(f"  full text retrieved         {len(got)}")
    print(f"  not retrieved               {len(miss)}")

    print("\n  BY PUBLISHER")
    print(f"  {'publisher':22s} {'retrieved':>9s} {'candidates':>11s} {'rate':>7s}")
    pubs = sorted({c["pub"] for c in cand})
    at100, atzero = [], []
    for p in pubs:
        g = [c for c in cand if c["pub"] == p]
        k = sum(1 for c in g if c["got"])
        rate = 100 * k / len(g)
        print(f"  {p:22s} {k:9d} {len(g):11d} {rate:6.1f}%")
        (at100 if rate == 100 else atzero if rate == 0 else []).append((p, len(g)))
    assert sum(len([c for c in cand if c["pub"] == p]) for p in pubs) == len(cand), \
        "the publisher rows do not sum to the candidate frame"
    print(f"  {'TOTAL':22s} {len(got):9d} {len(cand):11d}")
    print(f"\n  at 100% retrieval: {len(at100)} publishers, "
          f"{sum(n for _, n in at100)} papers -> {', '.join(p for p, _ in at100)}")
    print(f"  at   0% retrieval: {len(atzero)} publishers, "
          f"{sum(n for _, n in atzero)} papers -> {', '.join(p for p, _ in atzero)}")

    print("\n  BY YEAR")
    print(f"  {'year':6s} {'retrieved':>9s} {'candidates':>11s} {'rate':>7s}")
    for y in sorted({c["year"] for c in cand}):
        g = [c for c in cand if c["year"] == y]
        k = sum(1 for c in g if c["got"])
        print(f"  {y:<6d} {k:9d} {len(g):11d} {100*k/len(g):6.1f}%")

    print("\n  BY OPEN-ACCESS STATUS")
    for lab, v in (("open access", True), ("not open access", False)):
        g = [c for c in cand if c["oa"] is v]
        k = sum(1 for c in g if c["got"])
        lo, hi = wilson(k, len(g))
        print(f"  {lab:18s} {k:3d}/{len(g):<3d} = {100*k/len(g):5.1f}%  95% CI {lo:.1f}-{hi:.1f}")

    print("\n  DIRECTION OF THE BIAS")
    big = [(p, 100 * sum(1 for c in cand if c['pub'] == p and c['got'])
            / max(1, sum(1 for c in cand if c['pub'] == p)),
            sum(1 for c in cand if c['pub'] == p)) for p in pubs]
    big = [b for b in big if b[2] >= 5]
    big.sort(key=lambda b: -b[1])
    print("  publishers with 5+ candidates, best to worst retrieval:")
    for p, r, n in big:
        print(f"    {p:22s} {r:5.1f}%  (n={n})")
    print("\n  Retrieval is strongly associated with publisher. The verified corpus")
    print("  over-represents publishers whose full text could be obtained and")
    print("  under-represents the rest. This is a selection mechanism, not noise.")

    json.dump({"candidates": len(cand), "retrieved": len(got), "not_retrieved": len(miss),
               "by_publisher": {p: {"retrieved": sum(1 for c in cand if c["pub"] == p
                                                     and c["got"]),
                                    "candidates": sum(1 for c in cand if c["pub"] == p)}
                                for p in pubs},
               "by_year": {str(y): {"retrieved": sum(1 for c in cand if c["year"] == y
                                                     and c["got"]),
                                    "candidates": sum(1 for c in cand if c["year"] == y)}
                           for y in sorted({c["year"] for c in cand})},
               "by_oa": {str(v): {"retrieved": sum(1 for c in cand if c["oa"] is v
                                                   and c["got"]),
                                  "candidates": sum(1 for c in cand if c["oa"] is v)}
                         for v in (True, False)}},
              io.open("corpus/acquisition_bias.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nwrote corpus/acquisition_bias.json")


if __name__ == "__main__":
    main()
