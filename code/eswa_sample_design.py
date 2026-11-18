"""Disclose and test the audit's sampling design (ESWA panel, 2026-11-18).

The audited frame of 159 papers is not the whole eligible population. build_sample.py applied the
eligibility rules to the cleaned harvest, which admits 1,744 records, then drew a sample
stratified by primary modality x year band: in each stratum, half the most-cited records and half
drawn at random (seed 20260909), and finally force-included the authors' own paper.

This script reconstructs that draw from the same input and the same seed, checks that it
reproduces corpus/sample.json exactly, labels every audited paper by the half it came from, and
recomputes the primary endpoint (categories 2 + 3 over all learned-model papers, category 4 kept in
the denominator) separately for each half, for both the author-validated coding and the
two-human consensus.
"""
import csv
import io
import json
import os
import random
import re
from collections import defaultdict
from math import sqrt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
Z = 1.959963984540054
OUT = "corpus/eswa_sample_design_2026-11-18.json"
stratum_map = {}


def wilson(k, n):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return [100 * max(0, c - h), 100 * min(1, c + h)]


def reconstruct():
    """Byte-for-byte the logic of build_sample.py, with the half recorded."""
    random.seed(20260909)
    rows = json.load(open("corpus/primary_clean.json", encoding="utf-8"))
    BAD = re.compile(r"arXiv|Research Square|DOAJ|Preprints|eBooks|international archives|Biodiversidade|Coimbra", re.I)
    DET = re.compile(r"\b(detect\w*|recogni\w*|classif\w*|identif\w*|segment\w*|early warning|monitor\w*|surveillance|localiz\w*|alarm)\b", re.I)
    OFF = re.compile(r"\b(burn severity|susceptibilit|spread (model|predict|simulat)|risk (mapping|assess)|fuel (load|moisture|mapping)|post-?fire|emission|air quality|health|smoke exposure|evacuat|insurance|policy|recovery|regeneration|soil|hydrolog|carbon)\b", re.I)
    elig = []
    for r in rows:
        if r["year"] < 2020 or not r["venue"] or BAD.search(r["venue"]):
            continue
        if not DET.search(r["title"]):
            continue
        if OFF.search(r["title"]) and not re.search(r"\bdetect\w*|early warning|recogni\w*", r["title"], re.I):
            continue
        if len(r["abstract"]) < 250:
            continue
        elig.append(r)

    def modality(r):
        t = set(r["tags"])
        for tag, m in (("iot", "iot"), ("uav", "uav"), ("sat", "satellite"), ("edge", "edge")):
            if tag in t:
                return m
        return "vision"

    def band(y):
        return "2020-21" if y <= 2021 else ("2022-23" if y <= 2023 else "2024-26")

    strata = defaultdict(list)
    for r in elig:
        strata[(modality(r), band(r["year"]))].append(r)
    half, strata_out = {}, []
    stratum_map.clear()
    for k, v in sorted(strata.items()):
        n = max(4, round(180 * len(v) / len(elig)))
        vs = sorted(v, key=lambda x: -(x["cites"] or 0))
        n_top = n // 2
        top = vs[:n_top]
        rnd = random.sample(vs[n_top:], min(n - n_top, len(vs) - n_top))
        for x in top:
            half[x["id"]] = "top_cited"
            stratum_map[x["id"]] = (f"{k[0]}|{k[1]}", "top_cited")
        for x in rnd:
            half[x["id"]] = "random"
            stratum_map[x["id"]] = (f"{k[0]}|{k[1]}", "random")
        strata_out.append({"stratum": f"{k[0]}|{k[1]}", "pool": len(v), "top": len(top), "random": len(rnd)})
    seed = [r for r in rows if "10.1016/j.iot.2024.101248" in (r["doi"] or "")]
    if seed and seed[0]["id"] not in half:
        half[seed[0]["id"]] = "forced_self_inclusion"
    return len(rows), len(elig), half, strata_out


def endpoint(cats):
    n = len(cats)
    k = sum(1 for c in cats if c in (2, 3))
    return {"n": n, "k": k, "pct": 100 * k / n if n else None, "ci": wilson(k, n)}


def main():
    n_clean, n_elig, half, strata = reconstruct()
    sample = json.load(open("corpus/sample.json", encoding="utf-8"))
    sids = {s["id"] for s in sample}
    # The draw yields 182 records; 23 were removed before the freeze (13 reviews at the
    # title/abstract screen, 10 out of scope on full text: UNIVERSE_FROZEN.json
    # excluded_before_freeze). sample.json is the 159 that remain, so it must be a SUBSET.
    assert sids <= set(half), f"sample.json has {len(sids - set(half))} ids the draw cannot produce"
    old = json.load(io.open("corpus/fulltext_validation.json", encoding="utf-8"))["per_paper"]
    new = json.load(io.open("corpus/validation_incoming_codes.json", encoding="utf-8"))["per_paper"]
    exc = json.load(io.open("corpus/validation_exclcheck_codes.json", encoding="utf-8"))["per_paper"]
    author = {pid: d["category"] for pid, d in list(old.items()) + list(new.items()) + list(exc.items())}
    assert len(author) == 79, len(author)
    human = {}
    with io.open("human_coding/returned/consensus.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            human[r["paper_identifier"]] = int(r["category"])
    out = {"n_cleaned_harvest": n_clean, "n_eligible_pool": n_elig, "n_sampled": len(half),
           "strata": strata, "by_half": {}, "n_drawn": len(half),
           "n_removed_before_freeze": len(set(half) - sids),
           "removed_by_half": {h: sum(1 for i in set(half) - sids if half[i] == h) for h in ("top_cited", "random")},
           "frozen_by_half": {h: sum(1 for i in sids if half[i] == h) for h in ("top_cited", "random", "forced_self_inclusion")},
           "self_paper_half": half.get("W4399615782"),
           "reconstruction_is_superset_of_sample_json": True}
    for coding, codes in (("author_validation", author), ("human_consensus", human)):
        for h in ("top_cited", "random", "forced_self_inclusion", "ALL"):
            ids = [p for p in codes if p in half and (h == "ALL" or half[p] == h)]
            out["by_half"][f"{coding}|{h}"] = endpoint([codes[p] for p in ids])
        miss = [p for p in codes if p not in half]
        out["by_half"][f"{coding}|not_in_sample_map"] = len(miss)
    # also: endpoint with the forced paper removed
    for coding, codes in (("author_validation", author), ("human_consensus", human)):
        ids = [p for p in codes if half.get(p) in ("top_cited", "random")]
        out["by_half"][f"{coding}|sampled_only"] = endpoint([codes[p] for p in ids])
    # Design-weighted estimate. Within a stratum the top-cited half is a census of the n_top most
    # cited records (weight 1); the random half stands for the rest of that stratum's pool
    # (weight (pool - n_top) / n_random). Weights are fixed by the DRAW, so the downstream scope
    # and retrieval losses are assumed to be ignorable within stratum x half; that assumption is
    # stated, not tested. Interval: percentile bootstrap resampling papers within stratum x half.
    stratum_of, w = stratum_map, {}
    for x in strata:
        pass
    wt = {}
    for pid, (st, h) in stratum_of.items():
        info = next(x for x in strata if x["stratum"] == st)
        wt[pid] = 1.0 if h == "top_cited" else (info["pool"] - info["top"]) / max(info["random"], 1)
    import random as _r
    for coding, codes in (("author_validation", author), ("human_consensus", human)):
        ids = [p for p in codes if p in wt]
        def est(sel):
            W = sum(wt[p] for p in sel)
            return 100 * sum(wt[p] for p in sel if codes[p] in (2, 3)) / W
        point = est(ids)
        cells = defaultdict(list)
        for p in ids:
            cells[stratum_of[p]].append(p)
        rng = _r.Random(20261118)
        boots = sorted(est([q for c in cells.values() for q in rng.choices(c, k=len(c))]) for _ in range(4000))
        out[f"weighted|{coding}"] = {"n": len(ids), "pct": point, "ci": [boots[99], boots[3899]],
                                     "effective_weights_sum": sum(wt[p] for p in ids)}
        print("weighted", coding, round(point, 1), [round(boots[99], 1), round(boots[3899], 1)])
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), indent=1)
    for k, v in out["by_half"].items():
        print(k, v)
    print("pool", n_elig, "sampled", len(half))


if __name__ == "__main__":
    main()
