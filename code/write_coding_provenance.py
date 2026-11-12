#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Write corpus/human_coding_provenance.json — the trackable record of the coding workflow.

The workbooks, the reconciliation table and the referral folder all stay out of the repository:
they are human data and they quote third-party articles. What belongs in version control is the
part that carries no article text — the arrival hashes, the counts, the frozen pre-consensus
statistics, and the consensus codes themselves.

Codes are data about the papers. Quotations are from the papers. This file carries the first and
not the second, which is the line the rest of the project already draws.

Nothing here is computed fresh: hashes are read off the arrival receipts and the statistics off
the comparison output, so this file cannot disagree with them without one of them having changed.
"""
import csv
import hashlib
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
RET = "human_coding/returned"
OUT = "corpus/human_coding_provenance.json"


def receipt(who):
    p = os.path.join(RET, f"RECEIPT_coder_{who}.md")
    t = io.open(p, encoding="utf-8").read()
    h = re.search(r"sha256:\s*([0-9a-f]{64})", t)
    d = re.search(r"received:\s*([0-9-]{10})", t)
    if not h:
        sys.exit(f"No hash in {p}.")
    return {"sha256": h.group(1), "received": d.group(1) if d else None}


def main():
    prov = {}
    for who in ("A", "B"):
        r = receipt(who)
        wb = os.path.join(RET, f"workbook_coder_{who}.csv")
        now = hashlib.sha256(io.open(wb, "rb").read()).hexdigest()
        if now != r["sha256"]:
            sys.exit(f"REFUSING: {wb} no longer matches its arrival hash.")
        prov[f"coder_{who}"] = r
    prov["workbooks_verified_against_arrival_hashes"] = True

    res = json.load(io.open("corpus/human_coding_results.json", encoding="utf-8"))
    ab = next(v for k, v in res.items() if k.startswith("human A vs human B"))
    prov["pre_consensus"] = {
        "n": ab["n"],
        "agreement_count": round(ab["raw_agreement"] * ab["n"]),
        "raw_agreement": ab["raw_agreement"],
        "cohens_kappa": ab["kappa"],
        "n_disagreements": len(res["ab_disagreements"]),
        "note": "Frozen. The consensus round does not alter these.",
    }

    rows = list(csv.DictReader(io.open(os.path.join(RET, "reconciliation.csv"),
                                       encoding="utf-8")))
    decided, referred = {}, []
    for r in rows:
        c = r["consensus_category"].strip()
        if c:
            decided[r["paper_id"]] = int(c)
        else:
            referred.append(r["paper_id"])
    prov["consensus"] = {
        "n_cases": len(rows),
        "decided": decided,
        "referred_unresolved": referred,
        "coder_codes": {r["paper_id"]: {"A": int(r["coder_A_category"]),
                                        "B": int(r["coder_B_category"])} for r in rows},
        "note": ("Referred cases were sent back to the two coders for independent resolution. "
                 "Neither the earlier author classification nor any party's reading was "
                 "disclosed to them."),
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(prov, ensure_ascii=False, indent=1) + "\n")

    body = io.open(OUT, encoding="utf-8").read()
    for bad in ("supporting_quotation", "packet_passages"):
        if bad in body:
            sys.exit(f"REFUSED: {OUT} contains {bad}; article text must not be committed.")
    print(f"wrote {OUT}")
    print(f"  pre-consensus n={prov['pre_consensus']['n']} "
          f"agreement={prov['pre_consensus']['agreement_count']}/{prov['pre_consensus']['n']} "
          f"kappa={prov['pre_consensus']['cohens_kappa']:.3f}")
    print(f"  consensus decided {len(decided)}/{len(rows)}; referred: {', '.join(referred)}")
    print("  no article quotations in the file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
