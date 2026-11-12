"""Freeze the split-characteristics manifest before any training result is examined.

This is descriptive provenance, not analysis. For every replicate and fold of every protocol it
records what the partition actually contains, so that when a performance difference appears later
there is a contemporaneous record of how the composition differed — written before any score
existed, and therefore not shaped by one.

It also writes the split files themselves, one image path per line, which is what the training runs
consume. The manifest and the split files are hashed together: if a split file changes, the hash
moves and the change has to be justified.
"""
import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "scripts")

from pyrosdis_partitions import (SEEDS, assign_events, load_rows, split_grouped,  # noqa: E402
                                 split_partner_lopo, split_random, split_temporal)

OUT = "datasets/pyrosdis"
SPLITS = f"{OUT}/splits"

SPECS = [
    ("P1_random_image", split_random, None, SEEDS),
    ("P2_event_disjoint", split_grouped, "event", SEEDS),
    ("P3_camera_disjoint", split_grouped, "camera", SEEDS),
    ("P4_partner_lopo", split_partner_lopo, "partner", SEEDS[:3]),
    ("P5_temporal", split_temporal, None, SEEDS[:1]),
]


def characterise(rows, idx):
    rec = {}
    for arm in ("train", "val", "test"):
        sub = [rows[i] for i in idx[arm]]
        pos = sum(1 for r in sub if r["pos"])
        rec[arm] = {
            "images": len(sub),
            "positives": pos,
            "negatives": len(sub) - pos,
            "class_prevalence_pct": round(100 * pos / len(sub), 3),
            "boxes": sum(r["nbox"] for r in sub),
            "events": len({r["event"] for r in sub}),
            "cameras": len({r["camera"] for r in sub}),
            "partners": len({r["partner"] for r in sub}),
            "date_min": min(r["date"] for r in sub),
            "date_max": max(r["date"] for r in sub),
        }
    for axis in ("event", "camera", "partner"):
        tr = {rows[i][axis] for i in idx["train"]}
        va = {rows[i][axis] for i in idx["val"]}
        te = {rows[i][axis] for i in idx["test"]}
        rec[f"{axis}_crossings_train_test"] = len(tr & te)
        rec[f"{axis}_crossings_train_val"] = len(tr & va)
    rec["train_test_prevalence_diff_pp"] = round(
        rec["train"]["class_prevalence_pct"] - rec["test"]["class_prevalence_pct"], 3)
    return rec


def main():
    os.makedirs(SPLITS, exist_ok=True)
    rows = load_rows()
    n_ev = assign_events(rows)
    print(f"pooled {len(rows)} images, {n_ev} events")

    manifest = {"corpus": "pyronear/pyro-sdis", "n_pooled": len(rows), "n_events": n_ev,
                "event_gap_min": 30, "target": [0.70, 0.10, 0.20],
                "note": "descriptive provenance, frozen before any training result was examined",
                "partitions": {}}

    for name, fn, axis, seeds in SPECS:
        for s in seeds:
            idx = fn(rows, axis, s)
            if idx is None:
                continue
            key = f"{name}__seed{s}"
            manifest["partitions"][key] = characterise(rows, idx)
            for arm in ("train", "val", "test"):
                p = f"{SPLITS}/{key}_{arm}.txt"
                with io.open(p, "w", encoding="utf-8") as f:
                    for i in idx[arm]:
                        f.write(f"./images/{rows[i]['name']}\n")
            c = manifest["partitions"][key]
            print(f"  {key:34s} tr {c['train']['images']:6d} va {c['val']['images']:5d} "
                  f"te {c['test']['images']:6d} | prev diff "
                  f"{c['train_test_prevalence_diff_pp']:+7.3f}pp | ev-cross "
                  f"{c['event_crossings_train_test']:4d} cam-cross {c['camera_crossings_train_test']:3d}")

    # hash every split file so the manifest pins the exact partitions, not just their statistics
    h = hashlib.sha256()
    for fn_ in sorted(os.listdir(SPLITS)):
        h.update(io.open(f"{SPLITS}/{fn_}", "rb").read())
    manifest["split_files_sha256"] = h.hexdigest()
    manifest["n_split_files"] = len(os.listdir(SPLITS))

    json.dump(manifest, io.open("corpus/split_manifest.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    mh = hashlib.sha256(io.open("corpus/split_manifest.json", "rb").read()).hexdigest()
    print(f"\n  split files      {manifest['n_split_files']}")
    print(f"  split files hash {manifest['split_files_sha256'][:16]}")
    print(f"  manifest hash    {mh[:16]}")
    print("\nwrote corpus/split_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
