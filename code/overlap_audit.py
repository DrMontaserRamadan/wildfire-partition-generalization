"""
Cross-dataset near-duplicate audit for fire/smoke detection benchmarks.

Method (must be reported verbatim in the manuscript):
  - Every image is converted to 8-bit greyscale.
  - dHash-64: resize to 9x8 (Lanczos), bit i = (px[r,c] > px[r,c+1]), row-major, 64 bits.
  - pHash-64: resize to 32x32, 2-D DCT-II, take the top-left 8x8 block excluding the DC
    term, bit i = (coef_i > median(coefs)), 64 bits.
  - Candidate pair: Hamming distance <= HAMMING_MAX on EITHER hash.
  - Confirmation gate: normalised cross-correlation (NCC) on 32x32 greyscale, mean-centred,
    >= NCC_MIN. A candidate that fails the gate is NOT counted as a duplicate.
  - Exact duplicates are additionally reported via SHA-256 of the raw file bytes.

The NCC gate exists because perceptual hashes alone produce false pairs on low-texture
images (e.g. near-black frames, uniform sky). Reporting hash-only numbers without a
confirmation gate would repeat the very sloppiness this paper audits.

Defaults follow Ruangsang & Pramkeaw (Drones 2026, doi:10.3390/drones10080635) so our
numbers are comparable with theirs: 64-bit hash, Hamming <= 5.
"""
import os, sys, json, hashlib, math
from collections import defaultdict
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

HAMMING_MAX = 5
NCC_MIN = 0.95
EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


def dct2(a):
    """2-D DCT-II via matrix multiply (no scipy dependency for reproducibility)."""
    n = a.shape[0]
    k = np.arange(n)
    M = np.cos(np.pi * (2 * k[:, None] + 1) * k[None, :] / (2 * n))
    M[:, 0] *= 1 / math.sqrt(2)
    return M.T @ a @ M


def hashes(path):
    """Return (dhash_uint64, phash_uint64, ncc_vector_32x32, sha256) or None."""
    try:
        im = Image.open(path)
        im.draft("L", (64, 64))
        g = im.convert("L")
    except Exception:
        return None
    try:
        a9 = np.asarray(g.resize((9, 8), Image.LANCZOS), dtype=np.int16)
        dbits = (a9[:, 1:] > a9[:, :-1]).flatten()
        d = np.packbits(dbits).tobytes()
        dh = int.from_bytes(d, "big")

        a32 = np.asarray(g.resize((32, 32), Image.LANCZOS), dtype=np.float64)
        c = dct2(a32)[:8, :8].flatten()
        c = c[1:]  # drop DC
        pbits = c > np.median(c)
        pbits = np.append(pbits, False)  # pad to 64
        ph = int.from_bytes(np.packbits(pbits).tobytes(), "big")

        v = a32 - a32.mean()
        nrm = np.linalg.norm(v)
        vec = (v / nrm).flatten() if nrm > 1e-9 else np.zeros(1024)
    except Exception:
        return None
    try:
        sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    except Exception:
        sha = ""
    return dh, ph, vec.astype(np.float32), sha


def popcount(x):
    return bin(x).count("1")


def index_dir(root, name):
    recs = []
    for dp, _, fs in os.walk(root):
        for f in fs:
            if os.path.splitext(f)[1].lower() not in EXTS:
                continue
            p = os.path.join(dp, f)
            h = hashes(p)
            if h is None:
                continue
            rel = os.path.relpath(p, root).replace("\\", "/")
            recs.append({"ds": name, "rel": rel, "dh": h[0], "ph": h[1],
                         "vec": h[2], "sha": h[3]})
    print(f"  indexed {name}: {len(recs)} images", flush=True)
    return recs


def band_buckets(recs, key, nbands=8):
    """LSH-style banding so we don't do O(n^2) comparisons across large sets."""
    buckets = defaultdict(list)
    for i, r in enumerate(recs):
        v = r[key]
        for b in range(nbands):
            seg = (v >> (8 * b)) & 0xFF
            buckets[(b, seg)].append(i)
    return buckets


def compare(A, B, label):
    """Return confirmed duplicate pairs between two record lists."""
    cand = set()
    for key in ("dh", "ph"):
        bb = band_buckets(B, key)
        for i, ra in enumerate(A):
            v = ra[key]
            seen = set()
            for b in range(8):
                seg = (v >> (8 * b)) & 0xFF
                for j in bb.get((b, seg), ()):
                    seen.add(j)
            for j in seen:
                if popcount(ra[key] ^ B[j][key]) <= HAMMING_MAX:
                    cand.add((i, j))
    confirmed, exact = [], 0
    for i, j in cand:
        ncc = float(np.dot(A[i]["vec"], B[j]["vec"]))
        if ncc >= NCC_MIN:
            is_exact = bool(A[i]["sha"]) and A[i]["sha"] == B[j]["sha"]
            exact += is_exact
            confirmed.append({"a": A[i]["rel"], "b": B[j]["rel"],
                              "ncc": round(ncc, 4),
                              "dham": popcount(A[i]["dh"] ^ B[j]["dh"]),
                              "pham": popcount(A[i]["ph"] ^ B[j]["ph"]),
                              "exact": is_exact})
    a_hit = len({c["a"] for c in confirmed})
    b_hit = len({c["b"] for c in confirmed})
    print(f"  {label}: {len(cand)} candidates -> {len(confirmed)} confirmed "
          f"({exact} byte-exact); {a_hit}/{len(A)} of A and {b_hit}/{len(B)} of B involved",
          flush=True)
    return {"pairs": confirmed, "n_a": len(A), "n_b": len(B),
            "a_hit": a_hit, "b_hit": b_hit, "exact": exact,
            "candidates": len(cand)}


def internal(recs, label):
    """Duplicates WITHIN one dataset (and across its own splits)."""
    res = compare(recs, recs, label + " [internal]")
    res["pairs"] = [p for p in res["pairs"] if p["a"] != p["b"]]
    return res


if __name__ == "__main__":
    roots = json.load(open(sys.argv[1], encoding="utf-8"))  # {name: path}
    idx = {}
    print("INDEXING", flush=True)
    for name, path in roots.items():
        if not os.path.isdir(path):
            print(f"  SKIP {name}: {path} missing", flush=True)
            continue
        idx[name] = index_dir(path, name)
    out = {"params": {"hamming_max": HAMMING_MAX, "ncc_min": NCC_MIN,
                      "hash_bits": 64, "hashes": ["dhash", "phash"]},
           "sizes": {k: len(v) for k, v in idx.items()},
           "cross": {}, "internal": {}}
    names = sorted(idx)
    print("\nINTERNAL", flush=True)
    for n in names:
        out["internal"][n] = internal(idx[n], n)
    print("\nCROSS-DATASET", flush=True)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            out["cross"][f"{a}|{b}"] = compare(idx[a], idx[b], f"{a} vs {b}")
    # strip bulky pair lists into a side file
    pairs = {"cross": {k: v.pop("pairs") for k, v in out["cross"].items()},
             "internal": {k: v.pop("pairs") for k, v in out["internal"].items()}}
    json.dump(out, open("corpus/overlap_summary.json", "w"), indent=1)
    json.dump(pairs, open("corpus/overlap_pairs.json", "w"), indent=1)
    print("\nwrote corpus/overlap_summary.json and corpus/overlap_pairs.json")
