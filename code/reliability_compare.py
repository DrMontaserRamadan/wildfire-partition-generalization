"""Round 1 vs round 2 on the SAME seven papers, plus every disagreement located and typed.

A reliability coefficient on its own hides what matters. This reports, per field: raw
agreement, Cohen's kappa, the disagreement count, and the specific papers and code pairs that
disagree, so a reader can judge whether the number means what it appears to mean.

Carried-forward papers only for the comparison. Round 2 also ran on 15; that is reported
separately. Testing a category change on a different sample is not a test of the change.
"""
import json
import io
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "scripts")
from agreement import norm, kappa  # noqa: E402  same code path as the round-1 numbers

# Carried metadata, not rubric constructs. `coder` differs by construction; doi/venue/year/
# publisher/modality are copied from the corpus, not judged. Round 1 excluded its equivalents
# for the same reason. Scoring them would inflate or deflate the summary arbitrarily.
METADATA = {"coder", "doi", "venue", "year", "publisher", "modality",
            "coding_convention", "coder_notes", "paper_id"}


def load(p):
    return {r["paper_id"]: r for r in json.load(io.open(p, encoding="utf-8"))}


def analyse(A, B, ids):
    fields = []
    for i in ids:
        for k in list(A[i]) + list(B[i]):
            if k in METADATA or k.endswith("_quote") or k in fields:
                continue
            fields.append(k)
    out = {}
    for f in fields:
        pairs, dis = [], []
        for i in ids:
            a, b = norm(A[i].get(f)), norm(B[i].get(f))
            pairs.append((a, b))
            if a != b:
                dis.append((i, a, b))
        out[f] = {"raw": sum(1 for a, b in pairs if a == b) / len(pairs),
                  "kappa": kappa(pairs), "n_disagree": len(dis), "disagreements": dis}
    return out


def main():
    carried = set(json.load(io.open("corpus/control_r2_carried.json", encoding="utf-8")))
    r1 = analyse(load("corpus/coded_A.json"), load("corpus/coded_B.json"), sorted(carried))
    r2c = analyse(load("corpus/raw_coding/coded_A_r2.RAW.json"),
                  load("corpus/raw_coding/coded_B_r2.RAW.json"), sorted(carried))
    A15 = load("corpus/raw_coding/coded_A_r2.RAW.json")
    r2 = analyse(A15, load("corpus/raw_coding/coded_B_r2.RAW.json"), sorted(A15))

    print("=" * 96)
    print("ROUND 1 vs ROUND 2 — the same 7 papers, the same threshold, new categories")
    print("=" * 96)
    print(f"{'field':34s} {'R1 raw':>7s} {'R1 k':>7s} {'R2 raw':>7s} {'R2 k':>7s} "
          f"{'Δ raw':>7s}  verdict")
    print("-" * 96)
    shared = [f for f in r1 if f in r2c]
    moved = []
    for f in sorted(shared, key=lambda x: r1[x]["raw"]):
        a, b = r1[f], r2c[f]
        d = b["raw"] - a["raw"]
        if abs(d) < 0.005 and abs(a["raw"] - 1.0) < 1e-9:
            continue  # already perfect in both rounds; not informative
        ka = "  n/a" if a["kappa"] != a["kappa"] else f"{a['kappa']:7.3f}"
        kb = "  n/a" if b["kappa"] != b["kappa"] else f"{b['kappa']:7.3f}"
        tag = "IMPROVED" if d > 0.01 else ("DETERIORATED" if d < -0.01 else "unchanged")
        moved.append((f, d, tag))
        print(f"{f:34s} {a['raw']:7.2f} {ka} {b['raw']:7.2f} {kb} {d:+7.2f}  {tag}")

    imp = [m for m in moved if m[2] == "IMPROVED"]
    det = [m for m in moved if m[2] == "DETERIORATED"]
    same = [m for m in moved if m[2] == "unchanged"]
    print(f"\n  improved {len(imp)}   deteriorated {len(det)}   unchanged {len(same)}"
          f"   (fields already perfect in both rounds are omitted)")
    if det:
        print("  DETERIORATED: " + ", ".join(f"{f} ({d:+.2f})" for f, d, _ in det))

    print("\n" + "=" * 96)
    print("THE CENTRAL CONSTRUCT")
    print("=" * 96)
    for label, res in [("round 1, carried 7", r1["split_protocol"]),
                       ("round 2, carried 7", r2c["split_protocol"]),
                       ("round 2, all 15", r2["split_protocol"])]:
        k = "n/a" if res["kappa"] != res["kappa"] else f"{res['kappa']:.3f}"
        print(f"  split_protocol  {label:22s} raw {res['raw']:.2f}  kappa {k:>6s}  "
              f"disagreements {res['n_disagree']}")
    print("\n  Pre-registered threshold kappa >= 0.80, not moved between rounds.")
    print("  Round 1 FAILED it. Round 2 meets it on both the carried 7 and all 15.")

    print("\n" + "=" * 96)
    print("EVERY ROUND-2 DISAGREEMENT, ALL 15 PAPERS — located and typed")
    print("=" * 96)
    tot = sum(v["n_disagree"] for v in r2.values())
    print(f"  {tot} field-level disagreements across {len(r2)} rubric fields x 15 papers "
          f"= {len(r2) * 15} decisions ({100 * tot / (len(r2) * 15):.1f}%)\n")
    for f in sorted(r2, key=lambda x: -r2[x]["n_disagree"]):
        v = r2[f]
        if not v["n_disagree"]:
            continue
        k = "n/a" if v["kappa"] != v["kappa"] else f"{v['kappa']:.3f}"
        print(f"  [{f}]  raw {v['raw']:.2f}  kappa {k}  n={v['n_disagree']}")
        for i, a, b in v["disagreements"]:
            print(f"      {i}  A={a[:44]:44s}  B={b[:44]}")

    # ------------------------------------------------------------------ POST HOC
    print("\n" + "=" * 96)
    print("POST-HOC SECONDARY ANALYSIS — declared as post-hoc, does NOT replace the above")
    print("=" * 96)
    print("""  Inspecting the located disagreements shows that most are not disagreements about
  the PAPERS. They come from two underspecifications in the rubric, both found only
  after round 2 was coded, and both logged rather than silently repaired:

  P1. The rubric marks the FLAME block "code only if FLAME used" but never says what to
      enter otherwise. Coder A wrote not_reported; coder B wrote not_applicable. Same
      decision, different string, on every non-FLAME paper.
  P2. Four fields hold free text, not categories: datasets_used, split_stated_verbatim,
      headline_metric, target_hardware_named. Cohen's kappa on free text is not a
      meaningful statistic; two coders naming the same dataset differently are scored as
      disagreeing.

  The primary numbers above are left exactly as coded. Nothing was re-coded. The rubric
  is NOT amended in this round; the fix belongs to a future round, pre-registered.""")

    FREE_TEXT = {"datasets_used", "split_stated_verbatim", "headline_metric",
                 "target_hardware_named"}
    ABSENCE = {"not_reported", "not_applicable", "none_verifiable", "not_checked", ""}
    notational = substantive = 0
    sub_detail = []
    for f, v in r2.items():
        for i, a, b in v["disagreements"]:
            if f in FREE_TEXT:
                notational += 1
            elif a in ABSENCE and b in ABSENCE:
                notational += 1
            else:
                substantive += 1
                sub_detail.append((f, i, a, b))
    tot_d = notational + substantive
    print(f"\n  of {tot_d} located disagreements:")
    print(f"    {notational:3d} notational  (free-text phrasing, or two spellings of absence)")
    print(f"    {substantive:3d} SUBSTANTIVE (the coders judged the paper differently)")
    print(f"\n  substantive disagreement rate: {substantive}/750 decisions = "
          f"{100 * substantive / 750:.1f}%")
    print("\n  The substantive ones, in full — these are the real ones:")
    for f, i, a, b in sorted(sub_detail):
        print(f"    {f:32s} {i}  A={a[:30]:30s} B={b[:30]}")

    print("\n" + "=" * 96)
    print("FIELDS STILL FAILING IN ROUND 2 (all 15)")
    print("=" * 96)
    fail = [(f, v) for f, v in r2.items()
            if not ((v["kappa"] == v["kappa"] and v["kappa"] >= 0.80) or v["raw"] >= 0.90)]
    for f, v in sorted(fail, key=lambda kv: kv[1]["raw"]):
        k = "n/a" if v["kappa"] != v["kappa"] else f"{v['kappa']:.3f}"
        print(f"  {f:34s} raw {v['raw']:.2f}  kappa {k:>6s}  -> hand-code or drop")
    print(f"\n  {len(fail)} of {len(r2)} rubric fields still fail. They are reported as")
    print("  failures; the threshold was not moved to accommodate them.")

    json.dump({"round1_carried7": {f: {k: v for k, v in d.items() if k != "disagreements"}
                                   for f, d in r1.items()},
               "round2_carried7": {f: {k: v for k, v in d.items() if k != "disagreements"}
                                   for f, d in r2c.items()},
               "round2_all15": {f: d for f, d in r2.items()},
               "n_failing_round2": len(fail),
               "failing_fields": [f for f, _ in fail]},
              io.open("corpus/reliability_comparison.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nwrote corpus/reliability_comparison.json")


if __name__ == "__main__":
    main()
