"""Measure the corpus properties that the common evaluation policy has to be chosen against.

Section 3 of the protocol fixes the partitions and section 6 the training budget, but nothing in the
frozen design says how a prediction becomes a detection. Three numbers have to be picked for all
four architectures - a score floor, an NMS IoU threshold and a cap on detections per image - and
picking them from habit, or from what suits one model, is exactly what the audit half of this paper
criticises other people for.

So they are chosen against the corpus instead. This script reports what is actually there:

  - how many annotated objects an image holds, which bounds how large the detection cap must be
    before it can truncate a correct answer;
  - how much annotated objects overlap each other, which bounds how aggressive NMS can be before it
    starts suppressing true positives rather than duplicates.

It reads only ground-truth labels. No model, no predictions, no results.
"""
import io
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

DS = "datasets/pyrosdis"
OUT = "corpus/eval_policy_evidence.json"


def iou(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    ua = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / ua if ua > 0 else 0.0


def main():
    per_image = Counter()
    pair_ious = []
    areas = []
    n_boxes = 0

    names = sorted(os.listdir(f"{DS}/labels"))
    for name in names:
        boxes = []
        for ln in io.open(f"{DS}/labels/{name}", encoding="utf-8"):
            p = ln.split()
            if len(p) == 5:
                cx, cy, bw, bh = (float(x) for x in p[1:])
                boxes.append([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2])
                areas.append(bw * bh)
        per_image[len(boxes)] += 1
        n_boxes += len(boxes)
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                pair_ious.append(iou(boxes[i], boxes[j]))

    n_img = sum(per_image.values())
    max_objs = max(per_image)
    pair_ious.sort()

    def pct(v, q):
        return v[min(len(v) - 1, int(q * len(v)))] if v else 0.0

    over = {t: sum(1 for x in pair_ious if x >= t) for t in (0.3, 0.5, 0.7)}

    rep = {
        "n_images": n_img,
        "n_boxes": n_boxes,
        "boxes_per_image": {str(k): v for k, v in sorted(per_image.items())},
        "mean_boxes_per_image": round(n_boxes / n_img, 3),
        "max_boxes_in_any_image": max_objs,
        "n_ground_truth_pairs_sharing_an_image": len(pair_ious),
        "gt_pair_iou": {
            "max": round(max(pair_ious), 4) if pair_ious else 0.0,
            "p99": round(pct(pair_ious, 0.99), 4),
            "p95": round(pct(pair_ious, 0.95), 4),
            "median": round(pct(pair_ious, 0.50), 4),
            "n_at_or_above": {str(t): n for t, n in over.items()},
        },
        "box_area_fraction_of_image": {
            "median": round(pct(sorted(areas), 0.50), 5),
            "p95": round(pct(sorted(areas), 0.95), 5),
            "max": round(max(areas), 5) if areas else 0.0,
        },
    }
    json.dump(rep, io.open(OUT, "w", encoding="utf-8"), indent=1)

    print(f"images                       {n_img:,}")
    print(f"annotated objects            {n_boxes:,}")
    print(f"mean objects per image       {rep['mean_boxes_per_image']}")
    print(f"most objects in any image    {max_objs}")
    print("objects per image, counts   ",
          {k: v for k, v in list(rep["boxes_per_image"].items())[:12]})
    print(f"\nground-truth pairs sharing an image   {len(pair_ious):,}")
    print(f"  their IoU  max {rep['gt_pair_iou']['max']}  p99 {rep['gt_pair_iou']['p99']}  "
          f"p95 {rep['gt_pair_iou']['p95']}  median {rep['gt_pair_iou']['median']}")
    print(f"  pairs at IoU >= 0.3 / 0.5 / 0.7 : "
          f"{over[0.3]:,} / {over[0.5]:,} / {over[0.7]:,}")
    print(f"\nbox area as a fraction of the image: median "
          f"{rep['box_area_fraction_of_image']['median']}, "
          f"p95 {rep['box_area_fraction_of_image']['p95']}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
