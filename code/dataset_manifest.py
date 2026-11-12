"""Hash every extracted Pyro-SDIS file, so the copy the sweep trains on can be proved identical to
the copy the design was frozen against.

There is a gap the existing gate does not cover. `deploy/runpod_setup.sh` rebuilds the partitions and
checks them against the frozen split hashes, but the partitions are derived from
`corpus/pyrosdis_rows.json` - cached metadata that travels with the repository. They are lists of
filenames. Nothing in that check ever looks at an image. The extractor pulls from
`https://huggingface.co/api/datasets/pyronear/pyro-sdis/parquet/default`, which is the hub's parquet
conversion endpoint with no revision pinned, so a re-extract can return different bytes under the
same filenames and every existing check would still pass.

That is the failure this file exists to catch: the same split, the same filenames, different pixels,
and a silent difference between the corpus the design was frozen on and the corpus the numbers come
from. It would not be visible in any result.

    python scripts/dataset_manifest.py              # write corpus/dataset_manifest.json
    python scripts/dataset_manifest.py --verify     # check this machine's copy against it
"""
import argparse
import hashlib
import io
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

DATA = "datasets/pyrosdis"
TREES = ["images", "labels", "splits"]
OUT = "corpus/dataset_manifest.json"


def sha256_file(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def walk():
    """Every file in the three trees, in a stable order, as (relative path, absolute path)."""
    for tree in TREES:
        d = os.path.join(DATA, tree)
        if not os.path.isdir(d):
            sys.exit(f"ABORT: {d} does not exist. Extract the corpus first "
                     f"(python scripts/pyrosdis_extract.py).")
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if os.path.isfile(p) and not name.endswith(".cache"):
                yield f"{tree}/{name}", p


def build():
    files, total = {}, 0
    t0 = time.time()
    items = list(walk())
    for i, (rel, p) in enumerate(items, 1):
        size = os.path.getsize(p)
        files[rel] = [sha256_file(p), size]
        total += size
        if i % 5000 == 0:
            print(f"  {i:,}/{len(items):,} files, {total/1e9:.2f} GB, "
                  f"{time.time()-t0:.0f}s", flush=True)

    # One hash over the whole listing, so a single value identifies the corpus. Ordered by path so
    # it does not depend on directory iteration order.
    roll = hashlib.sha256()
    for rel in sorted(files):
        roll.update(f"{rel} {files[rel][0]} {files[rel][1]}\n".encode())

    man = {"corpus": "pyronear/pyro-sdis",
           "source": "https://huggingface.co/api/datasets/pyronear/pyro-sdis/parquet/default",
           "source_is_revision_pinned": False,
           "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "n_files": len(files), "total_bytes": total,
           "rollup_sha256": roll.hexdigest(),
           "note": "per-file sha256 of the extracted corpus the frozen design was built on; "
                   "the hub endpoint above pins no revision, so a re-extract must be checked "
                   "against this rather than trusted",
           "files": files}
    json.dump(man, io.open(OUT, "w", encoding="utf-8"), indent=1, sort_keys=True)
    print(f"\nwrote {OUT}")
    print(f"  {len(files):,} files, {total/1e9:.2f} GB, rollup {man['rollup_sha256'][:16]}")
    print(f"  built in {time.time()-t0:.0f}s")
    return 0


def verify():
    if not os.path.exists(OUT):
        sys.exit(f"ABORT: {OUT} is missing. It must travel with the repository.")
    man = json.load(io.open(OUT, encoding="utf-8"))
    want = man["files"]
    here = dict(walk())

    missing = sorted(set(want) - set(here))
    extra = sorted(set(here) - set(want))
    changed = []
    t0 = time.time()
    for i, rel in enumerate(sorted(set(want) & set(here)), 1):
        p = here[rel]
        if os.path.getsize(p) != want[rel][1] or sha256_file(p) != want[rel][0]:
            changed.append(rel)
        if i % 5000 == 0:
            print(f"  {i:,} checked, {len(changed)} differing, {time.time()-t0:.0f}s", flush=True)

    print(f"\nchecked {len(want):,} files in {time.time()-t0:.0f}s")
    print(f"  missing from this machine : {len(missing)}")
    print(f"  present but not in manifest: {len(extra)}")
    print(f"  same name, different bytes : {len(changed)}")
    for label, lst in (("missing", missing), ("extra", extra), ("changed", changed)):
        for rel in lst[:10]:
            print(f"    {label}: {rel}")
        if len(lst) > 10:
            print(f"    ...and {len(lst)-10} more {label}")

    if missing or changed:
        sys.exit("\nABORT: this corpus is not the one the design was frozen on. Do NOT train.\n"
                 "  Same filenames with different bytes is the dangerous case: every split check\n"
                 "  would still pass, and the difference would not appear in any result.")
    if extra:
        print("\nExtra files are not fatal - nothing outside the split lists is ever read - but "
              "they mean this\n  copy was not produced the same way. Worth knowing why.")
    print("\nthis corpus matches the frozen one.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    raise SystemExit(verify() if a.verify else build())
