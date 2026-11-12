"""Merge the per-shard coder outputs into one immutable file per coder, and validate.

Fails loudly rather than silently producing a short corpus. Checks that every frozen paper id
appears exactly once per coder, that no shard leaked a paper belonging to another, and that
both coders cover an identical id set — otherwise agreement would be computed on a subset
without anyone noticing.
"""
import json
import io
import os
import sys
import hashlib
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

N_SHARDS = 4


def main():
    frozen = json.load(io.open("corpus/frozen_corpus_67.json", encoding="utf-8"))
    want = set(frozen["paper_ids"])
    shard_ids = {}
    for i in range(N_SHARDS):
        recs = json.load(io.open(f"corpus/shards/shard_{i}.json", encoding="utf-8"))
        shard_ids[i] = {r["paper_id"] for r in recs}

    problems, merged = [], {}
    for coder in ("A", "B"):
        allrecs = []
        for i in range(N_SHARDS):
            p = f"corpus/raw_coding/coded_{coder}_67_shard{i}.json"
            if not os.path.exists(p):
                problems.append(f"MISSING {p}")
                continue
            try:
                recs = json.load(io.open(p, encoding="utf-8"))
            except ValueError as e:
                problems.append(f"UNPARSEABLE {p}: {e}")
                continue
            got = {r["paper_id"] for r in recs}
            if got != shard_ids[i]:
                extra, miss = got - shard_ids[i], shard_ids[i] - got
                if extra:
                    problems.append(f"{p}: {len(extra)} papers not in shard {i}")
                if miss:
                    problems.append(f"{p}: missing {len(miss)} of shard {i}")
            allrecs.extend(recs)
        ids = [r["paper_id"] for r in allrecs]
        dup = [k for k, v in Counter(ids).items() if v > 1]
        if dup:
            problems.append(f"coder {coder}: {len(dup)} duplicate paper ids")
        if set(ids) != want:
            problems.append(f"coder {coder}: covers {len(set(ids))} of {len(want)} frozen ids")
        merged[coder] = sorted(allrecs, key=lambda r: r["paper_id"])

    if problems:
        print("MERGE FAILED:")
        for p in problems:
            print("  " + p)
        return 1

    for coder in ("A", "B"):
        out = f"corpus/raw_coding/coded_{coder}_67.RAW.json"
        json.dump(merged[coder], io.open(out, "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        h = hashlib.sha256(io.open(out, "rb").read()).hexdigest()
        print(f"  {h[:16]}  {len(merged[coder]):3d} records  {out}")

    print(f"\nboth coders cover all {len(want)} frozen papers, exactly once each.")
    print("These files are the evidentiary record. Do not edit them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
