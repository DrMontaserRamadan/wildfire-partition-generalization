"""Compute the section 7 estimands E1-E4 from the completed rev 3 sweep.

Definitions are taken from PARTITION_GRANULARITY_PROTOCOL.md section 7 and are not
reinterpreted here. Nothing in this script chooses an outcome; it reports intervals.
"""
import json, glob, itertools, os
import numpy as np
from scipy.stats import kendalltau

MODELS = ["yolov8n", "yolov8s", "fasterrcnn", "retinanet"]
PROTOCOLS = ["P1_random_image", "P2_event_disjoint", "P3_camera_disjoint",
             "P4_partner_lopo", "P5_temporal"]
RNG = np.random.default_rng(20260918)

def load():
    recs = {}
    for p in glob.glob("corpus/experiment_runs/*.json"):
        if "PILOT" in p:
            continue
        d = json.load(open(p))
        fam, _, seed = d["partition"].partition("__seed")
        recs[(d["model"], fam, seed)] = d
    return recs

R = load()
assert len(R) == 76, len(R)
seeds = {f: sorted({k[2] for k in R if k[1] == f}) for f in PROTOCOLS}
map50 = lambda m, f, s: R[(m, f, s)]["metrics"]["map_50"]
mean50 = lambda m, f: float(np.mean([map50(m, f, s) for s in seeds[f]]))

out = {}

# ---- split-noise floor -------------------------------------------------
# "the maximum absolute difference in replicate-mean mAP between any two P1
# replicates for the same model"
per_model_spread = {m: max(map50(m, "P1_random_image", s) for s in seeds["P1_random_image"])
                     - min(map50(m, "P1_random_image", s) for s in seeds["P1_random_image"])
                    for m in MODELS}
FLOOR = max(per_model_spread.values())
out["split_noise_floor"] = {"per_model_p1_spread": per_model_spread, "floor": FLOOR}

# ---- E1 absolute performance shift, paired by seed ---------------------
e1 = {}
for f in PROTOCOLS[1:]:
    e1[f] = {}
    for m in MODELS:
        if f in ("P2_event_disjoint", "P3_camera_disjoint"):
            d = [map50(m, f, s) - map50(m, "P1_random_image", s) for s in seeds[f]]
            paired = True
        else:  # P4 has its own 3 partners, P5 a single split: compare to the P1 mean
            base = mean50(m, "P1_random_image")
            d = [map50(m, f, s) - base for s in seeds[f]]
            paired = False
        d = np.array(d)
        if len(d) > 1:
            bs = [RNG.choice(d, len(d), replace=True).mean() for _ in range(10000)]
            lo, hi = np.percentile(bs, [2.5, 97.5])
        else:
            lo = hi = float(d[0])
        e1[f][m] = {"delta_mean": float(d.mean()), "ci95": [float(lo), float(hi)],
                    "deltas": [float(x) for x in d], "n": len(d), "seed_paired": paired}
out["E1_absolute_shift"] = e1

# ---- E2 ranking concordance --------------------------------------------
rankvec = {f: np.array([mean50(m, f) for m in MODELS]) for f in PROTOCOLS}
e2 = {}
for a, b in itertools.combinations(PROTOCOLS, 2):
    tau, _ = kendalltau(rankvec[a], rankvec[b])
    n = min(len(seeds[a]), len(seeds[b]))
    if n > 1:
        bs = []
        for _ in range(10000):
            ia = RNG.choice(seeds[a], len(seeds[a]), replace=True)
            ib = RNG.choice(seeds[b], len(seeds[b]), replace=True)
            va = [np.mean([map50(m, a, s) for s in ia]) for m in MODELS]
            vb = [np.mean([map50(m, b, s) for s in ib]) for m in MODELS]
            t, _ = kendalltau(va, vb)
            bs.append(t)
        lo, hi = np.percentile(bs, [2.5, 97.5])
    else:
        lo = hi = float("nan")
    e2[f"{a}__vs__{b}"] = {"tau": float(tau), "ci95": [float(lo), float(hi)]}
out["E2_rank_concordance"] = e2
out["E2_order_and_winner"] = {
    f: {"order": [MODELS[i] for i in np.argsort(-rankvec[f])],
        "winner": MODELS[int(np.argmax(rankvec[f]))],
        "means": {m: mean50(m, f) for m in MODELS}} for f in PROTOCOLS}

# ---- E3 pairwise reversal rate -----------------------------------------
pairs = list(itertools.combinations(MODELS, 2))
e3 = {}
for a, b in itertools.combinations(PROTOCOLS, 2):
    rev = comp = indet = 0
    detail = []
    for x, y in pairs:
        da, db = mean50(x, a) - mean50(y, a), mean50(x, b) - mean50(y, b)
        if abs(da) <= FLOOR or abs(db) <= FLOOR:
            indet += 1
            detail.append({"pair": f"{x}>{y}", "status": "indeterminate",
                           "diff_a": da, "diff_b": db})
            continue
        comp += 1
        if np.sign(da) != np.sign(db):
            rev += 1
            detail.append({"pair": f"{x}>{y}", "status": "reversed",
                           "diff_a": da, "diff_b": db})
        else:
            detail.append({"pair": f"{x}>{y}", "status": "stable",
                           "diff_a": da, "diff_b": db})
    from scipy.stats import beta as _b
    if comp:
        lo = 0.0 if rev == 0 else _b.ppf(0.025, rev, comp - rev + 1)
        hi = 1.0 if rev == comp else _b.ppf(0.975, rev + 1, comp - rev)
    else:
        lo = hi = float("nan")
    e3[f"{a}__vs__{b}"] = {"reversed": rev, "comparable": comp, "indeterminate": indet,
                           "rate": (rev / comp) if comp else None,
                           "ci95": [float(lo), float(hi)], "detail": detail}
out["E3_pairwise_reversal"] = e3

# ---- E4 winner instability ---------------------------------------------
e4 = {"winner_by_protocol": {f: MODELS[int(np.argmax(rankvec[f]))] for f in PROTOCOLS}}
e4["distinct_winners"] = sorted(set(e4["winner_by_protocol"].values()))
e4["winner_changes"] = sum(
    1 for a, b in itertools.combinations(PROTOCOLS, 2)
    if e4["winner_by_protocol"][a] != e4["winner_by_protocol"][b])
e4["protocol_pairs"] = len(list(itertools.combinations(PROTOCOLS, 2)))
rank1 = {f: {m: 0 for m in MODELS} for f in PROTOCOLS}
for f in PROTOCOLS:
    for s in seeds[f]:
        v = [map50(m, f, s) for m in MODELS]
        rank1[f][MODELS[int(np.argmax(v))]] += 1
e4["rank1_count_by_replicate"] = {f: {"counts": rank1[f], "n": len(seeds[f])} for f in PROTOCOLS}
out["E4_winner_instability"] = e4

# ---- operating-point transfer (secondary, section 4 metrics) -----------
opt = {}
for f in PROTOCOLS:
    rows = []
    for m in MODELS:
        for s in seeds[f]:
            d = R[(m, f, s)]
            op, te = d["operating_point"], d["test_at_operating_point"]
            rows.append({"model": m, "seed": s,
                         "val_f1": op["val_f1"], "test_f1": te["f1"],
                         "f1_drop": op["val_f1"] - te["f1"],
                         "thr": op["score_threshold"]})
    opt[f] = {"mean_val_f1": float(np.mean([r["val_f1"] for r in rows])),
              "mean_test_f1": float(np.mean([r["test_f1"] for r in rows])),
              "mean_f1_drop": float(np.mean([r["f1_drop"] for r in rows])),
              "per_model_f1_drop": {m: float(np.mean([r["f1_drop"] for r in rows if r["model"] == m]))
                                    for m in MODELS},
              "rows": rows}
out["S1_operating_point_transfer"] = opt

os.makedirs("corpus", exist_ok=True)
json.dump(out, open("corpus/estimands_2026-09-18.json", "w"), indent=1)
print("wrote corpus/estimands_2026-09-18.json")
print(f"\nsplit-noise floor = {FLOOR:.4f}  (per-model P1 spread: " +
      ", ".join(f"{m} {v:.4f}" for m, v in per_model_spread.items()) + ")")
