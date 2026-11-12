"""Extract Pyro-SDIS images and YOLO labels to disk.

The parquet shards carry the image bytes and the annotation string together. Training needs them
as files, laid out so that ultralytics can find a label by swapping /images/ for /labels/ in the
path. Everything lands in one flat pool; the partition protocols are expressed later as text files
listing image paths, so the same extracted pool serves every protocol and no image is ever
duplicated per split.

Label integrity is checked here rather than trusted: every annotation line must have five fields,
the four geometry values must lie in [0, 1], and the set of class indices actually present is
reported instead of assumed. The dataset is documented as single-class, but the first row read from
the hub begins with the token "1", so the real indices are counted and remapped to a contiguous
range starting at zero if they do not already start there.
"""
import io
import json
import os
import sys
from collections import Counter

import pyarrow.parquet as pq

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

OUT = "datasets/pyrosdis"
BASE = "https://huggingface.co/api/datasets/pyronear/pyro-sdis/parquet/default"
SHARDS = [(f"{BASE}/train/{i}.parquet", "train") for i in range(6)]
SHARDS += [(f"{BASE}/val/0.parquet", "val")]


def main():
    import fsspec
    os.makedirs(f"{OUT}/images", exist_ok=True)
    os.makedirs(f"{OUT}/labels", exist_ok=True)
    fs = fsspec.filesystem("http")

    classes = Counter()
    bad_geom, bad_fields, written, empty = 0, 0, 0, 0
    names = []

    for url, split in SHARDS:
        with fs.open(url, "rb") as fh:
            t = pq.read_table(fh, columns=["image", "image_name", "annotations"])
        d = t.to_pydict()
        for i in range(t.num_rows):
            name = d["image_name"][i]
            img = d["image"][i]
            blob = img["bytes"] if isinstance(img, dict) else img
            with open(f"{OUT}/images/{name}", "wb") as f:
                f.write(blob)

            lines = []
            for ln in (d["annotations"][i] or "").strip().split("\n"):
                ln = ln.strip()
                if not ln:
                    continue
                parts = ln.split()
                if len(parts) != 5:
                    bad_fields += 1
                    continue
                cls = int(float(parts[0]))
                vals = [float(x) for x in parts[1:]]
                if not all(0.0 <= v <= 1.0 for v in vals):
                    bad_geom += 1
                    continue
                classes[cls] += 1
                lines.append((cls, vals))

            if not lines:
                empty += 1
            stem = os.path.splitext(name)[0]
            with io.open(f"{OUT}/labels/{stem}.txt", "w", encoding="utf-8") as f:
                for cls, vals in lines:
                    f.write(f"{cls} " + " ".join(f"{v:.6f}" for v in vals) + "\n")
            names.append(name)
            written += 1
        print(f"  {split:5s} {url.rsplit('/',1)[-1]:12s} -> {written} images", flush=True)

    print(f"\nimages written      {written}")
    print(f"images with no box  {empty}")
    print(f"class indices seen  {dict(classes)}")
    print(f"malformed lines     fields={bad_fields} geometry={bad_geom}")

    # Remap only if the indices are not already a contiguous range from zero.
    seen = sorted(classes)
    if seen != list(range(len(seen))):
        print(f"\nclass indices {seen} are not contiguous from 0; remapping")
        remap = {c: i for i, c in enumerate(seen)}
        for name in names:
            p = f"{OUT}/labels/{os.path.splitext(name)[0]}.txt"
            txt = io.open(p, encoding="utf-8").read().strip()
            if not txt:
                continue
            out = []
            for ln in txt.split("\n"):
                parts = ln.split()
                out.append(f"{remap[int(parts[0])]} " + " ".join(parts[1:]))
            io.open(p, "w", encoding="utf-8").write("\n".join(out) + "\n")
        print(f"  remapped {remap}")
    else:
        remap = {c: c for c in seen}
        print("\nclass indices already contiguous from 0; no remap needed")

    json.dump({"n_images": written, "n_empty": empty,
               "class_counts": {str(k): v for k, v in classes.items()},
               "remap": {str(k): v for k, v in remap.items()},
               "malformed_fields": bad_fields, "malformed_geometry": bad_geom,
               "n_classes": len(seen)},
              io.open("corpus/pyrosdis_extract.json", "w", encoding="utf-8"), indent=1)
    print("wrote corpus/pyrosdis_extract.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
