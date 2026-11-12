#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the reconciliation table for the A-vs-B disagreements.

One row per disagreement, carrying both coders' answers, both their quotations and notes, and
the partition-related passages from the packet. `consensus_category` and `consensus_reason` are
left EMPTY by construction and this script refuses to write if either is populated.

The consensus decision is not derivable from anything here. In particular the validated author
coding is deliberately NOT read, joined or displayed: consensus is to be reached from the frozen
coding rule and the paper text, and a visible author code would make that impossible to claim.

The packet passages are extracted with the same cue list and sentence splitter the full-text
validation used, imported rather than re-implemented, so the evidence in front of the consensus
round is selected the same way the evidence behind the validation was.

Output: human_coding/returned/reconciliation.csv  (+ a readable .md alongside)
Both land in returned/, which is gitignored, because they quote third-party article text.
"""
import csv
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "scripts")
from fulltext_validation_build import RX, sentences  # noqa: E402  frozen extraction, reused

RET = "human_coding/returned"
LABEL = {1: "mechanism reported", 2: "ratio or counts only",
         3: "no partition statement", 4: "unresolved"}
MAX_PASSAGES = 12


def load(path):
    with io.open(path, encoding="utf-8-sig") as fh:
        return {r["paper_identifier"]: r for r in csv.DictReader(fh)}


def evidence(pid):
    """Partition-related passages from the packet, in document order."""
    p = f"human_coding/packets/{pid}.txt"
    if not os.path.exists(p):
        return ["PACKET MISSING"]
    text = io.open(p, encoding="utf-8", errors="replace").read()
    hits = [s for s in sentences(text) if sum(1 for rx in RX if rx.search(s)) >= 2]
    if len(hits) > MAX_PASSAGES:
        # keep the densest, then restore document order so the reader sees the paper's sequence
        ranked = sorted(hits, key=lambda s: -sum(1 for rx in RX if rx.search(s)))[:MAX_PASSAGES]
        hits = [s for s in hits if s in set(ranked)]
    return hits


def main():
    A = load(os.path.join(RET, "workbook_coder_A.csv"))
    B = load(os.path.join(RET, "workbook_coder_B.csv"))
    if set(A) != set(B):
        sys.exit("The two workbooks do not cover the same papers.")
    dis = sorted(p for p in A if A[p]["category"].strip() != B[p]["category"].strip())
    print(f"{len(dis)} disagreements of {len(A)}")

    rows = []
    for pid in dis:
        a, b = A[pid], B[pid]
        ca, cb = int(a["category"]), int(b["category"])
        rows.append({
            "paper_id": pid,
            "coder_A_category": ca,
            "coder_A_label": LABEL[ca],
            "coder_A_quotation": (a["supporting_quotation"] or "").strip(),
            "coder_A_note": (a["coder_note"] or "").strip(),
            "coder_B_category": cb,
            "coder_B_label": LABEL[cb],
            "coder_B_quotation": (b["supporting_quotation"] or "").strip(),
            "coder_B_note": (b["coder_note"] or "").strip(),
            "packet_passages": "\n".join(f"- {s}" for s in evidence(pid)),
            "consensus_category": "",
            "consensus_reason": "",
        })

    for r in rows:
        if r["consensus_category"] or r["consensus_reason"]:
            sys.exit("REFUSED: a consensus column is populated. This file is built blank.")

    out_csv = os.path.join(RET, "reconciliation.csv")
    with io.open(out_csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    md = ["# Reconciliation — the A-vs-B disagreements", "",
          f"{len(rows)} cases. Both consensus columns are empty and are to be filled by the",
          "study lead and the two coders, from the coding rule and the paper text.",
          "The validated author coding is not shown here and was not read by this script.", ""]
    for i, r in enumerate(rows, 1):
        md += [f"## {i}. {r['paper_id']}", "",
               f"- Coder A: **{r['coder_A_category']} — {r['coder_A_label']}**",
               f"  - quotation: {r['coder_A_quotation'] or '(none)'}"]
        if r["coder_A_note"]:
            md.append(f"  - note: {r['coder_A_note']}")
        md += [f"- Coder B: **{r['coder_B_category']} — {r['coder_B_label']}**",
               f"  - quotation: {r['coder_B_quotation'] or '(none)'}"]
        if r["coder_B_note"]:
            md.append(f"  - note: {r['coder_B_note']}")
        md += ["", "Packet passages:", "", r["packet_passages"], "",
               "- consensus_category: ", "- consensus_reason: ", ""]
    io.open(os.path.join(RET, "reconciliation.md"), "w", encoding="utf-8",
            newline="\n").write("\n".join(md) + "\n")

    print(f"wrote {out_csv}")
    print(f"wrote {os.path.join(RET, 'reconciliation.md')}")
    print("consensus_category and consensus_reason are empty in every row.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
