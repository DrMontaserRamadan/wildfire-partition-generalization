"""Issue PROTOCOL_FREEZE rev 3, preserving rev 2 unchanged as historical provenance.

Rev 2 recorded a sha256 for scripts/run_experiment.py that no surviving copy matches. The attested
bytes were never committed and are not in the object store; the file was edited during pilot
debugging on 2026-09-11 between the freeze being written at 14:30 and the commit at 15:29, and the
freeze was never refreshed. Rev 3 therefore cannot be a diff against rev 2 for that one file. It
records what was read instead, in FREEZE_REVERIFICATION_2026-09-15.md, and hashes the corrected
implementation.

This script refuses to run unless the verification suite has passed, because a freeze that attests
untested code is worse than no freeze: it lends the code authority it has not earned.

    python scripts/test_run_experiment.py && python scripts/write_freeze_rev3.py
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

FREEZE = "corpus/PROTOCOL_FREEZE.json"
REV2_COPY = "corpus/PROTOCOL_FREEZE_rev2.json"

# Everything rev 2 covered, plus the files the rev-3 corrections introduced. The evaluation policy
# now lives in run_experiment.py, the evidence it was chosen from in eval_policy_evidence.json, and
# the checks that hold it in place in test_run_experiment.py - all three belong under the freeze,
# because a policy nobody can verify was not changed is not frozen.
FILES = [
    "PARTITION_GRANULARITY_PROTOCOL.md",
    "HUMAN_CODING_PROTOCOL.md",
    "NOVELTY_AUDIT_PARTITION_EXPERIMENT.md",
    "FREEZE_REVERIFICATION_2026-09-15.md",
    "corpus/pyrosdis_partitions.json",
    "corpus/pyrosdis_profile.json",
    "corpus/pyrosdis_rows.json",
    "corpus/split_manifest.json",
    "corpus/dataset_manifest.json",
    "corpus/eval_policy_evidence.json",
    "scripts/pyrosdis_partitions.py",
    "scripts/pyrosdis_profile.py",
    "scripts/pyrosdis_extract.py",
    "scripts/split_manifest.py",
    "scripts/dataset_manifest.py",
    "scripts/eval_policy_evidence.py",
    "scripts/run_experiment.py",
    "scripts/run_all.py",
    "scripts/test_run_experiment.py",
]


def sha256(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def main():
    if not os.path.exists(FREEZE):
        sys.exit(f"ABORT: {FREEZE} is missing.")
    rev2 = json.load(io.open(FREEZE, encoding="utf-8"))
    if "rev 2" not in rev2.get("purpose", ""):
        sys.exit(f"ABORT: {FREEZE} does not look like rev 2. Refusing to overwrite it blindly.")

    missing = [f for f in FILES if not os.path.exists(f)]
    if missing:
        sys.exit(f"ABORT: files to be frozen are missing: {missing}")

    print("running the verification suite; the freeze is not written unless it passes")
    r = subprocess.run([sys.executable, "scripts/test_run_experiment.py"],
                       capture_output=True, text=True)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if r.returncode != 0 or "ALL PASS" not in tail:
        print(r.stdout[-3000:])
        sys.exit("\nABORT: the verification suite did not pass. Rev 3 is not written.")
    n_checks = r.stdout.count("PASS")
    print(f"  suite passed, {n_checks} checks")

    # Preserve rev 2 byte for byte before anything else touches the path.
    if not os.path.exists(REV2_COPY):
        io.open(REV2_COPY, "wb").write(io.open(FREEZE, "rb").read())
        print(f"  preserved rev 2 at {REV2_COPY}")
    else:
        if sha256(REV2_COPY) != sha256(FREEZE):
            sys.exit(f"ABORT: {REV2_COPY} exists but differs from {FREEZE}. "
                     "Resolve by hand; do not overwrite history.")
        print(f"  rev 2 already preserved at {REV2_COPY}")

    ds = json.load(io.open("corpus/dataset_manifest.json", encoding="utf-8"))
    rev3 = {
        "frozen_at": time.strftime("%Y-%m-%d"),
        "purpose": "partition-granularity experiment, pre-training freeze (rev 3)",
        "revision_reason":
            "three corrections applied before any experimental result existed, approved 2026-09-15: "
            "(1) the YOLO arms trained on a linear learning-rate schedule while section 6 specifies "
            "cosine and the torchvision arms implemented cosine; cos_lr is now set explicitly. "
            "(2) the section 4 secondary metrics - precision and recall at the F1-maximal operating "
            "point selected on the validation arm - were never computed, and the validation arm was "
            "never read; they are now computed, and checkpoints and raw predictions are persisted "
            "for all four architectures so they can be audited without retraining. "
            "(3) the four models predicted under three different library inference configurations, "
            "which depressed the two torchvision arms on a ranking comparison; one architecture-"
            "independent evaluation policy now applies to all four, chosen from measured corpus "
            "properties. The replicate count was also restored from 3 to 5 for P1, P2 and P3, "
            "giving 19 partitions and 76 runs, because the split-noise floor of section 7 is "
            "defined on 5 P1 replicates and is anti-conservative when estimated from 3.",
        "rev2_preserved_at": REV2_COPY,
        "rev2_note":
            "rev 2 recorded sha256 af96658ccc4947b7... for scripts/run_experiment.py. No surviving "
            "copy matches it: the working copy was 4f641b83dbe03ba3..., the committed blob "
            "68dfacc0b30157f0..., and all 15,595 unreachable blobs in the object store were "
            "searched without finding the attested bytes. The file was edited during pilot "
            "debugging between the freeze (14:30) and the commit (15:29) on 2026-09-11 and the "
            "freeze was not refreshed. Rev 3 therefore records a re-reading of the implementation "
            "against sections 4 to 6 of the protocol, in FREEZE_REVERIFICATION_2026-09-15.md, "
            "rather than a diff against bytes that no longer exist. The chronology is not rewritten.",
        "verification":
            f"scripts/test_run_experiment.py, {n_checks} checks, all passing at the time of "
            "freezing; all four architectures additionally run end to end on a truncated corpus.",
        "dataset_rollup_sha256": ds["rollup_sha256"],
        "dataset_n_files": ds["n_files"],
        "supersedes": {k: v for k, v in rev2.get("files", {}).items()},
        "files": {f: sha256(f) for f in FILES},
    }
    json.dump(rev3, io.open(FREEZE, "w", encoding="utf-8"), indent=1)

    print(f"\nwrote {FREEZE} as rev 3, {len(FILES)} files")
    print(f"  dataset rollup {ds['rollup_sha256'][:16]}  ({ds['n_files']:,} files)")
    for f in FILES:
        was = rev2.get("files", {}).get(f)
        now = rev3["files"][f]
        mark = "unchanged" if was == now else ("CHANGED " if was else "new     ")
        print(f"  {mark}  {f:<45} {now[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
