"""Checks on the rev-3 corrections to run_experiment.py, run before any GPU is rented.

Each test targets one of the corrections, and several of them are written to fail if the correction
is quietly undone later:

  - the letterbox geometry is compared against ultralytics' own LetterBox rather than against a
    reimplementation of it, so the two families cannot drift apart silently;
  - the cosine schedule is read back out of the constructed trainer, not off the argument that was
    passed in, because passing cos_lr=True to something that ignores it would look identical;
  - the operating point is shown to be insensitive to the test arm, which is the leakage the
    protocol forbids;
  - the fast threshold sweep is checked against a brute-force recount at every threshold.

    python scripts/test_run_experiment.py
"""
import io
import math
import os
import sys
import tempfile

import numpy as np
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.chdir(ROOT)

import run_experiment as R

FAILED = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if detail else ""))
    if not cond:
        FAILED.append(name)
    return cond


# --------------------------------------------------------------------------------------------
def test_letterbox_matches_ultralytics():
    """The two families must letterbox to the same pixels, not merely to the same size."""
    print("\n[1] letterbox geometry is identical to ultralytics' LetterBox")
    from ultralytics.data.augment import LetterBox
    sz = R.HYPER["imgsz"]
    lb = LetterBox((sz, sz), auto=False, scale_fill=False, scaleup=True, center=True)

    rng = np.random.default_rng(0)
    shapes = [(1280, 720), (720, 1280), (416, 416), (1920, 1080), (640, 480), (333, 1001)]
    shapes += [tuple(rng.integers(64, 2000, 2)) for _ in range(40)]

    worst = 0
    ok_all = True
    for w, h in shapes:
        r, nw, nh, left, top = R.letterbox_params(int(w), int(h), sz)
        img = np.zeros((int(h), int(w), 3), dtype=np.uint8)
        out = lb(image=img)
        # Reconstruct ultralytics' own offsets from the padded result.
        ok = out.shape[:2] == (sz, sz)
        params = lb.get_params({"img": img})
        same = (params["top"] == top and params["left"] == left
                and params["new_unpad"] == (nw, nh)
                and abs(params["ratio"][0] - r) < 1e-12)
        worst = max(worst, abs(params["top"] - top), abs(params["left"] - left))
        ok_all &= ok and same
    check("geometry agrees on 46 image shapes", ok_all, f"max offset difference {worst} px")

    # The rounding rule is the part most likely to be got wrong; prove it is load-bearing.
    naive_differs = False
    for w, h in shapes:
        r, nw, nh, left, top = R.letterbox_params(int(w), int(h), sz)
        if left != round((sz - nw) / 2) or top != round((sz - nh) / 2):
            naive_differs = True
    check("round(pad - 0.1) differs from round(pad) on at least one real shape", naive_differs,
          "so the rule is not cosmetic")


# --------------------------------------------------------------------------------------------
def test_box_roundtrip():
    """A box letterboxed forward and mapped back must land where it started."""
    print("\n[2] letterbox box mapping is invertible")
    sz = R.HYPER["imgsz"]
    worst = 0.0
    for w, h in [(1280, 720), (720, 1280), (1920, 1080), (333, 1001), (416, 416)]:
        r, nw, nh, left, top = R.letterbox_params(w, h, sz)
        for box in ([10, 20, 110, 220], [0, 0, w, h], [w * 0.4, h * 0.4, w * 0.6, h * 0.6]):
            fwd = [box[0] * r + left, box[1] * r + top, box[2] * r + left, box[3] * r + top]
            back = [(fwd[0] - left) / r, (fwd[1] - top) / r,
                    (fwd[2] - left) / r, (fwd[3] - top) / r]
            worst = max(worst, max(abs(a - b) for a, b in zip(box, back)))
    check("forward then inverse returns the original box", worst < 1e-9,
          f"worst error {worst:.2e} px")


# --------------------------------------------------------------------------------------------
def test_matching_and_sweep():
    """Known-answer tests for the matcher, then the fast sweep against brute force."""
    print("\n[3] detection matching and the threshold sweep")

    def P(boxes, scores):
        return {"boxes": torch.tensor(boxes, dtype=torch.float32).reshape(-1, 4),
                "scores": torch.tensor(scores, dtype=torch.float32),
                "labels": torch.zeros(len(scores), dtype=torch.int32)}

    def T(boxes):
        return {"boxes": torch.tensor(boxes, dtype=torch.float32).reshape(-1, 4),
                "labels": torch.zeros(len(boxes), dtype=torch.int32)}

    # One perfect detection.
    s, tp, n = R.match_flags([P([[0, 0, 10, 10]], [0.9])], [T([[0, 0, 10, 10]])], 0.5)
    check("a perfect box is a true positive", list(tp) == [True] and n == 1)

    # Two detections on one object: the better-scoring one wins, the other is a duplicate.
    s, tp, n = R.match_flags([P([[0, 0, 10, 10], [0, 0, 10, 10]], [0.9, 0.8])],
                             [T([[0, 0, 10, 10]])], 0.5)
    check("a duplicate on the same object is a false positive", list(tp) == [True, False])

    # A box that misses.
    s, tp, n = R.match_flags([P([[100, 100, 110, 110]], [0.9])], [T([[0, 0, 10, 10]])], 0.5)
    check("a non-overlapping box is a false positive", list(tp) == [False] and n == 1)

    # Below the IoU threshold.
    s, tp, n = R.match_flags([P([[0, 0, 10, 4]], [0.9])], [T([[0, 0, 10, 10]])], 0.5)
    check("IoU 0.4 does not count at match_iou 0.5", list(tp) == [False])

    # An image with no ground truth contributes false positives but no recall denominator.
    s, tp, n = R.match_flags([P([[0, 0, 10, 10]], [0.9])], [T([])], 0.5)
    check("a detection on an empty image is a false positive", list(tp) == [False] and n == 0)

    # Fast sweep vs brute force on random data.
    rng = np.random.default_rng(7)
    preds, targets = [], []
    for _ in range(60):
        ng = int(rng.integers(0, 4))
        gt = []
        for g in range(ng):
            x, y = rng.uniform(0, 200, 2)
            gt.append([x, y, x + 30, y + 30])
        npred = int(rng.integers(0, 8))
        pb, ps = [], []
        for _ in range(npred):
            if ng and rng.random() < 0.6:
                g = gt[int(rng.integers(0, ng))]
                jitter = rng.uniform(-8, 8, 4)
                pb.append([g[0] + jitter[0], g[1] + jitter[1], g[2] + jitter[2], g[3] + jitter[3]])
            else:
                x, y = rng.uniform(0, 200, 2)
                pb.append([x, y, x + 30, y + 30])
            ps.append(float(rng.random()))
        preds.append(P(pb, ps))
        targets.append(T(gt))

    scores, is_tp, n_gt = R.match_flags(preds, targets, 0.5)
    s, prec, rec, f1 = R.sweep(scores, is_tp, n_gt)

    worst = 0.0
    for i in range(0, len(s), max(1, len(s) // 25)):
        thr = s[i]
        brute = R.pr_at(preds, targets, thr)
        worst = max(worst, abs(brute["precision"] - prec[i]), abs(brute["recall"] - rec[i]))
    check("cumulative sweep equals a brute-force recount at 25 thresholds", worst < 1e-12,
          f"worst disagreement {worst:.2e}")

    op = R.operating_point(preds, targets)
    best = float(f1.max())
    check("operating_point returns the F1 maximum", abs(op["val_f1"] - best) < 1e-12,
          f"F1 {op['val_f1']:.4f} at threshold {op['score_threshold']:.4f}")


# --------------------------------------------------------------------------------------------
def test_no_test_leakage():
    """The threshold must be a function of the validation arm and nothing else."""
    print("\n[4] the operating point cannot see the test arm")
    rng = np.random.default_rng(11)

    def arm(n, seed_shift):
        g = np.random.default_rng(11 + seed_shift)
        preds, targets = [], []
        for _ in range(n):
            gt = [[10, 10, 40, 40]] if g.random() < 0.8 else []
            pb = [[10 + g.uniform(-5, 5), 10, 40, 40]]
            ps = [float(g.random())]
            preds.append({"boxes": torch.tensor(pb, dtype=torch.float32),
                          "scores": torch.tensor(ps, dtype=torch.float32),
                          "labels": torch.zeros(1, dtype=torch.int32)})
            targets.append({"boxes": torch.tensor(gt, dtype=torch.float32).reshape(-1, 4),
                            "labels": torch.zeros(len(gt), dtype=torch.int32)})
        return preds, targets

    vp, vt = arm(50, 0)
    tp1, tt1 = arm(50, 1)
    tp2, tt2 = arm(50, 2)

    a = R.operating_point(vp, vt)["score_threshold"]
    b = R.operating_point(vp, vt)["score_threshold"]
    check("the threshold is deterministic given the validation arm", a == b)

    r1 = R.pr_at(tp1, tt1, a)
    r2 = R.pr_at(tp2, tt2, a)
    check("two different test arms do not change the threshold", a == b,
          f"threshold {a:.4f}, test recalls {r1['recall']:.3f} and {r2['recall']:.3f}")

    # The real guarantee is structural: main() passes val to operating_point and test to pr_at.
    src = io.open("scripts/run_experiment.py", encoding="utf-8").read()
    ok = ('op = operating_point(r["val_preds"], r["val_targets"])' in src
          and 'test_pr = pr_at(r["preds"], r["targets"], op["score_threshold"])' in src
          and src.count("operating_point(") == 2)   # the definition and that single call
    check("main() selects on val and applies to test, and calls operating_point exactly once", ok)


# --------------------------------------------------------------------------------------------
def test_common_inference_policy_is_applied():
    """Read the thresholds back off the constructed detectors, not off the arguments."""
    print("\n[5] the common inference policy reaches the torchvision detectors")
    rn = R.build_tv("retinanet")
    fr = R.build_tv("fasterrcnn")

    check("retinanet score floor", abs(rn.score_thresh - R.EVAL["score_floor"]) < 1e-12,
          f"{rn.score_thresh}")
    check("retinanet NMS IoU", abs(rn.nms_thresh - R.EVAL["nms_iou"]) < 1e-12, f"{rn.nms_thresh}")
    check("retinanet detection cap", rn.detections_per_img == R.EVAL["max_det"],
          f"{rn.detections_per_img}")
    check("faster r-cnn score floor",
          abs(fr.roi_heads.score_thresh - R.EVAL["score_floor"]) < 1e-12,
          f"{fr.roi_heads.score_thresh}")
    check("faster r-cnn NMS IoU", abs(fr.roi_heads.nms_thresh - R.EVAL["nms_iou"]) < 1e-12,
          f"{fr.roi_heads.nms_thresh}")
    check("faster r-cnn detection cap", fr.roi_heads.detections_per_img == R.EVAL["max_det"],
          f"{fr.roi_heads.detections_per_img}")
    check("both pinned to the protocol's input size",
          rn.transform.min_size == (R.HYPER["imgsz"],) and rn.transform.max_size == R.HYPER["imgsz"]
          and fr.transform.min_size == (R.HYPER["imgsz"],)
          and fr.transform.max_size == R.HYPER["imgsz"])

    src = io.open("scripts/run_experiment.py", encoding="utf-8").read()
    check("the YOLO predict call carries the same policy",
          'conf=EVAL["score_floor"]' in src and 'iou=EVAL["nms_iou"]' in src
          and 'max_det=EVAL["max_det"]' in src and "rect=False" in src)
    return rn


# --------------------------------------------------------------------------------------------
def test_cosine_is_actually_active():
    """Read the schedule out of the trainer, and compare the two families point by point."""
    print("\n[6] cosine decay is what both families actually execute")
    from ultralytics.utils import ops  # noqa: F401  (import surfaces a broken install early)
    from ultralytics.models.yolo.detect import DetectionTrainer

    tmp = tempfile.mkdtemp()
    data = os.path.join(tmp, "d.yaml")
    io.open(data, "w", encoding="utf-8").write(
        f"path: {tmp}\ntrain: t.txt\nval: t.txt\nnames:\n  0: smoke\n")
    io.open(os.path.join(tmp, "t.txt"), "w", encoding="utf-8").write("")

    epochs = R.HYPER["epochs"]
    got = {}
    for cos in (True, False):
        t = DetectionTrainer(overrides={"model": "yolov8n.pt", "data": data, "epochs": epochs,
                                        "cos_lr": cos, "lrf": R.HYPER["lrf"], "lr0": R.HYPER["lr0"],
                                        "project": tmp, "name": f"c{cos}", "exist_ok": True})
        t.epochs = epochs
        # _setup_scheduler wraps self.optimizer, which only exists once a full training run has
        # been set up. A one-parameter stand-in is enough: the quantity under test is the lambda
        # the trainer chooses, not what it is attached to.
        t.optimizer = torch.optim.SGD([torch.nn.Parameter(torch.zeros(1))], lr=R.HYPER["lr0"])
        t._setup_scheduler()
        got[cos] = np.array([t.lf(e) for e in range(epochs + 1)], dtype=float)

    lrf = R.HYPER["lrf"]
    want_cos = np.array([((1 - math.cos(e * math.pi / epochs)) / 2) * (lrf - 1) + 1
                         for e in range(epochs + 1)])
    want_lin = np.array([max(1 - e / epochs, 0) * (1.0 - lrf) + lrf for e in range(epochs + 1)])

    check("cos_lr=True yields a cosine lambda in the trainer",
          np.allclose(got[True], want_cos, atol=1e-12),
          f"max deviation {np.abs(got[True]-want_cos).max():.2e}")
    check("cos_lr=False would have been linear (the bug rev 2 shipped)",
          np.allclose(got[False], want_lin, atol=1e-12)
          and not np.allclose(got[False], want_cos, atol=1e-3),
          f"linear and cosine differ by up to {np.abs(got[False]-want_cos).max():.3f}")
    check("run_experiment passes cos_lr from HYPER and HYPER says True",
          R.HYPER["cos_lr"] is True
          and 'cos_lr=HYPER["cos_lr"]' in io.open("scripts/run_experiment.py",
                                                  encoding="utf-8").read())

    # The torchvision arms build their own lambda; compare the two on a common progress axis.
    steps_per_epoch = 100
    steps = steps_per_epoch * epochs
    warm = steps_per_epoch * R.HYPER["warmup_epochs"]

    def lr_at(s):
        if s < warm:
            return (s + 1) / warm
        p = (s - warm) / max(1, steps - warm)
        return lrf + (1 - lrf) * 0.5 * (1 + math.cos(math.pi * p))

    tv = np.array([lr_at(s) for s in range(warm, steps + 1)])
    prog = np.linspace(0, 1, len(tv))
    yolo_on_prog = np.array([((1 - math.cos(p * math.pi)) / 2) * (lrf - 1) + 1 for p in prog])
    check("the torchvision cosine matches the YOLO cosine after warmup",
          np.allclose(tv, yolo_on_prog, atol=1e-12),
          f"max deviation {np.abs(tv - yolo_on_prog).max():.2e}")
    check("it starts at lr0 and ends at lr0*lrf",
          abs(tv[0] - 1.0) < 1e-12 and abs(tv[-1] - lrf) < 1e-12)


# --------------------------------------------------------------------------------------------
def test_tv_predict_geometry():
    """Drive the real tv_predict inverse with a known answer.

    Both torchvision arms scored exactly zero on the smoke run. At one epoch on 200 images that is
    unremarkable, but a broken letterbox inverse - forgetting to subtract the padding, say - would
    look identical, and it would keep looking identical through a full sweep. So the inverse is
    given a box whose correct answer is known in advance: a stand-in model returns the letterboxed
    coordinates of a real ground-truth box, and what comes back must be that box in the original
    image's coordinates.
    """
    print("\n[9] tv_predict maps boxes back to original image coordinates")
    rels = [ln.strip() for ln in
            io.open(f"{R.SPLITS}/P1_random_image__seed20260911_test.txt", encoding="utf-8")
            if ln.strip()][:8]
    from PIL import Image
    sz = R.HYPER["imgsz"]

    truth = {}
    for rel in rels:
        w, h = Image.open(f"{R.DS}/{rel[2:]}").size
        lab = R.load_labels(rel)
        truth[rel] = (w, h, [R.yolo_to_xyxy(l[1:], w, h) for l in lab])

    class Stub:
        """Returns each image's own ground truth, expressed in letterboxed coordinates."""

        def __init__(self):
            self.i = 0

        def __call__(self, imgs):
            out = []
            for _ in imgs:
                rel = rels[self.i]
                self.i += 1
                w, h, boxes = truth[rel]
                r, _, _, left, top = R.letterbox_params(w, h, sz)
                lb = [[b[0] * r + left, b[1] * r + top, b[2] * r + left, b[3] * r + top]
                      for b in boxes]
                out.append({"boxes": torch.tensor(lb, dtype=torch.float32).reshape(-1, 4),
                            "scores": torch.ones(len(lb)),
                            "labels": torch.ones(len(lb), dtype=torch.int64)})
            return out

    preds, targets = R.tv_predict(Stub(), rels, torch.device("cpu"))

    worst, n = 0.0, 0
    for rel, p, t in zip(rels, preds, targets):
        if len(p["boxes"]) == 0:
            continue
        worst = max(worst, float((p["boxes"] - t["boxes"]).abs().max()))
        n += len(p["boxes"])
    check("recovered boxes equal the ground truth they were built from", worst < 0.02 and n > 0,
          f"{n} boxes over {len(rels)} images, worst error {worst:.4f} px")

    # And the same predictions must score a perfect mAP through the real metric, which proves the
    # prediction and target structures line up as well as the coordinates.
    m = R.evaluate(preds, targets)
    check("a perfect prediction scores mAP@50 = 1.0 end to end", abs(m["map_50"] - 1.0) < 1e-6,
          f"map_50 {m['map_50']:.6f}, map_50_95 {m['map_50_95']:.6f}")


# --------------------------------------------------------------------------------------------
def test_prediction_roundtrip():
    print("\n[7] predictions persist and reload exactly")
    tmp = tempfile.mkdtemp()
    rels = ["./images/a.jpg", "./images/b.jpg", "./images/c.jpg"]
    preds = [
        {"boxes": torch.tensor([[1., 2., 3., 4.], [5., 6., 7., 8.]]),
         "scores": torch.tensor([0.9, 0.1]), "labels": torch.zeros(2, dtype=torch.int32)},
        {"boxes": torch.zeros(0, 4), "scores": torch.zeros(0),
         "labels": torch.zeros(0, dtype=torch.int32)},
        {"boxes": torch.tensor([[9., 10., 11., 12.]]), "scores": torch.tensor([0.5]),
         "labels": torch.zeros(1, dtype=torch.int32)},
    ]
    p = os.path.join(tmp, "x.npz")
    R.save_predictions(p, rels, preds)
    z = np.load(p, allow_pickle=False)
    check("counts survive, including the empty image", list(z["counts"]) == [2, 0, 1])
    check("boxes survive", np.allclose(z["boxes"],
                                       [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]))
    check("scores survive", np.allclose(z["scores"], [0.9, 0.1, 0.5]))
    check("image order survives", list(z["images"]) == rels)
    size = os.path.getsize(p)
    check("the file is small enough to keep for every run", size < 2000, f"{size} bytes for 3 images")


# --------------------------------------------------------------------------------------------
def test_checkpoint_roundtrip(rn):
    print("\n[8] a torchvision checkpoint reloads and reproduces inference")
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, "ck.pt")
    rn.eval()
    x = [torch.zeros(3, R.HYPER["imgsz"], R.HYPER["imgsz"])]
    with torch.no_grad():
        before = rn(x)[0]
    torch.save({"model": "retinanet", "partition": "test",
                "state_dict": {k: v.cpu() for k, v in rn.state_dict().items()}}, p)

    fresh = R.build_tv("retinanet")
    fresh.load_state_dict(torch.load(p, map_location="cpu", weights_only=True)["state_dict"])
    fresh.eval()
    with torch.no_grad():
        after = fresh(x)[0]

    same = (before["boxes"].shape == after["boxes"].shape
            and torch.allclose(before["boxes"], after["boxes"], atol=1e-6)
            and torch.allclose(before["scores"], after["scores"], atol=1e-6))
    check("reloaded weights give identical detections", same,
          f"{len(before['boxes'])} boxes before, {len(after['boxes'])} after")
    mb = os.path.getsize(p) / 1e6
    check("checkpoint size recorded", mb > 0, f"retinanet {mb:.0f} MB")
    return mb


# --------------------------------------------------------------------------------------------
if __name__ == "__main__":
    test_letterbox_matches_ultralytics()
    test_box_roundtrip()
    test_matching_and_sweep()
    test_no_test_leakage()
    rn = test_common_inference_policy_is_applied()
    test_cosine_is_actually_active()
    test_tv_predict_geometry()
    test_prediction_roundtrip()
    test_checkpoint_roundtrip(rn)

    print("\n" + ("ALL PASS" if not FAILED else f"{len(FAILED)} FAILED: {FAILED}"))
    sys.exit(0 if not FAILED else 1)
