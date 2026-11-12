"""Emit every scope-analysis fraction into the registry, with its population named.

No percentage is typed here. Each record carries a numerator, a denominator and the analysis
population the denominator must equal; the percentage is derived by fractions.emit and checked
by verify_headlines.py.
"""
import json
import io
import os
import sys
import csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "scripts")
import reported_fractions as F  # noqa: E402

scope = json.load(io.open("corpus/scope_final.json", encoding="utf-8"))
excl = [x for x in json.load(io.open("corpus/excluded_reviews_records.json", encoding="utf-8"))
        if x.get("_exclusion_reason")]
rows = list(csv.DictReader(io.open("corpus/retrieval_table.csv", encoding="utf-8")))

pops = F.populations()

verified_in = sum(1 for r in scope if r["scope_tier"] in ("A", "B") and r["in_scope"])
verified_n = len(pops["POP_VERIFIED"])
miss = [x for x in rows if x["fulltext_obtained"] != "True"]

out = [
    {"id": "A1_out_of_scope", "population": "POP_VERIFIED",
     "label": "papers out of scope among full-text-verified papers",
     "numerator": verified_n - verified_in, "denominator": verified_n,
     "source": "scripts/scope_final.py + the 10 batch scope exclusions",
     "note": "the ten batch exclusions are full-text-verified OUT and belong in the denominator"},

    {"id": "A1b_in_scope", "population": "POP_VERIFIED",
     "label": "papers in scope among full-text-verified papers",
     "numerator": verified_in, "denominator": verified_n,
     "source": "scripts/scope_final.py"},

    {"id": "A3a_out_s2", "population": "POP_CANDIDATE",
     "label": "out of scope on task (S2) across the candidate corpus",
     "numerator": sum(1 for r in scope if r["scope_code"].startswith("OUT_S2")),
     "denominator": len(pops["POP_CANDIDATE"]),
     "source": "corpus/scope_final.json"},

    {"id": "A3b_out_s1", "population": "POP_CANDIDATE",
     "label": "out of scope on domain (S1) across the candidate corpus",
     "numerator": sum(1 for r in scope if r["scope_code"] == "OUT_S1"),
     "denominator": len(pops["POP_CANDIDATE"]),
     "source": "corpus/scope_final.json"},

    {"id": "A7_oa_retrieval_failures", "population": "POP_RETRIEVAL_FAILURES",
     "label": "retrieval failures occurring on nominally open-access papers",
     "numerator": sum(1 for x in miss if x["open_access"] == "True"),
     "denominator": len(miss),
     "source": "corpus/retrieval_table.csv"},
]

F.emit(out)
print(f"emitted {len(out)} scope fractions to corpus/reported_fractions.json")
for f in out:
    print(f"  {f['id']:28s} {f['numerator']:4d}/{f['denominator']:<4d} = {f['pct']:6.2f}%  "
          f"[{f['population']}]")
