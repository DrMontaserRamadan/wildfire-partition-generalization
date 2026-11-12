#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Assemble human_coding/returned/consensus.csv from records that already exist.

The consensus coding is not a third reading. It is the two coders' agreement wherever they
agreed, and the recorded reconciliation decision wherever they did not. Nothing here decides
anything, and there is no path through this script that invents a category:

  * both workbooks are checked against the hashes taken when they arrived, and neither is
    opened for writing;
  * every disagreement must carry a recorded consensus code, and the set of reconciliation
    rows must be exactly the set of disagreements — a row too many or too few and it refuses;
  * agreements are copied from the coders' own answers.

The supporting quotation is carried across from whichever coder the consensus code matches, so
each consensus row keeps a quotation traceable to the packet. Where the consensus took a
category neither coder chose, the quotation cell is left empty rather than filled with one that
supports a different category, and the reconciliation record carries the reasoning.

Output: human_coding/returned/consensus.csv
"""
import csv
import hashlib
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
RET = "human_coding/returned"
OUT = os.path.join(RET, "consensus.csv")
FIELDS = ["row", "paper_identifier", "category", "supporting_quotation", "coder_note"]


def receipt_hash(name):
    import re
    p = os.path.join(RET, f"RECEIPT_{name}.md")
    m = re.search(r"sha256:\s*([0-9a-f]{64})", io.open(p, encoding="utf-8").read())
    if not m:
        sys.exit(f"No hash recorded in {p}.")
    return m.group(1)


def load_workbook(who):
    wb = os.path.join(RET, f"workbook_coder_{who}.csv")
    now = hashlib.sha256(io.open(wb, "rb").read()).hexdigest()
    want = receipt_hash(f"coder_{who}")
    if now != want:
        sys.exit(f"REFUSING TO RUN: {wb} no longer matches its arrival hash.\n"
                 f"  arrival {want}\n  now     {now}")
    with io.open(wb, encoding="utf-8-sig") as fh:
        return {r["paper_identifier"].strip(): r for r in csv.DictReader(fh)}


def main():
    A, B = load_workbook("A"), load_workbook("B")
    print("both coder workbooks match their arrival hashes")
    if set(A) != set(B):
        sys.exit("The two workbooks do not cover the same papers.")

    recon_path = os.path.join(RET, "reconciliation.csv")
    with io.open(recon_path, encoding="utf-8") as fh:
        recon = {r["paper_id"].strip(): r for r in csv.DictReader(fh)}

    disagreed = {p for p in A if A[p]["category"].strip() != B[p]["category"].strip()}
    if set(recon) != disagreed:
        missing = sorted(disagreed - set(recon))
        extra = sorted(set(recon) - disagreed)
        sys.exit(f"REFUSED: the reconciliation file does not match the disagreements.\n"
                 f"  disagreements with no reconciliation row: {missing}\n"
                 f"  reconciliation rows that are not disagreements: {extra}")

    undecided = sorted(p for p, r in recon.items() if not r["consensus_category"].strip())
    if undecided:
        sys.exit(f"REFUSED: {len(undecided)} disagreement(s) carry no consensus code: "
                 f"{', '.join(undecided)}.\n"
                 f"  This file is not written while any case is open, and no code is inferred.")

    rows, from_recon, neither = [], 0, []
    for i, pid in enumerate(sorted(A), 1):
        if pid in recon:
            cat = recon[pid]["consensus_category"].strip()
            src = A[pid] if A[pid]["category"].strip() == cat else (
                B[pid] if B[pid]["category"].strip() == cat else None)
            if src is None:
                neither.append(pid)
            quote = src["supporting_quotation"] if src else ""
            note = ("consensus code; quotation carried from the coder whose category it matches"
                    if src else
                    "consensus code that neither coder recorded; see reconciliation.csv")
            from_recon += 1
        else:
            cat, quote = A[pid]["category"].strip(), A[pid]["supporting_quotation"]
            note = "both coders agreed independently"
        if cat not in {"1", "2", "3", "4"}:
            sys.exit(f"Category for {pid} is {cat!r}, outside 1-4.")
        rows.append({"row": i, "paper_identifier": pid, "category": cat,
                     "supporting_quotation": quote, "coder_note": note})

    with io.open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {OUT}")
    print(f"  {len(rows)} papers: {len(rows)-from_recon} from independent agreement, "
          f"{from_recon} from the reconciliation record")
    if neither:
        print(f"  {len(neither)} consensus code(s) neither coder recorded, quotation left "
              f"empty: {', '.join(neither)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
