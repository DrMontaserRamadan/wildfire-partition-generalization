"""Freeze and hash the coding instrument before the 67-paper corpus is coded.

Everything that could influence a code is hashed here: the paper list, the codebook, the coder
brief, the excerpts, and the analysis plan that fixes the estimands and the threshold. After
this runs, any change to any of them is detectable, and any change made in response to results
is therefore visible rather than deniable.

Also writes the shard assignment. Both coders receive IDENTICAL shard boundaries, so every
paper is coded exactly once by an A-instance and once by a B-instance, and no A-instance ever
shares a context with the B-instance covering the same papers.
"""
import json
import io
import os
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

N_SHARDS = 4

INSTRUMENT = [
    "RUBRIC.md",
    "notes/CODER_BRIEF_67.md",
    "PRE_CODING_FREEZE.md",
    "corpus/to_code.json",
    "scripts/prep_coding.py",
    "corpus/scope_final.json",
]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    docs = json.load(io.open("corpus/to_code.json", encoding="utf-8"))
    ids = sorted(d["paper_id"] for d in docs)
    assert len(ids) == 67, f"expected 67 papers, found {len(ids)}"
    assert len(set(ids)) == 67, "duplicate paper ids"

    corpus_hash = hashlib.sha256("\n".join(ids).encode()).hexdigest()
    json.dump({"n": len(ids), "sha256": corpus_hash, "paper_ids": ids},
              io.open("corpus/frozen_corpus_67.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    # deterministic shards, balanced, ordered by a hash of the id so modality and publisher
    # do not cluster inside a shard
    order = sorted(ids, key=lambda p: hashlib.sha256(("shard:" + p).encode()).hexdigest())
    shards = {i: [] for i in range(N_SHARDS)}
    for k, pid in enumerate(order):
        shards[k % N_SHARDS].append(pid)

    by_id = {d["paper_id"]: d for d in docs}
    os.makedirs("corpus/shards", exist_ok=True)
    shard_meta = []
    for i in range(N_SHARDS):
        recs = [by_id[p] for p in shards[i]]
        path = f"corpus/shards/shard_{i}.json"
        json.dump(recs, io.open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        chars = sum(r["chars_excerpt"] for r in recs)
        shard_meta.append({"shard": i, "n": len(recs), "chars": chars,
                           "sha256": sha(path), "paper_ids": shards[i]})
        print(f"  shard {i}: {len(recs):2d} papers, {chars:7d} excerpt chars")

    manifest = {
        "frozen_for": "67-paper full-corpus coding",
        "corpus_sha256": corpus_hash,
        "n_papers": len(ids),
        "n_shards": N_SHARDS,
        "instrument": {p: sha(p) for p in INSTRUMENT},
        "shards": shard_meta,
        "reliability_threshold": 0.80,
        "threshold_unchanged_since": "round 1",
        "known_defects_not_repaired": [
            "P1: FLAME block does not specify what to code for non-FLAME papers",
            "P2: four free-text fields scored as categories; kappa not meaningful on them",
        ],
    }
    json.dump(manifest, io.open("corpus/INSTRUMENT_FREEZE.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    print(f"\nINSTRUMENT FROZEN")
    print(f"  corpus       : {len(ids)} papers, sha256 {corpus_hash[:16]}...")
    for p, h in manifest["instrument"].items():
        print(f"  {h[:16]}  {p}")
    print(f"\n  wrote corpus/INSTRUMENT_FREEZE.json and corpus/frozen_corpus_67.json")
    print(f"  shards under corpus/shards/ — identical boundaries for both coders")


if __name__ == "__main__":
    main()
