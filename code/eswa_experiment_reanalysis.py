"""Re-analyses of the partition-granularity experiment requested by the ESWA panel (2026-11-18).

No model is trained here. Everything is computed from artifacts the 76 runs already wrote:
the per-run records (corpus/experiment_runs), the stored raw predictions (corpus/predictions),
the split files (datasets/pyrosdis/splits) and the image files themselves.

Analyses, each labelled by whether the protocol pre-specified it:
  R1  PRE-SPECIFIED (protocol sec. 8 item 3), previously unreported: detector ranking and Kendall
      tau under mAP@0.50:0.95 instead of mAP@0.50.
  R2  PRE-SPECIFIED (protocol sec. 7, E1), previously reported by bootstrap instead: linear mixed
      model, mAP@0.50 ~ rule, random intercepts for detector and replicate.
  R3  PRE-SPECIFIED (protocol sec. 8 item 5): each partner held out in turn (the three P4 folds),
      reported per fold.
  R4  POST HOC: complete-separation count (every group-disjoint run vs every random run).
  R5  POST HOC: paired RetinaNet - YOLOv8s differences within replicate, t interval (df = n-1).
  R6  POST HOC: share of each test arm with a confirmed near-duplicate in the TRAINING arm that
      was actually used (matched subsample), same hash + NCC gate as the cross-corpus audit.
  R7  PRE-SPECIFIED estimand S1_operating_point_transfer, previously unreported, extended post hoc:
      at the validation-chosen threshold, event-level detection rate (share of test events with
      at least one correctly localised plume) and false-alarm rate on smoke-free test images.
  R8  POST HOC: matched-image AP. For each replicate, the images that sit in the test arm of BOTH
      the random rule and a group-disjoint rule are scored with each rule's model, so the test
      images are identical and only the training allocation differs.

Not computable without retraining, so NOT run here and reported as protocol deviations:
  sec. 8 item 1 (event gap 15 / 60 min) and item 2 (unmatched training size).

Usage:  python scripts/eswa_experiment_reanalysis.py hash     # step 1, ~10-20 min, CPU
        python scripts/eswa_experiment_reanalysis.py analyse  # step 2
"""
import glob
import io
import itertools
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

DS = os.path.abspath("datasets/pyrosdis")
RUNS = "corpus/experiment_runs"
HASH_CACHE = "corpus/pyrosdis_image_hashes.npz"
OUT = "corpus/eswa_reanalysis_2026-11-18.json"
MODELS = ("yolov8n", "yolov8s", "retinanet", "fasterrcnn")
WORKING = ("yolov8n", "yolov8s", "retinanet")
RULES = ("P1_random_image", "P2_event_disjoint", "P3_camera_disjoint", "P4_partner_lopo",
         "P5_temporal")
HAMMING_MAX, NCC_MIN = 5, 0.95


# ------------------------------------------------------------------ step 1: hashes ------------
def step_hash():
    from overlap_audit import hashes
    from PIL import Image
    imgs = sorted(os.listdir(f"{DS}/images"))
    n = len(imgs)
    dh = np.zeros(n, np.uint64)
    ph = np.zeros(n, np.uint64)
    ncc = np.zeros((n, 1024), np.float32)
    wh = np.zeros((n, 2), np.int32)
    bad = []
    for i, f in enumerate(imgs):
        p = f"{DS}/images/{f}"
        h = hashes(p)
        if h is None:
            bad.append(f)
            continue
        dh[i], ph[i] = np.uint64(h[0]), np.uint64(h[1])
        ncc[i] = np.asarray(h[2], np.float32).reshape(-1)
        with Image.open(p) as im:
            wh[i] = im.size
        if i % 2000 == 0:
            print(f"  {i}/{n}", flush=True)
    np.savez_compressed(HASH_CACHE, names=np.array(imgs), dhash=dh, phash=ph, ncc=ncc, wh=wh)
    print(f"hashed {n - len(bad)}/{n}; unreadable {len(bad)} -> {HASH_CACHE}")


# ------------------------------------------------------------------ helpers -------------------
def runs():
    out = {}
    for p in glob.glob(f"{RUNS}/*.json"):
        if "PILOT" in p:
            continue
        r = json.load(io.open(p, encoding="utf-8"))
        rule, seed = r["partition"].split("__seed")
        out[(r["model"], rule, int(seed))] = r
    return out


def tau(a, b):
    s = 0
    pairs = list(itertools.combinations(range(len(a)), 2))
    for i, j in pairs:
        s += np.sign(a[i] - a[j]) * np.sign(b[i] - b[j])
    return float(s / len(pairs))


def t_interval(x):
    from scipy import stats
    x = np.asarray(x, float)
    if len(x) < 2:
        return {"n": len(x), "mean": float(x.mean()) if len(x) else None, "lo": None, "hi": None}
    m, se = x.mean(), x.std(ddof=1) / math.sqrt(len(x))
    q = stats.t.ppf(0.975, len(x) - 1)
    return {"n": len(x), "mean": float(m), "lo": float(m - q * se), "hi": float(m + q * se),
            "values": [float(v) for v in x]}


def popcount64(a):
    return np.bitwise_count(a)


def base(rel):
    return os.path.basename(rel)


# ------------------------------------------------------------------ step 2 -------------------
def r1_r4_r5(R):
    res = {}
    seeds = sorted({k[2] for k in R if k[1] == "P1_random_image"})
    for metric in ("map_50", "map_50_95"):
        means = {}
        for rule in RULES:
            means[rule] = {m: float(np.mean([R[(m, rule, s)]["metrics"][metric]
                                             for (mm, rr, s) in R if mm == m and rr == rule]))
                           for m in MODELS}
        order = {rule: sorted(MODELS, key=lambda m: -means[rule][m]) for rule in RULES}
        taus = {}
        for a, b in itertools.combinations(RULES, 2):
            taus[f"{a}|{b}"] = {
                "all4": tau([means[a][m] for m in MODELS], [means[b][m] for m in MODELS]),
                "working3": tau([means[a][m] for m in WORKING], [means[b][m] for m in WORKING])}
        res[metric] = {"means": means, "order": order, "tau": taus}
    # R4 separation
    sep = {}
    for m in MODELS:
        rand = [R[k]["metrics"]["map_50"] for k in R if k[0] == m and k[1] == "P1_random_image"]
        grp = [R[k]["metrics"]["map_50"] for k in R if k[0] == m and k[1] != "P1_random_image"]
        sep[m] = {"n_random": len(rand), "n_grouped": len(grp), "worst_random": min(rand),
                  "best_grouped": max(grp), "separated": max(grp) < min(rand)}
    res["separation"] = sep
    # drops for working detectors, absolute and relative, per rung
    drops = {}
    for rule in RULES[1:]:
        for m in MODELS:
            r0 = res["map_50"]["means"]["P1_random_image"][m]
            r1 = res["map_50"]["means"][rule][m]
            drops[f"{rule}|{m}"] = {"abs": r0 - r1, "rel": (r0 - r1) / r0}
    res["drops_map50"] = drops
    # R5 paired RetinaNet - YOLOv8s
    paired = {}
    for rule in RULES:
        ss = sorted({k[2] for k in R if k[1] == rule})
        for metric in ("map_50", "map_50_95"):
            d = [R[("retinanet", rule, s)]["metrics"][metric] - R[("yolov8s", rule, s)]["metrics"][metric]
                 for s in ss if ("retinanet", rule, s) in R and ("yolov8s", rule, s) in R]
            paired[f"{rule}|{metric}"] = t_interval(d)
    res["paired_retinanet_minus_yolov8s"] = paired
    # R3 partner folds, per fold
    res["partner_folds"] = {str(s): {m: R[(m, "P4_partner_lopo", s)]["metrics"]["map_50"] for m in MODELS}
                            for s in sorted({k[2] for k in R if k[1] == "P4_partner_lopo"})}
    return res


def r2_lmm(R):
    import pandas as pd
    import statsmodels.formula.api as smf
    rows = [{"map": r["metrics"]["map_50"], "rule": k[1], "model": k[0], "rep": str(k[2])}
            for k, r in R.items() if k[1] != "P4_partner_lopo"]
    out = {}
    for label, sub in (("all4", rows), ("working3", [r for r in rows if r["model"] != "fasterrcnn"])):
        df = pd.DataFrame(sub)
        df["rule"] = pd.Categorical(df["rule"], categories=[r for r in RULES if r != "P4_partner_lopo"])
        # model and replicate as crossed random intercepts via variance components
        df["one"] = 1
        md = smf.mixedlm("map ~ C(rule)", df, groups=df["one"],
                         vc_formula={"model": "0 + C(model)", "rep": "0 + C(rep)"})
        fit = md.fit(reml=True)
        ci = fit.conf_int()
        out[label] = {name: {"est": float(fit.params[name]), "lo": float(ci.loc[name, 0]),
                             "hi": float(ci.loc[name, 1]), "p": float(fit.pvalues[name])}
                      for name in fit.params.index if name.startswith("C(rule)") or name == "Intercept"}
        out[label]["converged"] = bool(fit.converged)
    return out


def load_hashes():
    z = np.load(HASH_CACHE, allow_pickle=False)
    idx = {n: i for i, n in enumerate(z["names"])}
    return idx, z["dhash"], z["phash"], z["ncc"], z["wh"]


def r6_neardup(R):
    from run_experiment import read_split, subsample, matched_n
    idx, dh, ph, ncc, _ = load_hashes()
    nccn = ncc - ncc.mean(1, keepdims=True)
    nccn /= np.maximum(np.linalg.norm(nccn, axis=1, keepdims=True), 1e-9)
    out = {}
    keys = sorted({f"{k[1]}__seed{k[2]}" for k in R})
    for key in keys:
        tr = subsample(read_split(key, "train"), matched_n(key), int(key.rsplit("seed", 1)[1]))
        te = read_split(key, "test")
        ti = np.array([idx[base(p)] for p in tr])
        ei = np.array([idx[base(p)] for p in te])
        tdh, tph, tv = dh[ti], ph[ti], nccn[ti]
        hit = np.zeros(len(ei), bool)
        for c0 in range(0, len(ei), 256):
            c = ei[c0:c0 + 256]
            cand = (popcount64(dh[c][:, None] ^ tdh[None, :]) <= HAMMING_MAX) | \
                   (popcount64(ph[c][:, None] ^ tph[None, :]) <= HAMMING_MAX)
            for r_, row in enumerate(cand):
                js = np.nonzero(row)[0]
                if len(js) and float((tv[js] @ nccn[c[r_]]).max()) >= NCC_MIN:
                    hit[c0 + r_] = True
        out[key] = {"n_test": int(len(ei)), "n_train_used": int(len(ti)),
                    "test_with_train_neardup": int(hit.sum()), "share": float(hit.mean())}
        print(f"  R6 {key}: {hit.mean():.3f}", flush=True)
    return out


def load_preds(path):
    with np.load(path, allow_pickle=False) as z:   # read each array ONCE; npz access is lazy
        images, counts, boxes, scores = z["images"], z["counts"], z["boxes"], z["scores"]
    offs = np.concatenate([[0], np.cumsum(counts)])
    return [(base(str(images[i])), boxes[offs[i]:offs[i + 1]], scores[offs[i]:offs[i + 1]])
            for i in range(len(counts))]


def gt_boxes(name, wh):
    from run_experiment import load_labels, yolo_to_xyxy
    w, h = wh
    return np.array([yolo_to_xyxy(l[1:], w, h) for l in load_labels(f"images/{name}")],
                    np.float64).reshape(-1, 4)


def r7_events(R):
    from run_experiment import iou_matrix
    from pyrosdis_partitions import load_rows, assign_events
    rows = load_rows()
    assign_events(rows)
    ev = {os.path.basename(r.get("file") or r.get("path") or r.get("image") or r.get("name")): r["event"]
          for r in rows}
    idx, _, _, _, wh = load_hashes()
    gt_cache = {}
    out = {}
    for k, r in sorted(R.items()):
        thr = r["operating_point"]["score_threshold"]
        preds = load_preds(r["predictions"][1])
        ev_pos, ev_hit = set(), set()
        neg, neg_alarm, pos_img, pos_hit = 0, 0, 0, 0
        for name, pb, sc in preds:
            if name not in gt_cache:
                gt_cache[name] = gt_boxes(name, wh[idx[name]])
            gb = gt_cache[name]
            keep = sc >= thr
            pb = pb[keep]
            if len(gb) == 0:
                neg += 1
                neg_alarm += int(len(pb) > 0)
                continue
            pos_img += 1
            e = ev[name]
            ev_pos.add(e)
            if len(pb) and (iou_matrix(pb, gb) >= 0.5).any():
                ev_hit.add(e)
                pos_hit += 1
        out[f"{k[0]}|{k[1]}|{k[2]}"] = {
            "threshold": thr, "events_with_smoke": len(ev_pos), "events_detected": len(ev_hit),
            "event_detection_rate": len(ev_hit) / max(len(ev_pos), 1),
            "smoke_images": pos_img, "smoke_images_hit": pos_hit,
            "negative_images": neg, "negative_images_with_alarm": neg_alarm,
            "false_alarm_image_rate": neg_alarm / neg if neg else None}
    return out


def r8_matched(R):
    import torch
    from run_experiment import evaluate
    idx, _, _, _, wh = load_hashes()
    out = {}
    for rule in ("P2_event_disjoint", "P3_camera_disjoint", "P5_temporal"):
        for s in sorted({k[2] for k in R if k[1] == rule}):
            for m in MODELS:
                if (m, rule, s) not in R or (m, "P1_random_image", s) not in R:
                    continue
                pr = {n: (b, c) for n, b, c in load_preds(R[(m, "P1_random_image", s)]["predictions"][1])}
                pg = {n: (b, c) for n, b, c in load_preds(R[(m, rule, s)]["predictions"][1])}
                common = sorted(set(pr) & set(pg))
                if len(common) < 50:
                    continue
                tg = [{"boxes": torch.tensor(gt_boxes(n, wh[idx[n]]), dtype=torch.float32).reshape(-1, 4),
                       "labels": torch.zeros(len(gt_boxes(n, wh[idx[n]])), dtype=torch.int32)} for n in common]

                def P(d):
                    return [{"boxes": torch.tensor(d[n][0], dtype=torch.float32).reshape(-1, 4),
                             "scores": torch.tensor(d[n][1], dtype=torch.float32),
                             "labels": torch.zeros(len(d[n][1]), dtype=torch.int32)} for n in common]
                a = evaluate(P(pr), tg)["map_50"]
                b = evaluate(P(pg), tg)["map_50"]
                out[f"{m}|{rule}|{s}"] = {"n_common": len(common), "map50_random_model": a,
                                          "map50_grouped_model": b, "gap": a - b}
                print(f"  R8 {m} {rule} {s}: n={len(common)} {a:.3f} vs {b:.3f}", flush=True)
    return out


def step_analyse(which):
    R = runs()
    assert len(R) == 76, len(R)
    res = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    res["_note"] = __doc__
    if "core" in which:
        res["R1_R4_R5"] = r1_r4_r5(R)
        res["R2_lmm"] = r2_lmm(R)
    def save():
        json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=1)
    save()
    if "dup" in which:
        res["R6_neardup"] = r6_neardup(R)
        save()
    if "events" in which:
        res["R7_events"] = r7_events(R)
        save()
    if "matched" in which:
        res["R8_matched"] = r8_matched(R)
    save()
    print("wrote", OUT)


if __name__ == "__main__":
    if sys.argv[1] == "hash":
        step_hash()
    else:
        step_analyse(sys.argv[2:] or ["core", "dup", "events", "matched"])
