"""Profile Pyro-SDIS grouping metadata without downloading the images.

The partition protocols for the granularity experiment may only be built from metadata that the
dataset actually ships, never from anything inferred from image content. This reads the parquet
shards column-wise over HTTP range requests, pulling the five metadata columns and skipping the
image bytes entirely, so the whole profile costs a few megabytes rather than 3.3 GB.

What the protocol needs from this, per candidate grouping axis: how many groups exist, how the
images are distributed across them, whether the axis is balanced enough to support disjoint folds,
and what the class prevalence looks like within each group. A grouping axis with three wildly
unbalanced levels cannot carry a leave-one-group-out analysis, and we would rather know that here
than after training.
"""
import io
import json
import os
import sys
from collections import Counter, defaultdict

import pyarrow.parquet as pq

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

BASE = "https://huggingface.co/api/datasets/pyronear/pyro-sdis/parquet/default"
SHARDS = [(f"{BASE}/train/{i}.parquet", "train") for i in range(6)] + [(f"{BASE}/val/0.parquet", "val")]
COLS = ["image_name", "partner", "camera", "date", "annotations"]


def main():
    import fsspec
    # pyarrow will not resolve an https:// URI itself, so hand it an fsspec file object; the
    # HTTP filesystem still serves byte ranges, which is what keeps this column read cheap.
    fs = fsspec.filesystem("http")

    rows = []
    for url, split in SHARDS:
        with fs.open(url, "rb") as fh:
            t = pq.read_table(fh, columns=COLS)
        d = t.to_pydict()
        for i in range(t.num_rows):
            rows.append({c: d[c][i] for c in COLS} | {"split": split})
        print(f"  read {split:5s} {url.rsplit('/',1)[-1]:12s} {t.num_rows:6d} rows", flush=True)

    print(f"\ntotal rows: {len(rows)}")
    tr = [r for r in rows if r["split"] == "train"]
    va = [r for r in rows if r["split"] == "val"]
    print(f"  official train {len(tr)}   official val {len(va)}")

    # An image with an empty annotation string carries no smoke box: that is the negative class.
    def npos(r):
        a = (r["annotations"] or "").strip()
        return 0 if not a else len([ln for ln in a.split("\n") if ln.strip()])

    for r in rows:
        r["nbox"] = npos(r)
        r["pos"] = r["nbox"] > 0

    print(f"  positives {sum(1 for r in rows if r['pos'])}  "
          f"negatives {sum(1 for r in rows if not r['pos'])}  "
          f"boxes {sum(r['nbox'] for r in rows)}")

    out = {"n": len(rows), "n_train": len(tr), "n_val": len(va),
           "n_pos": sum(1 for r in rows if r["pos"]),
           "n_boxes": sum(r["nbox"] for r in rows), "axes": {}}

    for axis in ("partner", "camera"):
        groups = defaultdict(list)
        for r in rows:
            groups[r[axis]].append(r)
        sizes = sorted(((k, len(v)) for k, v in groups.items()), key=lambda x: -x[1])
        print(f"\n{axis.upper()}: {len(groups)} distinct groups")
        print(f"  largest {sizes[0][1]}  smallest {sizes[-1][1]}  "
              f"median {sorted(s for _, s in sizes)[len(sizes)//2]}")
        share = 100 * sizes[0][1] / len(rows)
        print(f"  largest group holds {share:.1f}% of the corpus")
        for k, n in sizes[:12]:
            g = groups[k]
            p = 100 * sum(1 for r in g if r["pos"]) / len(g)
            xs = sorted({r["split"] for r in g})
            print(f"    {str(k)[:34]:34s} n={n:6d}  pos={p:5.1f}%  splits={','.join(xs)}")
        if len(sizes) > 12:
            print(f"    ... and {len(sizes)-12} more")
        out["axes"][axis] = {
            "n_groups": len(groups),
            "sizes": {str(k): n for k, n in sizes},
            "pos_rate": {str(k): round(100 * sum(1 for r in groups[k] if r["pos"]) / len(groups[k]), 2)
                         for k, _ in sizes},
            "largest_share_pct": round(share, 2),
        }

    # Does the official split already respect any grouping axis? If a camera appears on both
    # sides, the shipped split is not camera-disjoint, which is itself a reportable finding.
    print("\nDOES THE OFFICIAL SPLIT RESPECT ANY AXIS?")
    for axis in ("partner", "camera"):
        a = {r[axis] for r in tr}
        b = {r[axis] for r in va}
        both = a & b
        print(f"  {axis:8s} train={len(a):3d} val={len(b):3d} in BOTH={len(both):3d}"
              f"  -> {'NOT disjoint' if both else 'disjoint'}")
        out["axes"][axis]["official_split_disjoint"] = not both
        out["axes"][axis]["groups_in_both_official_splits"] = len(both)

    years = Counter(str(r["date"])[:4] for r in rows)
    months = Counter(str(r["date"])[:7] for r in rows)
    print(f"\nTEMPORAL: {len(months)} distinct months, range "
          f"{min(months)} .. {max(months)}")
    for y in sorted(years):
        print(f"    {y}  {years[y]:6d}")
    out["temporal"] = {"years": dict(years), "n_months": len(months),
                       "first": min(months), "last": max(months)}

    # camera-within-partner nesting: needed to know whether camera-disjoint and partner-disjoint
    # are genuinely different axes or whether one implies the other
    nest = defaultdict(set)
    for r in rows:
        nest[r["partner"]].add(r["camera"])
    print("\nNESTING (cameras per partner):")
    for p, cams in sorted(nest.items(), key=lambda x: -len(x[1])):
        print(f"    {str(p)[:24]:24s} {len(cams):3d} cameras")
    shared = [c for c in {r["camera"] for r in rows}
              if len({p for p, cs in nest.items() if c in cs}) > 1]
    print(f"  cameras appearing under more than one partner: {len(shared)}")
    out["nesting"] = {str(p): len(c) for p, c in nest.items()}
    out["cameras_under_multiple_partners"] = len(shared)

    json.dump(out, io.open("corpus/pyrosdis_profile.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nwrote corpus/pyrosdis_profile.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
