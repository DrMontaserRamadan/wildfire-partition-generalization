"""
Inter-rater agreement between two independent coders on the control set.

Reports, per field: raw percent agreement, Cohen's kappa, and the specific disagreements
so a third rater can adjudicate.

Interpretation rule fixed IN ADVANCE (must be stated in the manuscript):
  kappa >= 0.80  -> field is reliable, auto-code the full sample
  0.60-0.79      -> field needs a sharper definition, then re-test
  < 0.60         -> field is NOT auto-codable; hand-code it for the whole sample or drop it

Note on kappa with skewed marginals: when almost every paper gets the same code (e.g. nearly
all `not_reported`), kappa is depressed even at high raw agreement -- the well-known kappa
paradox. So we report BOTH, plus the marginal distribution, and judge a field on raw
agreement when one category exceeds 90% of codes. This is stated so it does not look like
post-hoc excuse-making.
"""
import argparse
import json, os, sys
from collections import Counter, defaultdict

A_PATH = "corpus/coded_A.json"
B_PATH = "corpus/coded_B.json"
OUT_PATH = "corpus/agreement.json"
RESTRICT = None


def load(p):
    if not os.path.exists(p):
        print(f"MISSING: {p}")
        return None
    d = json.load(open(p, encoding="utf-8"))
    return {r["paper_id"]: r for r in d}


def norm(v):
    if v is None:
        return "not_reported"
    if isinstance(v, list):
        return "|".join(sorted(str(x).lower().strip() for x in v))
    s = str(v).strip().lower()
    return s if s else "not_reported"


def kappa(pairs):
    """Cohen's kappa for two raters over a list of (a, b) code pairs."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    cats = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    if len(cats) < 2:
        return float("nan")  # undefined: single category
    po = sum(1 for a, b in pairs if a == b) / n
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    if abs(1 - pe) < 1e-12:
        return float("nan")
    return (po - pe) / (1 - pe)


def main():
    A, B = load(A_PATH), load(B_PATH)
    if A is None or B is None:
        sys.exit(1)
    ids = sorted(set(A) & set(B))
    if RESTRICT:
        keep = set(json.load(open(RESTRICT, encoding="utf-8")))
        before = len(ids)
        ids = [i for i in ids if i in keep]
        print(f"RESTRICTED to {RESTRICT}: {len(ids)} of {before} papers")
    print(f"Papers coded by both: {len(ids)}  (A={len(A)}, B={len(B)})")
    only_a, only_b = set(A) - set(B), set(B) - set(A)
    if only_a:
        print(f"  only in A: {sorted(only_a)}")
    if only_b:
        print(f"  only in B: {sorted(only_b)}")
    if not ids:
        sys.exit("no overlap")

    fields = []
    for i in ids:
        for k in list(A[i]) + list(B[i]):
            if k in ("paper_id", "coder_notes") or k.endswith("_quote"):
                continue
            if k not in fields:
                fields.append(k)

    rows, disagreements = [], defaultdict(list)
    for f in fields:
        pairs = []
        for i in ids:
            a, b = norm(A[i].get(f)), norm(B[i].get(f))
            pairs.append((a, b))
            if a != b:
                disagreements[f].append((i, a, b))
        raw = sum(1 for a, b in pairs if a == b) / len(pairs)
        k = kappa(pairs)
        marg = Counter(a for a, _ in pairs)
        top_share = marg.most_common(1)[0][1] / len(pairs)
        rows.append((f, raw, k, top_share, len(disagreements[f])))

    rows.sort(key=lambda r: (r[1], r[2] if r[2] == r[2] else -1))
    print(f"\n{'FIELD':38s} {'RAW':>6s} {'KAPPA':>7s} {'TOPSHR':>7s} {'DISAG':>6s}  VERDICT")
    print("-" * 92)
    reliable, needs_work, hand = [], [], []
    for f, raw, k, top, nd in rows:
        skewed = top >= 0.90
        if (k == k and k >= 0.80) or (skewed and raw >= 0.90):
            verdict = "AUTO-CODE" + (" (skewed, judged on raw)" if skewed and not (k == k and k >= 0.80) else "")
            reliable.append(f)
        elif (k == k and k >= 0.60) or raw >= 0.80:
            verdict = "SHARPEN DEFINITION, RETEST"
            needs_work.append(f)
        else:
            verdict = "HAND-CODE OR DROP"
            hand.append(f)
        ks = f"{k:7.3f}" if k == k else "    n/a"
        print(f"{f:38s} {raw:6.2f} {ks} {top:7.2f} {nd:6d}  {verdict}")

    print(f"\nSUMMARY: {len(reliable)} auto-codable, {len(needs_work)} need sharpening, "
          f"{len(hand)} must be hand-coded")

    print("\n" + "=" * 92)
    print("DISAGREEMENTS FOR ADJUDICATION (fields that are not auto-codable)")
    for f in needs_work + hand:
        if not disagreements[f]:
            continue
        print(f"\n  [{f}]")
        for i, a, b in disagreements[f]:
            print(f"     {i}:  A={a[:44]:44s}  B={b[:44]}")

    json.dump({"n": len(ids), "reliable": reliable, "needs_work": needs_work,
               "hand_code": hand,
               "table": [{"field": f, "raw": raw, "kappa": None if k != k else k,
                          "top_share": top, "n_disagree": nd}
                         for f, raw, k, top, nd in rows],
               "disagreements": {f: v for f, v in disagreements.items()}},
              open(OUT_PATH, "w"), indent=1)
    print(f"\nwrote {OUT_PATH}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--a", default=A_PATH, help="coder A file")
    ap.add_argument("--b", default=B_PATH, help="coder B file")
    ap.add_argument("--out", default=OUT_PATH, help="where to write the agreement report")
    ap.add_argument("--restrict", default=None,
                    help="JSON list of paper ids to restrict to. Use this to compare round 2 "
                         "against round 1 on the SAME papers: a category change tested on a "
                         "different sample is not a test of the category change.")
    args = ap.parse_args()
    A_PATH, B_PATH, OUT_PATH, RESTRICT = args.a, args.b, args.out, args.restrict
    main()
