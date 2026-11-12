"""Compare the returned human coding against the frozen author coding.

Run this ONLY after both completed workbooks have been returned and hashed. It reads the
coders' files and nothing else; it has no generator, no default, no imputation and no sample
data, so it cannot be run on anything but real returned answers. If a workbook is missing or
incomplete it stops and says what is missing.

Order of operations, from HUMAN_CODING_PROTOCOL.md, and the reason it matters:

    A returns  ->  freeze and hash  ->  B returns  ->  freeze and hash  ->  this script
    ->  consensus round on the disagreements it lists  ->  only then compare against the
        validated classification

The pre-consensus codes are reported whatever they show. A code revisable after seeing the other
coder's answer is not an independent observation, so this script refuses to compute the
human-versus-human statistics if a consensus file is already present and either workbook has
been modified more recently than it.

Usage
    python scripts/compare_human_coding.py                 # A vs B, plus each against validated
    python scripts/compare_human_coding.py --consensus     # adds the consensus comparisons

Expected inputs, all produced by people, none by this script:
    human_coding/returned/workbook_coder_A.csv
    human_coding/returned/workbook_coder_B.csv
    human_coding/returned/consensus.csv        (only for --consensus)

Population correction, 2026-09-20, authorised by the corresponding author
-------------------------------------------------------------------------
This script was written on 2026-09-18, when the learned-model corpus held 64 papers, and it
hardcoded 64 in the row-count guard and the paper-set check. The corpus expanded to 79 on
2026-09-19 and the coder package was rebuilt at 79, which left both literals stale: the script
refused to run against workbooks that were themselves correct.

Two things were corrected, and nothing else:

  * the expected row count is now read from human_coding/MANIFEST.json rather than written here,
    so it cannot go stale a third time;
  * the inter-coder comparison runs on all 79 papers. The previous code intersected the two
    coders with the validated set and used that single set everywhere, which would have computed
    A-versus-B on 64 papers and silently dropped the 15 the coders also coded.

Comparisons against the validated author coding remain on 64 and are labelled with it. That
denominator is not a choice: the 15 papers added by hand retrieval never received a validated
author code and cannot be given one retrospectively.

No coding, no consensus handling and no statistic was otherwise changed.
"""
import argparse
import csv
import io
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

RET = "human_coding/returned"

# How many papers were sent to each coder. This was the literal 64 until 2026-09-20. The corpus
# expanded to 79 learned-model papers on 2026-09-19 and the coder package was rebuilt at 79, which
# left the literal stale and made this script refuse to run against correct workbooks. The
# package's own manifest is the authority on what was sent, so it is read rather than repeated.
N_PAPERS = json.load(io.open("human_coding/MANIFEST.json", encoding="utf-8"))["n_papers"]

CATS = [1, 2, 3, 4]
LABEL = {1: "mechanism reported", 2: "ratio or counts only",
         3: "no partition statement", 4: "unresolved"}
# Categories 2 and 3 form the numerator of the central estimand. The coders were never told this.
NUMERATOR_CATS = {2, 3}


def load_workbook(path, who):
    if not os.path.exists(path):
        sys.exit(f"MISSING: {path}\n"
                 f"  {who} has not returned a workbook, or it has not been placed in {RET}/.\n"
                 f"  This script does not proceed without it and does not substitute anything.")
    with io.open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != N_PAPERS:
        sys.exit(f"INCOMPLETE: {path} has {len(rows)} rows, expected {N_PAPERS}.")
    out, blank, bad = {}, [], []
    for r in rows:
        pid = (r.get("paper_identifier") or "").strip()
        raw = (r.get("category") or "").strip()
        if not raw:
            blank.append(pid)
            continue
        try:
            c = int(raw)
        except ValueError:
            bad.append((pid, raw))
            continue
        if c not in CATS:
            bad.append((pid, raw))
            continue
        out[pid] = c
    if blank or bad:
        msg = [f"INCOMPLETE: {path}"]
        if blank:
            msg.append(f"  {len(blank)} rows have no category: {', '.join(blank[:8])}"
                       + (" ..." if len(blank) > 8 else ""))
        if bad:
            msg.append(f"  {len(bad)} rows have a value outside 1-4: {bad[:8]}")
        msg.append("  A blank row may be deliberate — see the instruction sheet on unreadable")
        msg.append("  packets. Resolve it with the coder rather than filling it in here.")
        sys.exit("\n".join(msg))
    return out


def kappa(a, b, keys):
    """Cohen's kappa, reported beside raw agreement because skewed marginals separate them."""
    n = len(keys)
    obs = sum(1 for k in keys if a[k] == b[k]) / n
    ma, mb = Counter(a[k] for k in keys), Counter(b[k] for k in keys)
    exp = sum((ma[c] / n) * (mb[c] / n) for c in CATS)
    k = (obs - exp) / (1 - exp) if exp < 1 else float("nan")
    return obs, exp, k


def crosstab(a, b, keys):
    t = {r: {c: 0 for c in CATS} for r in CATS}
    for k in keys:
        t[a[k]][b[k]] += 1
    return t


def print_crosstab(t, rowname, colname):
    print(f"      {colname} ->")
    print("      " + "".join(f"{c:>6}" for c in CATS) + "   total")
    for r in CATS:
        tot = sum(t[r].values())
        print(f"   {r}  " + "".join(f"{t[r][c]:>6}" for c in CATS) + f"   {tot:>5}")
    print("  tot  " + "".join(f"{sum(t[r][c] for r in CATS):>6}" for c in CATS)
          + f"   {sum(sum(v.values()) for v in t.values()):>5}")
    print(f"      (rows: {rowname})")


def wilson(k, n, z=1.959963985):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (100 * (c - h), 100 * (c + h))


def prevalence(codes, keys, label):
    num = sum(1 for k in keys if codes[k] in NUMERATOR_CATS)
    lo, hi = wilson(num, len(keys))
    print(f"  {label:34s} {num}/{len(keys)} = {100*num/len(keys):.1f}%  "
          f"(95% CI {lo:.1f}-{hi:.1f})")
    return {"numerator": num, "denominator": len(keys),
            "pct": 100 * num / len(keys), "ci95": [lo, hi]}


def compare(name, a, b, keys, results, show_table=True):
    obs, exp, k = kappa(a, b, keys)
    print(f"\n{name}")
    print(f"  raw agreement {obs:.3f} ({sum(1 for x in keys if a[x]==b[x])}/{len(keys)})   "
          f"expected {exp:.3f}   Cohen's kappa {k:.3f}")
    if obs >= 0.80 and k < 0.60:
        print("  NOTE: high raw agreement with low kappa. The marginals are skewed; report both "
              "and state the reading explicitly rather than leaving it to the reader.")
    if show_table:
        print_crosstab(crosstab(a, b, keys), name.split(" vs ")[0], name.split(" vs ")[-1])
    results[name] = {"raw_agreement": obs, "expected": exp, "kappa": k,
                     "n": len(keys), "crosstab": crosstab(a, b, keys)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--consensus", action="store_true",
                    help="also compare the consensus codes; requires consensus.csv")
    args = ap.parse_args()

    A = load_workbook(os.path.join(RET, "workbook_coder_A.csv"), "Coder A")
    B = load_workbook(os.path.join(RET, "workbook_coder_B.csv"), "Coder B")

    cons_path = os.path.join(RET, "consensus.csv")
    if os.path.exists(cons_path) and not args.consensus:
        ct = os.path.getmtime(cons_path)
        for c in ("A", "B"):
            wb = os.path.join(RET, f"workbook_coder_{c}.csv")
            if os.path.getmtime(wb) > ct:
                sys.exit(f"REFUSING TO RUN: {wb} was modified after {cons_path} was written.\n"
                         "  Pre-consensus codes must be frozen before consensus. A code revised\n"
                         "  after seeing the other coder's answer is not an independent\n"
                         "  observation. Restore the frozen workbook from its hash.")

    val = json.load(io.open("corpus/fulltext_validation.json", encoding="utf-8"))
    V = {pid: rec["category"] for pid, rec in val["per_paper"].items()}

    # Two populations, deliberately kept apart rather than merged into one intersection.
    #
    # Until 2026-09-20 this script intersected the two coders WITH the validated set and used the
    # result for everything. That would now silently compute the inter-coder agreement on 64
    # papers and discard the 15 the coders also coded. Both coders coded the whole corpus, so the
    # inter-coder comparison runs on the whole corpus.
    #
    # The validated author coding exists for 64 papers only. The 15 added by hand retrieval never
    # received one and cannot be given one after the fact, so every comparison against the
    # validated classification is capped at 64 and is labelled with that denominator.
    ab_keys = sorted(set(A) & set(B))
    val_keys = sorted(set(A) & set(B) & set(V))
    if len(ab_keys) != N_PAPERS:
        sys.exit(f"Coder paper sets do not line up: A {len(A)}, B {len(B)}, "
                 f"common {len(ab_keys)}, expected {N_PAPERS}.")
    if len(val_keys) != len(V):
        sys.exit(f"The coders do not cover the validated set: validated {len(V)}, "
                 f"common {len(val_keys)}.")

    results = {}
    print("=" * 78)
    print("HUMAN DOUBLE-CODING — the pre-consensus comparison")
    print("=" * 78)
    print("Reported whatever it shows, per the protocol fixed before any paper was sent.")

    print(f"Inter-coder population: {len(ab_keys)} papers, the full corpus both coders received.")
    print(f"Validated-comparison population: {len(val_keys)} papers, those carrying an author "
          f"code.")
    results["populations"] = {"inter_coder": len(ab_keys), "vs_validated": len(val_keys)}

    compare(f"human A vs human B (n={len(ab_keys)})", A, B, ab_keys, results)

    print("\n" + "-" * 78)
    print("Category distributions")
    for nm, d, kk in (("human A", A, ab_keys), ("human B", B, ab_keys),
                      ("validated (authors)", V, val_keys)):
        c = Counter(d[k] for k in kk)
        print(f"  {nm:22s} (n={len(kk)})  " + "  ".join(f"{i}:{c[i]:>2}" for i in CATS))

    print("\n" + "-" * 78)
    print(f"Prevalence of the central estimand — categories 2 and 3, on the {len(val_keys)} "
          f"papers")
    print("that carry a validated author code, so the three are directly comparable.")
    results["prevalence"] = {
        "human_A": prevalence(A, val_keys, "human A"),
        "human_B": prevalence(B, val_keys, "human B"),
        "validated_authors": prevalence(V, val_keys, "validated (authors)"),
    }

    compare(f"human A vs validated (n={len(val_keys)})", A, V, val_keys, results,
            show_table=False)
    compare(f"human B vs validated (n={len(val_keys)})", B, V, val_keys, results,
            show_table=False)

    dis = [k for k in ab_keys if A[k] != B[k]]
    print("\n" + "-" * 78)
    print(f"Disagreements between the two coders: {len(dis)} of {len(ab_keys)}")
    for k in dis:
        print(f"  {k}   A={A[k]} ({LABEL[A[k]]})   B={B[k]} ({LABEL[B[k]]})")
    print("\nThese are the papers for the consensus round. Where the disagreements fall is the")
    print("evidence about what caused them: concentrated on one category boundary points at the")
    print("rubric, spread across differently-worded papers points at the source texts. Neither")
    print("reading is assumed.")
    results["ab_disagreements"] = dis

    if args.consensus:
        C = load_workbook(cons_path, "the consensus round")
        print("\n" + "=" * 78)
        print("CONSENSUS — the agreed coding of the full corpus")
        print("=" * 78)
        # The consensus coding covers all 79 papers, so its own distribution and prevalence are
        # reported on that population. Only the comparison against the validated author coding
        # is capped at 64, and it is labelled where it appears.
        cc = Counter(C[k] for k in ab_keys)
        print(f"  distribution (n={len(ab_keys)})  "
              + "  ".join(f"{i}:{cc[i]:>2}" for i in CATS))
        results["consensus_distribution"] = {str(i): cc[i] for i in CATS}
        print(f"\nPrevalence of the central estimand — categories 2 and 3, on all "
              f"{len(ab_keys)} papers")
        print("the coders received.")
        results["prevalence"]["consensus_79"] = prevalence(C, ab_keys, "human consensus")

        print("\n" + "-" * 78)
        print("CONSENSUS — compared against the validated classification")
        print("-" * 78)
        # Capped at the validated population for the same reason as above: the 15 hand-retrieved
        # papers carry no author code to compare a consensus against.
        compare(f"consensus vs validated (n={len(val_keys)})", C, V, val_keys, results)
        results["prevalence"]["consensus"] = prevalence(C, val_keys, "human consensus")
        cd = [k for k in val_keys if C[k] != V[k]]
        print(f"\n  consensus disagrees with the validated code on {len(cd)} of "
              f"{len(val_keys)}:")
        for k in cd:
            print(f"    {k}   consensus={C[k]} ({LABEL[C[k]]})   "
                  f"validated={V[k]} ({LABEL[V[k]]})")
        results["consensus_vs_validated_disagreements"] = cd

        hp = results["prevalence"]["consensus"]["pct"]
        vp = results["prevalence"]["validated_authors"]["pct"]
        print(f"\n  human consensus {hp:.1f}%  against validated {vp:.1f}%  "
              f"difference {hp-vp:+.1f} points")
        if abs(hp - vp) > 10:
            print("\n  *** The difference exceeds the 10-point threshold fixed in advance. ***")
            print("  Per HUMAN_CODING_PROTOCOL.md the HUMAN figure governs and the manuscript's")
            print("  headline changes. The model-derived figure is not protected.")
        else:
            print("\n  Within the 10-point threshold fixed in advance. The validated figure")
            print("  stands as the headline, and the human result is reported beside it.")

    out = "corpus/human_coding_results.json"
    json.dump(results, io.open(out, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
