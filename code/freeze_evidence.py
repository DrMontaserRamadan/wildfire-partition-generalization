"""
Freeze the verified evidence artifacts with checksums.

Anything listed here is FROZEN: it may be added to, but any change to an existing value must
be deliberate, recorded in the audit trail, and re-frozen. Re-running this script reports any
file whose checksum has changed since the last freeze, so silent drift is impossible.
"""
import os, json, hashlib, datetime, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

FROZEN = [
    # Contribution 1 - FLAME protocol drift
    "notes/RESULTS_flame_protocol_drift.md",
    "corpus/flame_timeline.json",
    # Contribution 2 - benchmark contamination (measurement + method + consequence)
    "notes/RESULTS_overlap_audit.md",
    "scripts/overlap_audit.py",
    "scripts/contamination_taxonomy.py",
    "scripts/decontamination_experiment.py",
    "scripts/confound_control.py",
    "corpus/overlap_summary.json",
    "corpus/overlap_pairs.json",
    "corpus/contamination_taxonomy.json",
    "corpus/decontamination_results.json",
    "corpus/confound_control_results.json",
    "corpus/provenance_control_results.json",
    "scripts/provenance_control.py",
    "notes/FLAME_GENEALOGY.md",
    "notes/NOVELTY_AUDIT.md",
    "CHECKPOINT.md",
    "corpus/ds_roots.json",
    # Coding reliability
    "notes/RESULTS_coding_reliability.md",
    "corpus/coded_A.json",
    "corpus/coded_B.json",
    "corpus/agreement.json",
    "scripts/agreement.py",
    "RUBRIC.md",
    # Sampling
    "corpus/UNIVERSE_FROZEN.json",
    "corpus/retrieval_table.csv",
    "scripts/freeze_universe.py",
    # Governance
    "CLAIM_EVIDENCE_MATRIX.md",
    "notes/AUDIT_TRAIL.md",

    # scope screen — the abstract decisions are frozen BEFORE any full text was opened, so
    # that the calibration in scope_calibrate.py cannot have been fitted after the fact
    "notes/SCOPE_SCREEN_RUBRIC.md",
    "corpus/scope_screen_packet.json",
    "corpus/scope_abstract_decisions.json",
    "corpus/scope_ft/ALL.tsv",
    "corpus/scope_final.json",
    "corpus/scope_table.csv",
    "corpus/scope_calibration.json",
    "notes/RESULTS_scope_screen.md",
    "scripts/scope_screen_build.py",
    "scripts/scope_freeze_abstract.py",
    "scripts/scope_fulltext_probe.py",
    "scripts/scope_calibrate.py",
    "scripts/scope_final.py",
    "corpus/scope_tierA_packet.json",
    "corpus/scope_ft/tierA.tsv",
    "scripts/scope_tierA_probe.py",
    "scripts/prep_coding.py",
    "scripts/test_coding_excerpts.py",
    "corpus/to_code.json",
    "corpus/raw_coding/coded_A_r2.RAW.json",
    "corpus/raw_coding/coded_B_r2.RAW.json",
    "corpus/raw_coding/README.md",
    "corpus/control_r2_carried.json",
    "corpus/agreement_r2.json",
    "corpus/agreement_r2_on_carried7.json",
    "corpus/reliability_comparison.json",
    "corpus/scope_sensitivity.json",
    "notes/RESULTS_coding_reliability_r2.md",
    "scripts/reliability_compare.py",
    "scripts/scope_sensitivity.py",
    "scripts/lopo.py",
    "notes/CODER_ALLOCATION_DESIGN.md",
    "scripts/coder_provenance.py",
    "PRE_CODING_FREEZE.md",
    "notes/CODER_BRIEF_67.md",
    "notes/NOVELTY_CHECKS_2026-09-11.md",
    "corpus/INSTRUMENT_FREEZE.json",
    "corpus/frozen_corpus_67.json",
    "corpus/reported_fractions.json",
    "scripts/freeze_instrument.py",
    "scripts/reported_fractions.py",
    "scripts/emit_scope_fractions.py",
    "scripts/merge_shards.py",
    "scripts/reliability_67.py",
    "scripts/prevalence.py",
    "CHECKPOINT_67.md",
    "drafts/manuscript_v2.md",
    "CHANGE_AUDIT_v1_to_v2.md",
    "corpus/fulltext_validation.json",
    "corpus/fulltext_validation_packet.json",
    "corpus/validation/ALL.tsv",
    "corpus/acquisition_bias.json",
    "scripts/fulltext_validation_build.py",
    "scripts/fulltext_validation_compare.py",
    "scripts/acquisition_bias.py",
    "drafts/manuscript_v1.md",
    "scripts/verify_manuscript.py",
    "FINAL_GATE.md",
    "scripts/rename_overlap_taxonomy.py",
    "MANUSCRIPT_ARCHITECTURE.md",
    "notes/CONTAMINATION_FINDINGS_67.md",
    "corpus/raw_coding/coded_A_67.RAW.json",
    "corpus/raw_coding/coded_B_67.RAW.json",
    "corpus/raw_coding/hash_history.json",
    "corpus/reliability_67.json",
    "corpus/prevalence.json",
    "corpus/sensitivity_matrix.json",
    "corpus/coder_provenance.json",
    "scripts/sensitivity_matrix.py",
    "scripts/capture_transcript_audits.py",
    "CLAIM_LEDGER.md",
    "CHECKPOINT_R2.md",
    "notes/RESULTS_lopo.md",
    "scripts/verify_headlines.py",
    "scripts/make_figure3.py",
    "figures/figure3_protocol_separation.png",
    "FIGURES.md",
    "FRAMEWORK.md",
    "notes/CODER_BRIEF_r2.md",
    "corpus/control_set_r2.json",
    "scripts/build_control_set_r2.py",
    "corpus/agreement_r1_on_carried7.json",
]

MANIFEST = "corpus/EVIDENCE_MANIFEST.json"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    prev = {}
    if os.path.exists(MANIFEST):
        prev = {r["path"]: r["sha256"] for r in json.load(open(MANIFEST))["files"]}

    files, missing, changed = [], [], []
    for p in FROZEN:
        if not os.path.exists(p):
            missing.append(p)
            continue
        s = sha(p)
        if p in prev and prev[p] != s:
            changed.append(p)
        files.append({"path": p, "sha256": s, "bytes": os.path.getsize(p)})

    payload = {
        "frozen_at": datetime.datetime.now().replace(microsecond=0).isoformat(),
        "n_files": len(files),
        "files": files,
        "missing_at_freeze": missing,
    }
    json.dump(payload, open(MANIFEST, "w"), indent=1)

    print(f"FROZEN {len(files)} artifacts")
    for f in files:
        print(f"  {f['sha256'][:12]}  {f['bytes']:10d}  {f['path']}")
    if missing:
        print(f"\nNOT YET PRESENT ({len(missing)}) - will be frozen when produced:")
        for m in missing:
            print(f"  - {m}")
    if changed:
        print(f"\n*** CHANGED SINCE LAST FREEZE ({len(changed)}) - must be justified in the "
              f"audit trail: ***")
        for c in changed:
            print(f"  ! {c}")
        sys.exit(2)
    print(f"\nmanifest -> {MANIFEST}")


if __name__ == "__main__":
    main()
