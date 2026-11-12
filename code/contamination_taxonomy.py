"""
Contamination TAXONOMY — characterise the overlap, do not just count it.

Consumes corpus/overlap_summary.json and corpus/overlap_pairs.json (from overlap_audit.py)
and classifies every confirmed duplicate pair along five orthogonal axes:

  1. IDENTITY      exact_bytes | exact_pixels | near_duplicate
                   (exact_pixels = decoded arrays identical but file bytes differ, i.e. the
                    same image re-encoded; this is the dominant class and is invisible to any
                    byte-level dedup such as "Total Commander", which is what FASDD used)
  2. LOCUS         within_split | across_split_same_dataset | across_dataset
  3. LABEL         same_label | conflicting_label | label_unknown
  4. CLASS         which class(es) the pair sits in -> class-specific contamination rates
  5. CONSEQUENCE   train_test_leak | train_val_leak | cross_dataset_leak | benign_within_train

Also computes EFFECTIVE TEST SET SIZE: the number of distinct visual items in a test split
after collapsing duplicate groups. A test set of N images containing D duplicate groups
measures fewer than N independent things, which inflates apparent precision of the estimate.
"""
import json, os, sys, hashlib
from collections import defaultdict, Counter
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
Image.MAX_IMAGE_PIXELS = None

ROOTS = json.load(open("corpus/ds_roots.json", encoding="utf-8"))


def label_of(ds, rel):
    """Class label from the path convention of each dataset."""
    parts = rel.split("/")
    if ds == "DeepQuestAI_FireSmoke":          # Train|Test / Fire|Smoke|Neutral / x.jpg
        return parts[1] if len(parts) > 1 else "?"
    if ds == "DeepQuestAI_inference":          # fire|smoke|neutral / x.jpg
        return parts[0] if parts else "?"
    if ds == "FireNET":                        # train|validation / images / x.jpg
        return "fire"                          # verified: all 701 boxes are class 'fire'
    return "?"


def split_of(ds, rel):
    parts = rel.split("/")
    if ds.startswith("DeepQuestAI_FireSmoke"):
        return parts[0].lower()                # train | test
    if ds == "FireNET":
        return parts[0].lower()                # train | validation
    return "single"


def pixel_sig(path):
    try:
        a = np.asarray(Image.open(path).convert("RGB"))
        return hashlib.sha256(a.tobytes()).hexdigest()
    except Exception:
        return None


def main():
    S = json.load(open("corpus/overlap_summary.json", encoding="utf-8"))
    P = json.load(open("corpus/overlap_pairs.json", encoding="utf-8"))

    pixcache = {}

    def pix(ds, rel):
        k = (ds, rel)
        if k not in pixcache:
            pixcache[k] = pixel_sig(os.path.join(ROOTS[ds], rel))
        return pixcache[k]

    rows = []

    def add(ds_a, a, ds_b, b, rec, locus):
        pa, pb = pix(ds_a, a), pix(ds_b, b)
        if rec.get("exact"):
            identity = "exact_bytes"
        elif pa and pb and pa == pb:
            identity = "exact_pixels"
        else:
            identity = "near_duplicate"
        la, lb = label_of(ds_a, a), label_of(ds_b, b)
        # normalise case and dataset-specific synonyms before comparing.
        # DeepQuestAI uses Fire/Smoke/Neutral; FireNET uses lowercase 'fire'.
        # Treating 'Fire' and 'fire' as a conflict would be a false positive.
        NORM = {"neutral": "nofire", "normal": "nofire", "no_fire": "nofire"}
        na, nb = la.strip().lower(), lb.strip().lower()
        na, nb = NORM.get(na, na), NORM.get(nb, nb)
        if la == "?" or lb == "?":
            lab = "label_unknown"
        elif na == nb:
            lab = "same_label"
        else:
            lab = "conflicting_label"
        sa, sb = split_of(ds_a, a), split_of(ds_b, b)
        if locus == "across_dataset":
            cons = "cross_dataset_overlap"
        elif sa == sb:
            cons = "benign_within_split"
        elif {sa, sb} & {"test"}:
            cons = "train_test_leakage"
        else:
            cons = "train_val_leakage"
        rows.append({"ds_a": ds_a, "a": a, "ds_b": ds_b, "b": b, "identity": identity,
                     "locus": locus, "label": lab, "class_a": la, "class_b": lb,
                     "split_a": sa, "split_b": sb, "consequence": cons,
                     "ncc": rec.get("ncc"), "dham": rec.get("dham")})

    for k, pairs in P["internal"].items():
        seen = set()
        for rec in pairs:
            a, b = rec["a"], rec["b"]
            if a == b:
                continue
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            sa, sb = split_of(k, a), split_of(k, b)
            add(k, a, k, b, rec, "within_split" if sa == sb else "across_split_same_dataset")

    for k, pairs in P["cross"].items():
        ds_a, ds_b = k.split("|")
        for rec in pairs:
            add(ds_a, rec["a"], ds_b, rec["b"], rec, "across_dataset")

    print(f"CONFIRMED DUPLICATE PAIRS CLASSIFIED: {len(rows)}\n")
    for axis in ("identity", "locus", "label", "consequence"):
        print(f"BY {axis.upper()}:")
        for k, v in Counter(r[axis] for r in rows).most_common():
            print(f"   {v:5d}  {k}")
        print()

    print("CONFLICTING-LABEL PAIRS (the evaluation-noise cases):")
    conf = [r for r in rows if r["label"] == "conflicting_label"]
    if not conf:
        print("   none")
    for r in conf[:20]:
        print(f"   [{r['identity']}] {r['ds_a']}:{r['a']} ({r['class_a']})"
              f"  <->  {r['ds_b']}:{r['b']} ({r['class_b']})")
    print()

    print("CLASS-SPECIFIC CONTAMINATION (cross-dataset pairs by class):")
    cd = [r for r in rows if r["locus"] == "across_dataset"]
    for k, v in Counter(f"{r['class_a']} <-> {r['class_b']}" for r in cd).most_common():
        print(f"   {v:5d}  {k}")
    print()

    print("EFFECTIVE TEST-SET SIZE (distinct visual items after collapsing duplicates):")
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for r in rows:
        union((r["ds_a"], r["a"]), (r["ds_b"], r["b"]))
    for ds, root in ROOTS.items():
        if not os.path.isdir(root):
            continue
        for split in ("test", "validation"):
            members = []
            for dp, _, fs in os.walk(root):
                for f in fs:
                    if os.path.splitext(f)[1].lower() not in (".jpg", ".jpeg", ".png", ".bmp"):
                        continue
                    rel = os.path.relpath(os.path.join(dp, f), root).replace("\\", "/")
                    if split_of(ds, rel) == split:
                        members.append((ds, rel))
            if not members:
                continue
            groups = {find(m) for m in members}
            print(f"   {ds}/{split}: {len(members)} images -> {len(groups)} distinct items "
                  f"({100*(1-len(groups)/len(members)):.1f}% redundant)")

    # SCOPE, made explicit after a provenance error. `DFire_test` was added to ds_roots.json in
    # freeze event 2 purely as a CROSS-DATASET specificity control, where it contributes zero
    # pairs. Letting it into the WITHIN-split pass as well pulls in ~13,151 of its own internal
    # near-duplicates and silently turns a 369-pair taxonomy into a 13,520-pair one — which is a
    # different question (within-dataset redundancy, already reported by DetectiumFire 2025) and
    # is not what any downstream number in this project refers to.
    #
    # The taxonomy therefore covers pairs among the FireNET / DeepQuestAI corpora. D-Fire's
    # internal redundancy is counted and reported separately, never folded in.
    WITHIN_SPLIT_EXCLUDED = {"DFire_test"}
    dfire_internal = sum(1 for r in rows
                         if r["ds_a"] in WITHIN_SPLIT_EXCLUDED
                         or r["ds_b"] in WITHIN_SPLIT_EXCLUDED)
    rows = [r for r in rows
            if r["ds_a"] not in WITHIN_SPLIT_EXCLUDED
            and r["ds_b"] not in WITHIN_SPLIT_EXCLUDED]
    print(f"\nSCOPE: {len(rows)} pairs among FireNET/DeepQuestAI corpora.")
    print(f"       {dfire_internal} pairs touching DFire_test excluded from this taxonomy "
          f"(it is a cross-dataset specificity control and contributes 0 across-dataset pairs;"
          f" its internal redundancy is a separate question).")

    json.dump(rows, open("corpus/contamination_taxonomy.json", "w"), indent=1)
    print("\nwrote corpus/contamination_taxonomy.json")


if __name__ == "__main__":
    main()
