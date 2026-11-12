"""Recompute the corpus flow and the abstract-screen confusion matrix from the records.

Two targeted sweeps have now been run by hand, and neither is a random sample of anything: the
first pursued papers the abstract screen had placed IN scope, the second pursued papers it had
placed OUT. Pooling them into a single "share out of scope" would report a selection artefact.
They are therefore reported as what they are, a validation of the abstract screen in both
directions, which is the confusion matrix this script prints.
"""
import io
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def L(p):
    return json.load(io.open(p, encoding="utf-8"))


def main():
    acq = L("corpus/acquisition_bias.json")
    scope = {r["paper_id"]: r for r in L("corpus/scope_final.json")}
    excl_rev = [x for x in L("corpus/excluded_reviews_records.json")
                if x.get("_exclusion_reason")]
    s1 = L("corpus/scope_incoming_decisions.json")["decisions"]
    s2 = L("corpus/scope_exclcheck_decisions.json")["decisions"]

    # one paper in sweep 2 arrived as page 1 only; its status is unchanged and it is NOT
    # counted as verified at full text
    PARTIAL = {"W3135044310"}

    n_cand = acq["candidates"]
    auto = acq["retrieved"]
    ab = [r for r in scope if scope[r]["scope_tier"] in ("A", "B")]
    v_auto = len(ab) + len(excl_rev)
    landing = auto - v_auto

    hand = len(s1) + len(s2)
    v_hand = len(s1) + len([d for d in s2 if d["paper_id"] not in PARTIAL])
    verified = v_auto + v_hand
    retrieved = auto + hand
    unretrieved = n_cand - retrieved

    in_auto = sum(1 for r in ab if scope[r]["in_scope"])
    in_scope = in_auto + sum(1 for d in s1 + s2 if d["in_scope"])
    out_scope = verified - in_scope

    codes = Counter(scope[r]["scope_code"] for r in ab if not scope[r]["in_scope"])
    for d in s1 + s2:
        if not d["in_scope"] and d["paper_id"] not in PARTIAL:
            codes[d["scope_code"]] += 1
    s1c = codes["OUT_S1"]
    s2c = codes["OUT_S2"] + codes["OUT_BORDERLINE_S2"]
    s3c = codes["OUT_S3"] + len(excl_rev)

    learned = 64 + len(L("corpus/validation_incoming_codes.json")["per_paper"]) \
        + len(L("corpus/validation_exclcheck_codes.json")["per_paper"])

    print("CORPUS FLOW")
    print(f"  candidates                        {n_cand}")
    print(f"  retrieved                         {retrieved}   "
          f"({auto} automatically, {hand} by hand)")
    print(f"  still unretrieved                 {unretrieved}")
    print(f"  verified at full text             {verified}   "
          f"(4 landing pages, 1 partial, excluded)")
    print(f"  in scope                          {in_scope}")
    print(f"  out of scope                      {out_scope}   "
          f"(S1 {s1c}, S2 {s2c}, document type {s3c})")
    print(f"  train a learned model             {learned}")
    assert s1c + s2c + s3c == out_scope, (s1c, s2c, s3c, out_scope)
    assert in_scope + out_scope == verified

    print("\nABSTRACT SCREEN vs FULL TEXT, on every paper where both exist")
    a_in_f_in = 53 - 3 + sum(1 for d in s1 if d["in_scope"])
    a_in_f_out = 3 + sum(1 for d in s1 if not d["in_scope"])
    a_out_f_out = 27 + sum(1 for d in s2 if not d["in_scope"])
    a_out_f_in = sum(1 for d in s2 if d["in_scope"])
    print(f"  abstract IN  -> full text IN      {a_in_f_in}")
    print(f"  abstract IN  -> full text OUT     {a_in_f_out}   "
          f"false inclusions, {100*a_in_f_out/(a_in_f_in+a_in_f_out):.1f}%")
    print(f"  abstract OUT -> full text OUT     {a_out_f_out}")
    print(f"  abstract OUT -> full text IN      {a_out_f_in}   "
          f"false exclusions, {100*a_out_f_in/(a_out_f_out+a_out_f_in):.1f}%")

    out = dict(candidates=n_cand, retrieved=retrieved, retrieved_auto=auto, retrieved_hand=hand,
               unretrieved=unretrieved, verified=verified, in_scope=in_scope,
               out_of_scope=out_scope, out_s1=s1c, out_s2=s2c, out_doctype=s3c,
               learned=learned,
               confusion=dict(abstract_in_full_in=a_in_f_in, abstract_in_full_out=a_in_f_out,
                              abstract_out_full_out=a_out_f_out,
                              abstract_out_full_in=a_out_f_in))
    json.dump(out, io.open("corpus/corpus_flow_now.json", "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
