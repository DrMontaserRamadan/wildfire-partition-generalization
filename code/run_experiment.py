"""Train one (model, partition) pair under the frozen protocol and score it.

Two model families are involved, and they must not be scored by their own native evaluators: each
framework computes mAP with slightly different conventions, and a ranking comparison across
families would then confound the architecture with the metric implementation. Every model here is
trained by its own trainer and then evaluated by ONE shared routine, torchmetrics'
MeanAveragePrecision, fed identical prediction and target structures.

Sharing the metric is not enough on its own. Predictions have to reach that metric on equal terms
too, so EVAL below fixes one architecture-independent evaluation policy - the same score floor, NMS
threshold, detection cap and letterbox geometry for all four models. Left to their library defaults
the four would have predicted under three different configurations, and the two torchvision arms
would have been scored on a truncated precision-recall curve.

Everything in HYPER is fixed by PARTITION_GRANULARITY_PROTOCOL.md and must not be tuned. The
training arm is subsampled to the protocol's matched N so that a score difference between protocols
cannot be an artefact of one having more data.

The validation arm exists for exactly one purpose, set out in section 4: it selects the operating
point that maximises F1, and that fixed threshold is then applied to test. Test never selects
anything.

Usage:
    python scripts/run_experiment.py --model yolov8n --partition P1_random_image__seed20260911
    python scripts/run_experiment.py --model retinanet --partition ... --pilot
"""
import argparse
import io
import json
import math
import os
import random
import shutil
import sys
import time

import numpy as np
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

DS = os.path.abspath("datasets/pyrosdis")
SPLITS = f"{DS}/splits"
RESULTS = "corpus/experiment_runs"
CKPT = "corpus/checkpoints"
PREDS = "corpus/predictions"

# --- frozen by the protocol; do not tune -------------------------------------------------------
HYPER = {
    "imgsz": 416, "epochs": 25, "batch": 16, "optimizer": "SGD", "momentum": 0.937,
    "weight_decay": 5e-4, "lr0": 0.01, "lrf": 0.01, "warmup_epochs": 3,
    "fliplr": 0.5, "pretrained": True, "cos_lr": True,
}

# --- one evaluation policy for all four architectures, fixed before any result exists ----------
#
# The protocol did not specify how a prediction becomes a detection, so the four models would have
# inherited three different library configurations. These values are chosen from measured corpus
# properties, recorded in corpus/eval_policy_evidence.json, not from what suits any model:
#
#   score_floor 0.001  average precision integrates the precision-recall curve, so the floor must
#                      sit below the scores that populate its high-recall tail. The torchvision
#                      default of 0.05 truncates that tail and depresses AP; 0.001 is the value the
#                      YOLO family and common detection practice already use.
#   nms_iou     0.50   no two annotated objects in this corpus overlap at all - across 4,443
#                      ground-truth pairs sharing an image the maximum pairwise IoU is 0.0 - so NMS
#                      cannot suppress a true positive at any threshold in the usual range. The
#                      choice is therefore purely about duplicate suppression, and 0.50 is both the
#                      stricter option and the common convention.
#   max_det     100    the most objects in any image in the corpus is 5. A cap of 100 is twenty
#                      times that, and it is also the detection count at which torchmetrics
#                      accumulates map_50, so a larger cap would only feed the metric detections it
#                      discards.
#   match_iou   0.50   the IoU at which a detection counts as correct when locating the F1-maximal
#                      operating point, matching the primary metric.
#
# Letterbox geometry is shared for the same reason: ultralytics letterboxes to a square canvas with
# aspect preserved and a 114 fill, while the torchvision path previously stretched images to a
# square. Both now use letterbox_params below.
EVAL = {
    "score_floor": 0.001, "nms_iou": 0.50, "max_det": 100, "match_iou": 0.50,
    "letterbox_fill": 114,
}

MATCHED_N = {"P4_partner_lopo": 13836, "_default": 21995}
MODELS = ("yolov8n", "yolov8s", "retinanet", "fasterrcnn")


def matched_n(partition):
    for k, v in MATCHED_N.items():
        if partition.startswith(k):
            return v
    return MATCHED_N["_default"]


# Set by --smoke. A smoke run truncates every arm to a handful of images so that all four execution
# paths can be exercised end to end in minutes, on any machine, without a GPU rental. It is a
# correctness check and nothing else: its output is written to a separate directory so that a smoke
# result can never be mistaken for a run, and it carries no timing meaning whatsoever.
SMOKE = 0


def read_split(key, arm):
    p = f"{SPLITS}/{key}_{arm}.txt"
    rows = [ln.strip() for ln in io.open(p, encoding="utf-8") if ln.strip()]
    return rows[:SMOKE] if SMOKE else rows


def subsample(paths, n, seed):
    """Draw the matched-size training arm with the replicate's own seed."""
    if len(paths) <= n:
        return list(paths)
    rng = random.Random(seed)
    out = list(paths)
    rng.shuffle(out)
    return out[:n]


def seed_of(key):
    return int(key.rsplit("seed", 1)[1])


# --- shared geometry --------------------------------------------------------------------------

def letterbox_params(w, h, sz):
    """Aspect-preserving resize to a square canvas, matching ultralytics' LetterBox exactly.

    Reproduces ultralytics.data.augment.LetterBox with auto=False, scale_fill=False, scaleup=True,
    center=True: ratio r = min(sz/h, sz/w), unpadded size rounded, padding split in two and the top
    and left offsets taken as round(pad - 0.1). The rounding rule matters - taking round(pad)
    instead would put the torchvision arms half a pixel off the YOLO arms at odd padding widths.
    """
    r = min(sz / h, sz / w)
    nw, nh = round(w * r), round(h * r)
    dw, dh = (sz - nw) / 2, (sz - nh) / 2
    left, top = round(dw - 0.1), round(dh - 0.1)
    return r, nw, nh, left, top


# --- shared evaluation ------------------------------------------------------------------------

def load_labels(img_rel):
    stem = os.path.splitext(os.path.basename(img_rel))[0]
    p = f"{DS}/labels/{stem}.txt"
    if not os.path.exists(p):
        return []
    out = []
    for ln in io.open(p, encoding="utf-8"):
        parts = ln.split()
        if len(parts) == 5:
            out.append([int(parts[0])] + [float(x) for x in parts[1:]])
    return out


def yolo_to_xyxy(box, w, h):
    cx, cy, bw, bh = box
    return [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h]


def target_of(rel, w, h):
    lab = load_labels(rel)
    return {"boxes": torch.tensor([yolo_to_xyxy(l[1:], w, h) for l in lab],
                                  dtype=torch.float32).reshape(-1, 4),
            "labels": torch.tensor([l[0] for l in lab], dtype=torch.int32)}


def evaluate(preds, targets):
    """One metric for every model family. preds/targets are lists of dicts on CPU."""
    from torchmetrics.detection import MeanAveragePrecision
    m = MeanAveragePrecision(box_format="xyxy", iou_type="bbox",
                             max_detection_thresholds=[1, 10, EVAL["max_det"]])
    m.update(preds, targets)
    r = m.compute()
    return {"map_50": float(r["map_50"]), "map_50_95": float(r["map"]),
            "mar_100": float(r[f"mar_{EVAL['max_det']}"])}


def iou_matrix(pb, gb):
    """IoU of every predicted box against every ground-truth box, both xyxy."""
    if len(pb) == 0 or len(gb) == 0:
        return np.zeros((len(pb), len(gb)), dtype=np.float32)
    pb, gb = np.asarray(pb, np.float64), np.asarray(gb, np.float64)
    ix0 = np.maximum(pb[:, None, 0], gb[None, :, 0])
    iy0 = np.maximum(pb[:, None, 1], gb[None, :, 1])
    ix1 = np.minimum(pb[:, None, 2], gb[None, :, 2])
    iy1 = np.minimum(pb[:, None, 3], gb[None, :, 3])
    iw = np.clip(ix1 - ix0, 0, None)
    ih = np.clip(iy1 - iy0, 0, None)
    inter = iw * ih
    ap = (pb[:, 2] - pb[:, 0]) * (pb[:, 3] - pb[:, 1])
    ag = (gb[:, 2] - gb[:, 0]) * (gb[:, 3] - gb[:, 1])
    union = ap[:, None] + ag[None, :] - inter
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(union > 0, inter / union, 0.0).astype(np.float32)


def match_flags(preds, targets, iou_thr):
    """Label every prediction a true or false positive, once, for the whole arm.

    Greedy matching in descending score order, one ground-truth box per prediction, which is the
    usual detection convention. Doing it once is what makes the threshold sweep exact rather than
    approximate: raising a score threshold only removes low-scoring predictions, and because the
    greedy order is by descending score, removing them cannot change the verdict on any prediction
    that outranks them. So a single pass yields the true positive count at every threshold.
    """
    scores, is_tp = [], []
    n_gt = 0
    for p, t in zip(preds, targets):
        gb = t["boxes"].numpy()
        n_gt += len(gb)
        sc = p["scores"].numpy()
        if len(sc) == 0:
            continue
        order = np.argsort(-sc, kind="stable")
        pb = p["boxes"].numpy()[order]
        sc = sc[order]
        M = iou_matrix(pb, gb)
        taken = np.zeros(len(gb), dtype=bool)
        for i in range(len(pb)):
            j, best = -1, 0.0
            for g in range(len(gb)):
                if not taken[g] and M[i, g] > best:
                    best, j = M[i, g], g
            hit = j >= 0 and best >= iou_thr
            if hit:
                taken[j] = True
            scores.append(float(sc[i]))
            is_tp.append(bool(hit))
    return np.asarray(scores, np.float64), np.asarray(is_tp, bool), n_gt


def sweep(scores, is_tp, n_gt):
    """Precision, recall and F1 at every distinct score threshold, from cumulative counts."""
    if len(scores) == 0 or n_gt == 0:
        return np.zeros(0), np.zeros(0), np.zeros(0), np.zeros(0)
    order = np.argsort(-scores, kind="stable")
    s, tp = scores[order], is_tp[order]
    ctp = np.cumsum(tp)
    cfp = np.cumsum(~tp)
    prec = ctp / np.maximum(ctp + cfp, 1)
    rec = ctp / n_gt
    f1 = np.where(prec + rec > 0, 2 * prec * rec / np.maximum(prec + rec, 1e-12), 0.0)
    return s, prec, rec, f1


def operating_point(preds, targets):
    """The F1-maximising score threshold ON THE VALIDATION ARM. Never call this with test data."""
    scores, is_tp, n_gt = match_flags(preds, targets, EVAL["match_iou"])
    s, prec, rec, f1 = sweep(scores, is_tp, n_gt)
    if len(s) == 0:
        return {"score_threshold": 1.0, "val_precision": 0.0, "val_recall": 0.0, "val_f1": 0.0,
                "val_n_gt": int(n_gt), "val_n_pred": 0}
    i = int(np.argmax(f1))
    return {"score_threshold": float(s[i]), "val_precision": float(prec[i]),
            "val_recall": float(rec[i]), "val_f1": float(f1[i]),
            "val_n_gt": int(n_gt), "val_n_pred": int(len(s))}


def pr_at(preds, targets, thr):
    """Precision and recall at a threshold fixed elsewhere. Applied to test; never fitted on it."""
    scores, is_tp, n_gt = match_flags(preds, targets, EVAL["match_iou"])
    keep = scores >= thr
    tp = int(is_tp[keep].sum())
    fp = int((~is_tp[keep]).sum())
    fn = int(n_gt - tp)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / n_gt if n_gt else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"precision": prec, "recall": rec, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn, "n_gt": int(n_gt)}


def save_predictions(path, rels, preds):
    """Persist raw predictions so every secondary metric can be recomputed without retraining."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    counts = np.array([len(p["scores"]) for p in preds], dtype=np.int32)
    if counts.sum():
        boxes = np.concatenate([p["boxes"].numpy() for p in preds if len(p["scores"])])
        scores = np.concatenate([p["scores"].numpy() for p in preds if len(p["scores"])])
        labels = np.concatenate([p["labels"].numpy() for p in preds if len(p["scores"])])
    else:
        boxes = np.zeros((0, 4), np.float32)
        scores = np.zeros(0, np.float32)
        labels = np.zeros(0, np.int16)
    np.savez_compressed(path, images=np.array(rels), counts=counts,
                        boxes=boxes.astype(np.float32), scores=scores.astype(np.float32),
                        labels=labels.astype(np.int16))


# --- ultralytics family -----------------------------------------------------------------------

def yolo_predict(model, rels):
    from PIL import Image
    preds, targets = [], []
    for i in range(0, len(rels), 32):
        chunk = [f"{DS}/{p[2:]}" for p in rels[i:i + 32]]
        res = model.predict(chunk, imgsz=HYPER["imgsz"], conf=EVAL["score_floor"],
                            iou=EVAL["nms_iou"], max_det=EVAL["max_det"], rect=False,
                            verbose=False, device=0)
        for rel, r in zip(rels[i:i + 32], res):
            b = r.boxes
            preds.append({"boxes": b.xyxy.cpu(), "scores": b.conf.cpu(),
                          "labels": b.cls.cpu().int()})
            w, h = Image.open(f"{DS}/{rel[2:]}").size
            targets.append(target_of(rel, w, h))
    return preds, targets


def run_yolo(model_name, key, pilot):
    from ultralytics import YOLO

    epochs = 1 if (pilot or SMOKE) else HYPER["epochs"]
    seed = seed_of(key)
    train = subsample(read_split(key, "train"), matched_n(key), seed)
    val = read_split(key, "val")

    work = os.path.abspath(f"runs/{model_name}__{key}")
    os.makedirs(work, exist_ok=True)
    tr_txt, va_txt = f"{work}/train.txt", f"{work}/val.txt"
    io.open(tr_txt, "w", encoding="utf-8").write("\n".join(f"{DS}/{p[2:]}" for p in train))
    io.open(va_txt, "w", encoding="utf-8").write("\n".join(f"{DS}/{p[2:]}" for p in val))

    yaml = f"{work}/data.yaml"
    io.open(yaml, "w", encoding="utf-8").write(
        f"path: {DS}\ntrain: {tr_txt}\nval: {va_txt}\nnames:\n  0: smoke\n")

    model = YOLO(f"{model_name}.pt")
    t0 = time.time()
    # cos_lr=True is not optional: ultralytics defaults it to False and then selects a LINEAR decay,
    # while section 6 of the protocol specifies cosine and the torchvision arms implement cosine.
    # Without it two of the four models train on an undeclared schedule.
    model.train(data=yaml, epochs=epochs, imgsz=HYPER["imgsz"], batch=HYPER["batch"],
                optimizer=HYPER["optimizer"], momentum=HYPER["momentum"],
                weight_decay=HYPER["weight_decay"], lr0=HYPER["lr0"], lrf=HYPER["lrf"],
                cos_lr=HYPER["cos_lr"], warmup_epochs=HYPER["warmup_epochs"],
                fliplr=HYPER["fliplr"],
                mosaic=0.0, mixup=0.0, copy_paste=0.0, scale=0.0, translate=0.0,
                hsv_h=0.0, hsv_s=0.0, hsv_v=0.0, erasing=0.0, degrees=0.0, shear=0.0,
                perspective=0.0, flipud=0.0, auto_augment=None,
                seed=seed, deterministic=False, val=False, plots=False, save=True,
                project=work, name="train", exist_ok=True, verbose=False,
                patience=0, workers=4, rect=False)
    train_s = time.time() - t0

    t1 = time.time()
    val_preds, val_targets = yolo_predict(model, val)
    test = read_split(key, "test")
    preds, targets = yolo_predict(model, test)
    eval_s = time.time() - t1

    src = f"{work}/train/weights/last.pt"
    return {"preds": preds, "targets": targets, "val_preds": val_preds,
            "val_targets": val_targets, "train_s": train_s, "eval_s": eval_s,
            "n_train": len(train), "n_test": len(test), "n_val": len(val),
            "val_rels": val, "test_rels": test, "weights_src": src}


# --- torchvision family -----------------------------------------------------------------------

class DetDS(torch.utils.data.Dataset):
    """Letterboxed to the same geometry as the YOLO arms, for training and for evaluation.

    This previously resized to a square, which distorts aspect ratio, while ultralytics letterboxes.
    Two of the four models therefore saw differently shaped objects from the other two, at training
    time as well as at test time.
    """

    def __init__(self, paths, imgsz, train):
        self.paths, self.imgsz, self.train = paths, imgsz, train

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        from PIL import Image
        import torchvision.transforms.functional as F
        rel = self.paths[i]
        img = Image.open(f"{DS}/{rel[2:]}").convert("RGB")
        w, h = img.size
        sz = self.imgsz
        r, nw, nh, left, top = letterbox_params(w, h, sz)

        canvas = Image.new("RGB", (sz, sz), (EVAL["letterbox_fill"],) * 3)
        canvas.paste(img.resize((nw, nh), Image.BILINEAR), (left, top))

        boxes = [yolo_to_xyxy(l[1:], w, h) for l in load_labels(rel)]
        boxes = [[b[0] * r + left, b[1] * r + top, b[2] * r + left, b[3] * r + top] for b in boxes]
        labels = [l[0] + 1 for l in load_labels(rel)]   # torchvision reserves 0 for background

        t = F.to_tensor(canvas)
        if self.train and random.random() < 0.5:
            t = torch.flip(t, dims=[2])
            boxes = [[sz - b[2], b[1], sz - b[0], b[3]] for b in boxes]
        keep = [j for j, b in enumerate(boxes) if b[2] > b[0] + 1 and b[3] > b[1] + 1]
        return t, {"boxes": torch.tensor([boxes[j] for j in keep],
                                         dtype=torch.float32).reshape(-1, 4),
                   "labels": torch.tensor([labels[j] for j in keep], dtype=torch.int64)}


def collate(b):
    return tuple(zip(*b))


def build_tv(name):
    """Build a torchvision detector pinned to the protocol's input size and the common eval policy.

    These models carry their own GeneralizedRCNNTransform, which by default rescales every input
    to min_size=800 / max_size=1333. Left alone it would silently upscale our 416 px images to 800,
    so the torchvision arms would train at a different resolution from the YOLO arms while the
    protocol claimed one size for all four. min_size and max_size are therefore pinned to imgsz.

    The detection heads also carry their own inference defaults - a 0.05 score floor, 0.5 NMS and a
    100 or 300 detection cap - which differ from each other and from the YOLO arms. They are set
    from EVAL so that all four models predict under one policy.
    """
    import torchvision
    sz = HYPER["imgsz"]
    common = dict(min_size=sz, max_size=sz, detections_per_img=EVAL["max_det"])
    if name == "retinanet":
        m = torchvision.models.detection.retinanet_resnet50_fpn(
            weights="DEFAULT", score_thresh=EVAL["score_floor"], nms_thresh=EVAL["nms_iou"],
            **common)
        from torchvision.models.detection.retinanet import RetinaNetClassificationHead
        na = m.head.classification_head.num_anchors
        m.head.classification_head = RetinaNetClassificationHead(
            in_channels=256, num_anchors=na, num_classes=2)
        return m
    m = torchvision.models.detection.fasterrcnn_mobilenet_v3_large_fpn(
        weights="DEFAULT", min_size=sz, max_size=sz,
        box_score_thresh=EVAL["score_floor"], box_nms_thresh=EVAL["nms_iou"],
        box_detections_per_img=EVAL["max_det"])
    from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
    m.roi_heads.box_predictor = FastRCNNPredictor(
        m.roi_heads.box_predictor.cls_score.in_features, 2)
    return m


def tv_predict(model, rels, dev):
    """Run inference and map boxes back through the letterbox to original image coordinates."""
    from PIL import Image
    preds, targets = [], []
    dl = torch.utils.data.DataLoader(DetDS(rels, HYPER["imgsz"], False), batch_size=16,
                                     shuffle=False, num_workers=4, collate_fn=collate)
    with torch.no_grad():
        offset = 0
        for imgs, _ in dl:
            out = model([i.to(dev) for i in imgs])
            for j, o in enumerate(out):
                rel = rels[offset + j]
                w, h = Image.open(f"{DS}/{rel[2:]}").size
                r, _, _, left, top = letterbox_params(w, h, HYPER["imgsz"])
                bx = o["boxes"].cpu()
                if len(bx):
                    bx = (bx - torch.tensor([left, top, left, top], dtype=torch.float32)) / r
                else:
                    bx = bx.reshape(-1, 4)
                preds.append({"boxes": bx, "scores": o["scores"].cpu(),
                              "labels": (o["labels"].cpu() - 1).int()})
                targets.append(target_of(rel, w, h))
            offset += len(imgs)
    return preds, targets


def run_tv(model_name, key, pilot):
    epochs = 1 if (pilot or SMOKE) else HYPER["epochs"]
    seed = seed_of(key)
    torch.manual_seed(seed)
    random.seed(seed)

    train = subsample(read_split(key, "train"), matched_n(key), seed)
    val = read_split(key, "val")
    test = read_split(key, "test")
    dev = torch.device("cuda")

    dl = torch.utils.data.DataLoader(
        DetDS(train, HYPER["imgsz"], True), batch_size=HYPER["batch"], shuffle=True,
        num_workers=4, collate_fn=collate, persistent_workers=True, pin_memory=True)

    model = build_tv(model_name).to(dev)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.SGD(params, lr=HYPER["lr0"], momentum=HYPER["momentum"],
                          weight_decay=HYPER["weight_decay"])
    steps = max(1, len(dl)) * epochs
    warm = max(1, len(dl)) * HYPER["warmup_epochs"]

    def lr_at(s):
        if s < warm:
            return (s + 1) / warm
        p = (s - warm) / max(1, steps - warm)
        return HYPER["lrf"] + (1 - HYPER["lrf"]) * 0.5 * (1 + math.cos(math.pi * p))

    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_at)
    scaler = torch.amp.GradScaler("cuda")

    t0 = time.time()
    model.train()
    for ep in range(epochs):
        for imgs, tgts in dl:
            imgs = [i.to(dev, non_blocking=True) for i in imgs]
            tgts = [{k: v.to(dev) for k, v in t.items()} for t in tgts]
            with torch.amp.autocast("cuda"):
                loss = sum(build_loss(model, imgs, tgts).values())
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
        print(f"    epoch {ep+1}/{epochs} done ({time.time()-t0:.0f}s)", flush=True)
    train_s = time.time() - t0

    model.eval()
    t1 = time.time()
    val_preds, val_targets = tv_predict(model, val, dev)
    preds, targets = tv_predict(model, test, dev)
    eval_s = time.time() - t1

    return {"preds": preds, "targets": targets, "val_preds": val_preds,
            "val_targets": val_targets, "train_s": train_s, "eval_s": eval_s,
            "n_train": len(train), "n_test": len(test), "n_val": len(val),
            "val_rels": val, "test_rels": test, "state_dict": model.state_dict()}


def build_loss(model, imgs, tgts):
    return model(imgs, tgts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=MODELS)
    ap.add_argument("--partition", required=True)
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--smoke", type=int, default=0,
                    help="truncate every arm to N images and run one epoch; correctness only")
    a = ap.parse_args()

    global SMOKE, RESULTS, CKPT, PREDS
    if a.smoke:
        SMOKE = a.smoke
        RESULTS, CKPT, PREDS = (f"{d}_smoke" for d in (RESULTS, CKPT, PREDS))

    os.makedirs(RESULTS, exist_ok=True)
    tag = f"{a.model}__{a.partition}" + ("__PILOT" if a.pilot else "") + ("__SMOKE" if a.smoke else "")
    out_p = f"{RESULTS}/{tag}.json"
    if os.path.exists(out_p) and not (a.pilot or a.smoke):
        print(f"already done: {out_p}")
        return 0

    torch.cuda.reset_peak_memory_stats()
    print(f"RUN {tag}  matched_n={matched_n(a.partition)} "
          f"epochs={1 if (a.pilot or a.smoke) else HYPER['epochs']}", flush=True)

    fn = run_yolo if a.model.startswith("yolo") else run_tv
    r = fn(a.model, a.partition, a.pilot)

    metrics = evaluate(r["preds"], r["targets"])
    # Section 4: the operating point is chosen on validation, never on test. These two calls are
    # the whole of that rule - op comes from the validation arm alone, and the threshold it returns
    # is then applied unchanged to test.
    op = operating_point(r["val_preds"], r["val_targets"])
    test_pr = pr_at(r["preds"], r["targets"], op["score_threshold"])
    metrics.update({"precision": test_pr["precision"], "recall": test_pr["recall"],
                    "f1": test_pr["f1"]})
    peak_gb = torch.cuda.max_memory_allocated() / 1e9

    os.makedirs(CKPT, exist_ok=True)
    ck = f"{CKPT}/{tag}.pt"
    if "state_dict" in r:
        torch.save({"model": a.model, "partition": a.partition,
                    "state_dict": {k: v.cpu() for k, v in r["state_dict"].items()}}, ck)
    else:
        shutil.copyfile(r["weights_src"], ck)

    save_predictions(f"{PREDS}/{tag}__val.npz", r["val_rels"], r["val_preds"])
    save_predictions(f"{PREDS}/{tag}__test.npz", r["test_rels"], r["preds"])

    rec = {"model": a.model, "partition": a.partition, "pilot": a.pilot,
           "n_train_used": r["n_train"], "n_test": r["n_test"], "n_val": r["n_val"],
           "train_seconds": round(r["train_s"], 1), "eval_seconds": round(r["eval_s"], 1),
           "peak_gpu_gb": round(peak_gb, 2), "metrics": metrics,
           "operating_point": op, "test_at_operating_point": test_pr,
           "epochs": 1 if (a.pilot or a.smoke) else HYPER["epochs"], "hyper": HYPER, "eval_policy": EVAL,
           "checkpoint": ck, "checkpoint_bytes": os.path.getsize(ck),
           "predictions": [f"{PREDS}/{tag}__val.npz", f"{PREDS}/{tag}__test.npz"]}
    json.dump(rec, io.open(out_p, "w", encoding="utf-8"), indent=1)
    print(f"  mAP@50 {metrics['map_50']:.4f} | mAP@50:95 {metrics['map_50_95']:.4f} "
          f"| P {metrics['precision']:.4f} R {metrics['recall']:.4f} "
          f"@thr {op['score_threshold']:.4f} (val F1 {op['val_f1']:.4f})")
    print(f"  train {r['train_s']:.0f}s | eval {r['eval_s']:.0f}s | peak {peak_gb:.2f} GB")
    print(f"  wrote {out_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
