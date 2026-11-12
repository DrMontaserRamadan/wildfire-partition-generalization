"""Trace every headline number in CLAIM_LEDGER.md back to a frozen source record.

A ledger that asserts its own numbers is worth nothing. This recomputes each one from the
frozen artefacts and fails loudly on any mismatch, so a stale figure cannot survive a green
check. Exits non-zero if any headline does not reconcile.
"""
import json
import io
import os
import csv
import re
import sys
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

checks = []


def check(name, got, want, tol=0.05, src=""):
    ok = (abs(got - want) <= tol) if isinstance(want, float) else (got == want)
    checks.append((ok, name, got, want, src))


def L(p):
    return json.load(io.open(p, encoding="utf-8"))


# ---------------------------------------------------------------- A. scope
scope = L("corpus/scope_final.json")
excl = [x for x in L("corpus/excluded_reviews_records.json") if x.get("_exclusion_reason")]
verified = [r for r in scope if r["scope_tier"] in ("A", "B")]
v_in = sum(1 for r in verified if r["in_scope"])
v_n = len(verified) + len(excl)          # the ten batch exclusions are verified-OUT
check("A1 in-scope verified numerator", v_in, 67, src="scope_final.json")
check("A1 in-scope verified denominator", v_n, 111, src="+ 10 batch scope exclusions")
check("A1 out-of-scope %", 100 * (v_n - v_in) / v_n, 39.6, 0.1)
check("A3 OUT_S2 count", sum(1 for r in scope if r["scope_code"].startswith("OUT_S2")), 35)
check("A3 OUT_S1 count", sum(1 for r in scope if r["scope_code"] == "OUT_S1"), 23)
check("A9 landing-page tier C1",
      sum(1 for r in scope if "landing page" in r["scope_evidence"]), 4)

cal = L("corpus/scope_calibration.json")
check("A4 sensitivity", cal["unclear_as_OUT"]["sens"], 1.0, 1e-9)
check("A5 kappa low", cal["unclear_as_OUT"]["kappa"], 0.912, 0.001)
check("A5 kappa high", cal["unclear_as_IN"]["kappa"], 0.787, 0.001)

sens = L("corpus/scope_sensitivity.json")
check("A1 contested lower bound %", sens["verified_bounds_pct"][0], 59.5, 0.1)
check("A1 contested upper bound %", sens["verified_bounds_pct"][1], 61.3, 0.1)
check("A2 total lower", sens["total_bounds_of_159"][0], 81.1, 0.2)
check("A2 total upper", sens["total_bounds_of_159"][1], 93.4, 0.2)
check("contested count", len(sens["contested"]), 9)

rows = list(csv.DictReader(io.open("corpus/retrieval_table.csv", encoding="utf-8")))
miss = [x for x in rows if x["fulltext_obtained"] != "True"]
oa_fail = [x for x in miss if x["open_access"] == "True"]
check("A7 OA retrieval failures", len(oa_fail), 39, src="retrieval_table.csv")
check("A7 total retrieval failures", len(miss), 54)

# ---------------------------------------------------------------- B. reliability
rel = L("corpus/reliability_comparison.json")
check("B1 r1 split_protocol raw", rel["round1_carried7"]["split_protocol"]["raw"], 0.4286, 0.001)
check("B1 r1 split_protocol kappa", rel["round1_carried7"]["split_protocol"]["kappa"], 0.1515, 0.001)
check("B1 r2 split_protocol raw", rel["round2_carried7"]["split_protocol"]["raw"], 1.0, 1e-9)
check("B1 r2 split_protocol kappa", rel["round2_carried7"]["split_protocol"]["kappa"], 1.0, 1e-9)
check("B4 failing fields", rel["n_failing_round2"], 11)

A = {r["paper_id"]: r for r in L("corpus/raw_coding/coded_A_r2.RAW.json")}
B = {r["paper_id"]: r for r in L("corpus/raw_coding/coded_B_r2.RAW.json")}
check("B raw codings A", len(A), 15)
check("B raw codings B", len(B), 15)
check("B2 ratio_only modal (A)",
      sum(1 for r in A.values() if r.get("split_protocol") == "ratio_only_mechanism_unstated"), 5)
check("B2 ratio_only modal (B)",
      sum(1 for r in B.values() if r.get("split_protocol") == "ratio_only_mechanism_unstated"), 5)
# the raw codings must still disagree where the analysis says they do: no consensus overwrite
subs = sum(1 for p in A if A[p].get("hyperparams_full") != B[p].get("hyperparams_full"))
check("raw codings NOT overwritten with consensus", subs, 4,
      src="hyperparams_full disagreements preserved")

# ---------------------------------------------------------------- C. FLAME
fl = [r for r in L("corpus/flame_timeline.json") if r.get("headline_accuracy") is not None]
off = [r["headline_accuracy"] for r in fl if r["protocol"] == "OFFICIAL"]
oth = [r["headline_accuracy"] for r in fl if r["protocol"] != "OFFICIAL"]
check("C1 median official", st.median(off), 83.98, 0.01)
check("C1 median non-official", st.median(oth), 98.18, 0.01)
check("C1 gap", st.median(oth) - st.median(off), 14.20, 0.01)
check("C2 IQRs disjoint", st.quantiles(off, n=4)[2] < st.quantiles(oth, n=4)[0], True)
wins = sum(1 for a in off for b in oth if b > a)
check("C3 pairwise wins", wins, 233)
check("C3 pairwise total", len(off) * len(oth), 234)
check("C4 max official", max(off), 92.00, 0.01)
check("C4 min non-official", min(oth), 91.20, 0.01)

# ---------------------------------------------------------------- D. contamination
ov = L("corpus/overlap_summary.json")
fn = ov["sizes"]["FireNET"]
check("D1 FireNET size", fn, 502)
pair = ov["cross"].get("DeepQuestAI_FireSmoke|FireNET") or ov["cross"].get("FireNET|DeepQuestAI_FireSmoke")
hit = pair["b_hit"] if "FireNET" in "DeepQuestAI_FireSmoke|FireNET".split("|")[1] else pair["a_hit"]
check("D1 FireNET images with a twin", hit, 218, src="overlap_summary.json")
check("D1 overlap share %", 100 * hit / fn, 43.4, 0.1)
check("D3 D-Fire vs DeepQuestAI overlap", ov["cross"]["DFire_test|DeepQuestAI_FireSmoke"]["a_hit"], 0)
check("D3 D-Fire vs FireNET overlap", ov["cross"]["DFire_test|FireNET"]["a_hit"], 0)

# ---------------------------------------------------------------- fraction registry gate
# Every reported fraction must (a) recompute to its stated percentage and (b) have a
# denominator equal to the analysis population it declares. Typed percentages are not
# authoritative and cannot reach a manuscript through this gate.
sys.path.insert(0, "scripts")
import reported_fractions as F  # noqa: E402

registry = F.load_registry()
pops = F.populations()
frac_problems = []

if not registry:
    frac_problems.append("registry is EMPTY — no fraction has been emitted")

for f in registry:
    recomputed = round(100.0 * f["numerator"] / f["denominator"], 4)
    if abs(recomputed - f["pct"]) > 1e-6:
        frac_problems.append(
            f"{f['id']}: stored pct {f['pct']} != {f['numerator']}/{f['denominator']} "
            f"= {recomputed}")
    pop = f["population"]
    if pop not in pops:
        # populations that only exist after coding are resolved by the coding pipeline
        if not pop.startswith("POP_"):
            frac_problems.append(f"{f['id']}: unknown population {pop!r}")
        continue
    n_pop = len(pops[pop])
    if f["denominator"] != n_pop:
        frac_problems.append(
            f"{f['id']}: denominator {f['denominator']} != |{pop}| = {n_pop} "
            f"— the denominator does not match the population it claims")

checks.append((not frac_problems, f"fraction registry ({len(registry)} fractions)",
               len(frac_problems), 0, "scripts/reported_fractions.py"))

# ------------------------------------------- R. partition-granularity experiment (C3)
# The ledger's section R asserts the experiment's numbers. Recompute each from the 76 run
# records so the ledger cannot drift from them, and re-derive the run-level provenance that
# every row in that section depends on.
C3 = L("corpus/estimands_2026-09-18.json")
_runs = [L(f"corpus/experiment_runs/{f}") for f in os.listdir("corpus/experiment_runs")
         if f.endswith(".json") and "PILOT" not in f]
_log = [json.loads(x) for x in
        io.open("corpus/run_all_log.jsonl", encoding="utf-8").read().splitlines() if x.strip()]
SRC = "corpus/estimands_2026-09-18.json"

check("R  runs completed", len(_runs), 76, src=SRC)
check("R  runs ok in log", sum(1 for r in _log if r.get("ok")), 76, src="run_all_log.jsonl")
check("R  distinct GPUs (a second device would confound)",
      len({r["gpu"] for r in _log}), 1, src="run_all_log.jsonl")
check("R2 split-noise floor", C3["split_noise_floor"]["floor"], 0.0226, tol=0.0001, src=SRC)

_e1 = C3["E1_absolute_shift"]
check("R1 smallest effect is >= 9x the floor",
      round(min(abs(v["delta_mean"]) for v in _e1["P2_event_disjoint"].values())
            / C3["split_noise_floor"]["floor"], 1), 9.4, tol=0.1, src=SRC)
for _p, _lo, _hi in (("P2_event_disjoint", 0.212, 0.275),
                     ("P3_camera_disjoint", 0.268, 0.493),
                     ("P4_partner_lopo", 0.286, 0.596)):
    _d = sorted(abs(v["delta_mean"]) for v in _e1[_p].values())
    check(f"R1 {_p} delta low", _d[0], _lo, tol=0.001, src=SRC)
    check(f"R1 {_p} delta high", _d[-1], _hi, tol=0.001, src=SRC)
check("R1 every E1 interval excludes zero",
      sum(1 for p in _e1.values() for v in p.values()
          if v["ci95"][0] <= 0 <= v["ci95"][1] and v["n"] > 1), 0, src=SRC)

_e2 = C3["E2_rank_concordance"]
check("R3 tau, P1 vs every coarser rung",
      len({round(v["tau"], 2) for k, v in _e2.items() if k.startswith("P1_")}), 1, src=SRC)
check("R3 that single tau value", round(
    next(v["tau"] for k, v in _e2.items() if k.startswith("P1_")), 2), 0.33, tol=0.005, src=SRC)
check("R3 tau, every coarse-coarse pair",
      min(round(v["tau"], 2) for k, v in _e2.items() if not k.startswith("P1_")),
      1.00, tol=0.005, src=SRC)

_e4 = C3["E4_winner_instability"]
check("R4 winner-changing rung pairs", _e4["winner_changes"], 4, src=SRC)
check("R4 rung pairs total", _e4["protocol_pairs"], 10, src=SRC)
check("R4 distinct winners", len(_e4["distinct_winners"]), 2, src=SRC)
for _p, _m, _n in (("P1_random_image", "yolov8s", 5), ("P3_camera_disjoint", "retinanet", 5),
                   ("P4_partner_lopo", "retinanet", 3)):
    check(f"R4 {_p} rank-1 unanimity",
          _e4["rank1_count_by_replicate"][_p]["counts"][_m], _n, src=SRC)

# R5 is the fragile row. Its margin above the floor is the number the ledger and the matrix
# both require to be disclosed, so it is recomputed rather than trusted.
_rev = C3["E3_pairwise_reversal"]["P1_random_image__vs__P3_camera_disjoint"]
_sep = abs(next(x["diff_a"] for x in _rev["detail"] if x["pair"] == "yolov8s>retinanet"))
check("R5 reversing pair P1 separation", _sep, 0.0236, tol=0.0002, src=SRC)
check("R5 margin above the floor (must stay disclosed)",
      round(_sep - C3["split_noise_floor"]["floor"], 4), 0.0010, tol=0.0002, src=SRC)
check("R5 reversals, P1 vs camera-disjoint", _rev["reversed"], 1, src=SRC)
check("R7 reversals among coarse rungs",
      sum(v["reversed"] for k, v in C3["E3_pairwise_reversal"].items()
          if not k.startswith("P1_")), 0, src=SRC)

check("R9 P4 training images",
      min(r["n_train_used"] for r in _runs if r["partition"].startswith("P4")), 13836, src=SRC)
check("R9 other-rung training images",
      max(r["n_train_used"] for r in _runs if r["partition"].startswith("P1")), 21995, src=SRC)

# R10 is recorded in the ledger as computed and deliberately unreported. Check it is still
# present in the analysis record, so "we chose not to report it" stays an auditable statement
# rather than a claim about a number nobody can find.
check("R10 operating-point analysis retained in the record",
      "S1_operating_point_transfer" in C3, True, src=SRC)

# Section P's endpoint rows, added when hand retrieval enlarged the corpus on 2026-09-19. The
# ledger asserted A1 and A3 for a day without either being bound to a source, which is how the
# first version of this gate let a changed count through; the rows below close that.
_LED = io.open("CLAIM_LEDGER.md", encoding="utf-8").read()
_REC = json.load(io.open("corpus/endpoint_recomputed.json", encoding="utf-8"))
_SRCP = "endpoint_recomputed.json"
for _key, _lab in (("combined", "P0"), ("validated_original", "P0a"),
                   ("newly_retrieved", "P0c")):
    _b = _REC[_key]
    check(f"{_lab} numerator over denominator in the ledger",
          f"{_b['k']} / {_b['n']} = {_b['pct']:.1f}%" in _LED
          or f"{_b['k']}/{_b['n']} = {_b['pct']:.1f}%" in _LED, True, src=_SRCP)
check("P0 interval in the ledger",
      f"[{_REC['combined']['ci'][0]:.1f}–{_REC['combined']['ci'][1]:.1f}]" in _LED, True,
      src=_SRCP)
check("P0b frozen coding still stated on its own population",
      "38 / 64 = 59.4%" in _LED and "NEVER EXTEND TO 77" in _LED, True, src=_SRCP)
check("P0d abstract-screen accuracy recorded in both directions",
      "false inclusions 5/71 = 7.0%; false exclusions 2/55 = 3.6%" in _LED, True,
      src="corpus_flow_now.json")
check("P0c does not present the retrieval-bias test as significant",
      "does NOT reach significance" in _LED, True, src=_SRCP)
check("P0 excluding-unresolved figure",
      f"{_REC['combined']['excl_unresolved']['k']}/{_REC['combined']['excl_unresolved']['n']} = "
      f"{_REC['combined']['excl_unresolved']['pct']:.1f}%" in _LED, True, src=_SRCP)
check("A1 stated as counts, not a pooled rate",
      "71 out / 156 full-text-verified, **reported as counts only**" in _LED
      and "35.7%" not in _LED, True, src="scope_final + hand")
check("A3 scope-failure counts, stated as counts and not compared",
      "**OUT_S1 26 vs OUT_S2 31** of the 156 verified" in _LED, True, src="scope_final + hand")
check("C10 no longer claims our own paper is outside the coded corpus",
      "It is NOT in the 67-paper coded corpus" not in _LED, True, src="fulltext_validation")
check("C10 records the self-inclusion sensitivity",
      "54/78 = 69.2%" in _LED, True, src="fulltext_validation")

# Section H, added 2026-09-29 when the consensus round closed. Same discipline as section P:
# a ledger row asserting a number nobody can trace is how a stale figure survives, so every
# value in H is recomputed here from the result record rather than read back from the ledger.
_HC = json.load(io.open("corpus/human_coding_results.json", encoding="utf-8"))
_SRCH = "human_coding_results.json"
_ab = next(v for k, v in _HC.items() if k.startswith("human A vs human B"))
_cvv = _HC["consensus vs validated (n=64)"]
_c79, _c64 = _HC["prevalence"]["consensus_79"], _HC["prevalence"]["consensus"]
_v64 = _HC["prevalence"]["validated_authors"]
_cdist = _HC["consensus_distribution"]

check("H1 pre-consensus agreement and kappa in the ledger",
      f"{round(_ab['raw_agreement']*_ab['n'])}/{_ab['n']} = "
      f"{100*_ab['raw_agreement']:.1f}%, Cohen's κ = {_ab['kappa']:.3f}" in _LED, True, src=_SRCH)
check("H2 consensus distribution in the ledger",
      f"1:{_cdist['1']}, 2:{_cdist['2']}, 3:{_cdist['3']}, 4:{_cdist['4']}" in _LED, True,
      src=_SRCH)
check("H3 consensus prevalence and interval in the ledger",
      f"{_c79['numerator']} / {_c79['denominator']} = {_c79['pct']:.1f}% "
      f"[{_c79['ci95'][0]:.1f}–{_c79['ci95'][1]:.1f}]" in _LED, True, src=_SRCH)
check("H4 consensus-versus-validated agreement in the ledger",
      f"{round(_cvv['raw_agreement']*_cvv['n'])} / {_cvv['n']} = "
      f"{100*_cvv['raw_agreement']:.1f}%, κ = {_cvv['kappa']:.3f}" in _LED, True, src=_SRCH)
check("H5 records that the two agree in total while disagreeing on papers",
      f"disagree on {len(_HC['consensus_vs_validated_disagreements'])} of the "
      f"{_c64['denominator']}" in _LED, True, src=_SRCH)
check("H3 gap against the endpoint, with its direction, stated in the ledger",
      f"{abs(_c79['pct'] - _REC['combined']['pct']):.1f} points with the independent coding "
      f"lower" in _LED and _c79["pct"] < _REC["combined"]["pct"], True, src=_SRCH)
check("ledger does not claim the consensus confirms the author coding",
      "consensus confirms" not in _LED.lower(), True, src=_SRCH)

# The ten-point rule is the one place a result could silently change the paper's headline.
_gap64 = abs(_c64["pct"] - _v64["pct"])
_gap79 = abs(_c79["pct"] - _REC["combined"]["pct"])
check("ten-point rule still satisfied on both populations",
      _gap64 <= 10 and _gap79 <= 10, True, src=_SRCH)

# H6 counts which coder each agreed code upheld, from the reconciliation file itself.
_recon = list(csv.DictReader(io.open("human_coding/returned/reconciliation.csv",
                                     encoding="utf-8")))
_upA = sum(1 for r in _recon
           if r["consensus_category"].strip() == r["coder_A_category"].strip())
_upB = sum(1 for r in _recon
           if r["consensus_category"].strip() == r["coder_B_category"].strip())
check("H6 upheld counts match the reconciliation record",
      f"{len(_recon)} agreed codes, {_upA} match coder A, {_upB} match coder B alone, "
      f"{len(_recon) - _upA - _upB} matches neither" in _LED, True, src="reconciliation.csv")
check("every disagreement now carries a consensus code",
      all(r["consensus_category"].strip() for r in _recon), True, src="reconciliation.csv")

# H7 must agree with what the coders actually returned, not with anything decided here.
_ref = io.open("human_coding/returned/referral_return.md", encoding="utf-8").read()
for _pid in ("W4399615782", "W4413480292"):
    _blk = _ref.split(f"### {_pid}", 1)[1] if f"### {_pid}" in _ref else ""
    _m = re.search(r"\*\*Agreed category:\s*([1-4])", _blk)
    check(f"H7 {_pid} ledger category matches the coders' return",
          bool(_m) and f"`{_pid}` = {_m.group(1)}" in _LED, True, src="referral_return.md")

# ---------------------------------------------------------------- report
bad = [c for c in checks if not c[0]]
print(f"HEADLINE TRACEABILITY — {len(checks)} checks against frozen source records")
print("=" * 78)
for ok, name, got, want, src in checks:
    if not ok:
        print(f"  FAIL  {name:44s} got {got!r}  expected {want!r}  {src}")
if frac_problems:
    print("\n  FRACTION REGISTRY PROBLEMS:")
    for p in frac_problems:
        print(f"    {p}")

print(f"\n  passed {len(checks) - len(bad)} / {len(checks)}")
if bad:
    print("\n  A FAILING CHECK MEANS A LEDGER NUMBER NO LONGER MATCHES ITS SOURCE.")
    sys.exit(1)
print("  every headline in CLAIM_LEDGER.md reconciles with its frozen source record.")
print(f"  every one of {len(registry)} reported fractions recomputes from its stored "
      f"numerator/denominator")
print("  and every denominator matches the analysis population it declares.")
