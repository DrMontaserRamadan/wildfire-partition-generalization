#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Record approved consensus decisions into the reconciliation file.

Writes ONLY human_coding/returned/reconciliation.csv. It never opens either coder workbook for
writing, and it verifies both against the hashes recorded when they arrived before it will write
anything: the coders' original answers are the independent record and must survive the consensus
round untouched.

Decisions are supplied on the command line as PAPERID=CATEGORY pairs, so what was approved is
visible in the shell history rather than buried in a file. A paper already carrying a consensus
code is not overwritten; re-deciding one requires clearing it by hand, on purpose.

    python scripts/record_consensus.py W3090022951=1 W3186499362=3 ...

Two of the fourteen cases were not settled in the reconciliation round and were referred back to
the two independent coders, so their decisions did not come from the corresponding author and
must not be recorded as though they had. Those are written with --from-referral, which reads the
coders' returned answers out of the frozen return file rather than off the command line:

    python scripts/record_consensus.py --from-referral

That path verifies the return file against the hash taken when it arrived, refuses any paper it
does not find in the file, and records the provenance of each decision as the referral rather
than as an approval from this side.
"""
import csv
import hashlib
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
RET = "human_coding/returned"
RECON = os.path.join(RET, "reconciliation.csv")


def receipt_hash(who):
    p = os.path.join(RET, f"RECEIPT_coder_{who}.md")
    m = re.search(r"sha256:\s*([0-9a-f]{64})", io.open(p, encoding="utf-8").read())
    if not m:
        sys.exit(f"No hash recorded in {p}.")
    return m.group(1)


REFERRAL = os.path.join(RET, "referral_return.md")
REFERRAL_RECEIPT = os.path.join(RET, "RECEIPT_referral.md")


def read_referral():
    """Parse the coders' returned answers, after checking the file is the one that arrived."""
    if not os.path.exists(REFERRAL):
        sys.exit(f"No referral return at {REFERRAL}.")
    raw = io.open(REFERRAL, "rb").read()
    m = re.search(r"sha256:\s*([0-9a-f]{64})", io.open(REFERRAL_RECEIPT, encoding="utf-8").read())
    if not m:
        sys.exit(f"No hash recorded in {REFERRAL_RECEIPT}.")
    now = hashlib.sha256(raw).hexdigest()
    if now != m.group(1):
        sys.exit(f"REFUSING TO RUN: {REFERRAL} no longer matches its arrival hash.\n"
                 f"  arrival {m.group(1)}\n  now     {now}\n"
                 f"  The coders' returned answers are the record. Restore the file.")
    text = raw.decode("utf-8")

    found = {}
    for block in re.split(r"^###\s+", text, flags=re.M)[1:]:
        pid = block.split("\n", 1)[0].strip()
        cat = re.search(r"\*\*Agreed category:\s*([1-4])\b", block)
        if not cat:
            sys.exit(f"No agreed category for {pid} in the referral return. "
                     f"A recorded disagreement is not written by this script.")
        found[pid] = int(cat.group(1))
    if not found:
        sys.exit(f"{REFERRAL} carries no decisions.")
    print(f"referral return matches its arrival hash; {len(found)} decision(s) read from it")
    return found


def main(argv):
    if not argv:
        sys.exit("Nothing to record. Pass PAPERID=CATEGORY pairs, or --from-referral.")

    for who in ("A", "B"):
        wb = os.path.join(RET, f"workbook_coder_{who}.csv")
        now = hashlib.sha256(io.open(wb, "rb").read()).hexdigest()
        want = receipt_hash(who)
        if now != want:
            sys.exit(f"REFUSING TO RUN: {wb} no longer matches its arrival hash.\n"
                     f"  arrival {want}\n  now     {now}\n"
                     f"  The coders' originals are the independent record. Restore it.")
    print("both coder workbooks match their arrival hashes; neither is opened for writing")

    from_referral = "--from-referral" in argv
    argv = [a for a in argv if a != "--from-referral"]

    decisions = {}
    if from_referral:
        if argv:
            sys.exit("--from-referral takes no PAPERID=CATEGORY pairs; the decisions are read "
                     "from the frozen return file, not retyped.")
        decisions = read_referral()
    for a in argv:
        if "=" not in a:
            sys.exit(f"Bad argument {a!r}; expected PAPERID=CATEGORY.")
        pid, cat = a.split("=", 1)
        if cat not in {"1", "2", "3", "4"}:
            sys.exit(f"Category for {pid} must be 1-4, got {cat!r}.")
        decisions[pid] = int(cat)
    if not decisions:
        sys.exit("Nothing to record.")

    with io.open(RECON, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
        fields = list(rows[0].keys())

    known = {r["paper_id"] for r in rows}
    unknown = sorted(set(decisions) - known)
    if unknown:
        sys.exit(f"Not disagreement cases: {', '.join(unknown)}")

    written = 0
    for r in rows:
        pid = r["paper_id"]
        if pid not in decisions:
            continue
        if r["consensus_category"].strip():
            sys.exit(f"{pid} already has consensus {r['consensus_category']}. "
                     f"Clear it by hand to re-decide.")
        c = decisions[pid]
        r["consensus_category"] = str(c)
        # The reason records the evidence the decision rests on, drawn from the coders' own
        # quotations and the packet passages already in the row. It is not a re-derivation.
        if from_referral:
            r["consensus_reason"] = (
                f"Consensus {c}. Agreed by the two independent coders on a fresh re-reading "
                f"after referral, not decided on this side; coder A had "
                f"{r['coder_A_category']}, coder B had {r['coder_B_category']} before it. The "
                f"deciding quotation and the boundary reasoning are recorded verbatim in "
                f"referral_return.md. The validated author coding was not consulted.")
        else:
            r["consensus_reason"] = (
                f"Consensus {c}. Approved by the corresponding author on the coding rule and the "
                f"packet text; coder A had {r['coder_A_category']}, coder B had "
                f"{r['coder_B_category']}. The validated author coding was not consulted.")
        written += 1

    with io.open(RECON, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    done = sum(1 for r in rows if r["consensus_category"].strip())
    print(f"recorded {written} decision(s); {done} of {len(rows)} cases now have a consensus code")
    if done < len(rows):
        print("remaining: " + ", ".join(r["paper_id"] for r in rows
                                        if not r["consensus_category"].strip()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
