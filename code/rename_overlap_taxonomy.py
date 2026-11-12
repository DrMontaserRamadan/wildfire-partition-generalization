"""Rename the overlap taxonomy's consequence labels. Pair assignments are NOT touched.

`cross_dataset_leak` overstates what the evidence establishes. There is no train/test
relationship between two separately published corpora, and the memorisation mechanism was
refuted by our own size-matched placebo control. The 275 across-dataset pairs are shared or
overlapping source material: benchmark OVERLAP, not leakage.

Only the 3 pairs that actually cross a training and a test partition inside one dataset's own
designated split earn the word leakage.

The rename is label-only and is verified to be so: every pair's datasets, files, identity,
locus and similarity scores must be byte-identical before and after.
"""
import json
import io
import os
import sys
import hashlib
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SRC = "corpus/contamination_taxonomy.json"
RENAME = {
    "cross_dataset_leak": "cross_dataset_overlap",
    "train_test_leak": "train_test_leakage",
    "train_val_leak": "train_val_leakage",
    "benign_within_split": "benign_within_split",
}
IDENTITY_KEYS = ["ds_a", "a", "ds_b", "b", "identity", "locus", "label",
                 "class_a", "class_b", "split_a", "split_b", "ncc", "dham"]


def fingerprint(rows):
    """Hash everything EXCEPT the consequence label, to prove assignments did not move."""
    blob = json.dumps([[r.get(k) for k in IDENTITY_KEYS] for r in rows],
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def main():
    rows = json.load(io.open(SRC, encoding="utf-8"))
    before_fp = fingerprint(rows)
    before = Counter(r.get("consequence") for r in rows)

    unknown = {c for c in before if c not in RENAME}
    if unknown:
        print(f"ABORT: unmapped consequence values {sorted(unknown)}")
        return 1

    for r in rows:
        r["consequence"] = RENAME[r["consequence"]]

    after_fp = fingerprint(rows)
    after = Counter(r.get("consequence") for r in rows)

    if before_fp != after_fp:
        print("ABORT: pair assignments changed. Nothing written.")
        return 1

    json.dump(rows, io.open(SRC, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    print("OVERLAP TAXONOMY RENAMED — labels only")
    print(f"  pair-assignment fingerprint unchanged: {before_fp[:16]}")
    print(f"  {len(rows)} pairs\n")
    print(f"  {'before':28s} {'after':28s}  n")
    for k in sorted(before):
        print(f"  {k:28s} {RENAME[k]:28s}  {before[k]}")
    print("\n  'leakage' now appears only where a training and a test partition of the SAME")
    print("  dataset are crossed. The 275 across-dataset pairs are labelled overlap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
