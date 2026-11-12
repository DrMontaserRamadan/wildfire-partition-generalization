"""Regression test for the coding excerpts. Exits non-zero if the old defect reappears.

The defect: excerpts were assembled by merging oversized character windows and then cut at a
fixed cap, so what reached the coders was a PREFIX of the paper. The Results section of the
seed paper vanished entirely and four other excerpts had silent internal elisions. Both coders
caught it independently, which is the only reason it was caught at all.

The test that matters is not "is the excerpt long enough" but "does it reach the end of the
paper". A prefix and a targeted extract can have identical lengths.
"""
import json
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

REACH_MIN = 0.70        # the last retained passage must start at least this far into the text
SPREAD_MIN = 6          # distinct document deciles a paper's passages must touch


def passage_positions(excerpt, raw):
    """Where each retained passage sits in the source, as a fraction of document length."""
    pos = []
    for frag in re.split(r"\[\.\.\..{0,40}omitted \.\.\.\]", excerpt):
        probe = re.sub(r"«[^»]*»", "", frag).strip()[:60]
        if len(probe) < 30:
            continue
        i = raw.find(probe)
        if i >= 0:
            pos.append(i / max(1, len(raw)))
    return pos


def main():
    docs = json.load(io.open("corpus/to_code.json", encoding="utf-8"))
    failures = []
    reaches = []

    for o in docs:
        raw = io.open(f"corpus/ft/{o['ftkey']}.txt", encoding="utf-8", errors="replace").read()
        pos = passage_positions(o["excerpt"], raw)
        if not pos:
            failures.append((o["paper_id"], "no passage could be located in the source"))
            continue
        reach = max(pos)
        spread = len({int(p * 10) for p in pos})
        reaches.append(reach)
        if reach < REACH_MIN:
            failures.append((o["paper_id"],
                             f"last passage at {reach:.0%} of the document - looks like a prefix"))
        elif spread < SPREAD_MIN:
            failures.append((o["paper_id"],
                             f"passages touch only {spread} deciles - coverage is clustered"))

        # every elision must be declared, never silent
        if "[...]" in o["excerpt"] and "omitted" not in o["excerpt"]:
            failures.append((o["paper_id"], "undeclared elision marker"))

    reaches.sort()
    print(f"papers checked           : {len(docs)}")
    print(f"last-passage reach       : median {reaches[len(reaches)//2]:.0%}, "
          f"min {reaches[0]:.0%}, max {reaches[-1]:.0%}")
    print(f"papers reaching past {REACH_MIN:.0%} : "
          f"{sum(1 for r in reaches if r >= REACH_MIN)}/{len(reaches)}")

    if failures:
        print(f"\nFAIL ({len(failures)}):")
        for pid, why in failures:
            print(f"  {pid}  {why}")
        return 1
    print("\nPASS - no excerpt is a prefix, and every elision is declared.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
