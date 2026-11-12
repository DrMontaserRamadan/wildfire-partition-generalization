"""Look for the same paper entering the sampling frame twice.

Found while checking a hand-retrieved PDF: the Russian original of one article and its Springer
English translation are two separate OpenAlex records, with two DOIs and two titles that differ
only in wording ("Assessment"/"Estimation", "Multi-Temporal"/"Multidate"). Both happened to be
out of scope, so nothing moved. A duplicate that landed INSIDE the corpus would be worse: it
would count one paper twice in the endpoint's denominator and numerator.

This scans the whole candidate frame for near-duplicate titles and reports every pair, with the
scope status of both members, so any pair inside the corpus is visible rather than assumed absent.
"""
import io
import json
import os
import re
import unicodedata
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

STOP = {"a", "an", "and", "for", "from", "in", "of", "on", "the", "to", "using", "with",
        "based", "via", "its"}


def toks(s):
    s = unicodedata.normalize("NFKC", s).lower()
    return {w for w in re.findall(r"[a-z0-9]+", s) if w not in STOP and len(w) > 2}


def main():
    uni = json.load(io.open("corpus/UNIVERSE_FROZEN.json", encoding="utf-8"))["papers"]
    scope = {r["paper_id"]: r for r in
             json.load(io.open("corpus/scope_final.json", encoding="utf-8"))}
    hand = {d["paper_id"]: d for d in
            json.load(io.open("corpus/scope_incoming_decisions.json",
                              encoding="utf-8"))["decisions"]}

    def status(pid):
        if pid in hand:
            return f"{hand[pid]['scope_code']} (full text)"
        r = scope.get(pid)
        return f"{r['scope_code']} ({r['scope_evidence'][:11]})" if r else "not screened"

    T = {p["paper_id"]: toks(p["title"]) for p in uni}
    title = {p["paper_id"]: p["title"] for p in uni}
    doi = {p["paper_id"]: p.get("doi") for p in uni}

    pairs = []
    for a, b in combinations(sorted(T), 2):
        ta, tb = T[a], T[b]
        if not ta or not tb:
            continue
        j = len(ta & tb) / len(ta | tb)
        if j >= 0.55:
            pairs.append((j, a, b))
    pairs.sort(reverse=True)

    print(f"candidate frame: {len(uni)} records")
    print(f"near-duplicate title pairs at Jaccard >= 0.55: {len(pairs)}\n")
    inside = 0
    for j, a, b in pairs:
        sa, sb = status(a), status(b)
        both_in = ("IN" in sa and not sa.startswith("OUT")) and \
                  ("IN" in sb and not sb.startswith("OUT"))
        mark = "  <-- BOTH IN SCOPE, would double-count" if both_in else ""
        inside += both_in
        print(f"J={j:.2f}{mark}")
        print(f"   {a}  {sa:<22} {title[a][:74]}")
        print(f"        doi {doi[a]}")
        print(f"   {b}  {sb:<22} {title[b][:74]}")
        print(f"        doi {doi[b]}\n")
    print(f"pairs with both members in scope: {inside}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
