"""Provenance and blinding audit for the eight coder instances.

Runs BEFORE any substantive result is examined. Hashes every raw output, records completion
time and size, and searches each agent transcript for tool calls that touched a forbidden file.

Distinguishes three kinds of access, because conflating them would either hide a real breach or
manufacture a false one:

  SELF      — the instance reading or validating its OWN output file. Harmless and expected.
  SHARD     — an instance reading a shard that is not its own. A breach of the allocation.
  CROSS     — an instance reading another ROLE's output, a previous round's coding, an
              agreement or reliability file, the analysis plan, or any results document.
              This is the breach that would invalidate independence.

A finding is reported, never silently repaired. Re-running a coder because its output is
inconvenient is not an available response.
"""
import json
import io
import os
import re
import sys
import glob
import hashlib
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TASKDIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "Temp", "claude",
    "C--Users-info-Documents-my-project-new-papers-review-paper-fire-detection",
    "d3253af5-b958-4303-bb8c-1e692a65799d", "tasks")

# files that would compromise independence if a coder opened them
CROSS_PATTERNS = [
    r"coded_[AB]_r2", r"coded_[AB]\.json", r"agreement", r"reliability_",
    r"PRE_CODING_FREEZE", r"RESULTS_", r"CHECKPOINT", r"CLAIM_LEDGER",
    r"FRAMEWORK\.md", r"prevalence", r"scope_sensitivity", r"lopo",
    r"NOVELTY", r"verify_headlines",
]
TOOL_RE = re.compile(r'"name"\s*:\s*"(Read|Bash|Grep|Glob|Edit|Write)"')


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def audit_transcript(path, role, shard):
    """Return (self_hits, shard_hits, cross_hits) as lists of short descriptions."""
    selfh, shardh, crossh = [], [], []
    own = f"coded_{role}_67_shard{shard}"
    own_shard = f"shard_{shard}.json"
    if not os.path.exists(path):
        return None
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"name"' not in line:
                continue
            for m in TOOL_RE.finditer(line):
                seg = line[m.start():m.start() + 1500]
                if own in seg:
                    selfh.append("own output")
                    continue
                mo = re.search(r"shard_(\d)\.json", seg)
                if mo and mo.group(0) != own_shard:
                    shardh.append(mo.group(0))
                other_role = "B" if role == "A" else "A"
                if re.search(rf"coded_{other_role}_67", seg):
                    crossh.append(f"other role output ({other_role})")
                for pat in CROSS_PATTERNS:
                    if re.search(pat, seg):
                        crossh.append(pat)
    return selfh, shardh, crossh


def main():
    inst = json.load(io.open("corpus/INSTRUMENT_FREEZE.json", encoding="utf-8"))
    print("CODER PROVENANCE AND BLINDING AUDIT")
    print("=" * 92)
    print(f"instrument frozen: corpus sha256 {inst['corpus_sha256'][:16]}..., "
          f"{inst['n_papers']} papers, {inst['n_shards']} shards")
    print("allocation: role A = 4 instances, role B = 4 instances, identical shard boundaries,")
    print("            every paper rated exactly once per role, zero singly-coded papers.\n")

    # map agent transcripts to (role, shard) by the output file each one wrote
    # Stream each transcript rather than reading a fixed prefix: the identifying filename can
    # appear anywhere, and a prefix-only scan silently failed to attribute most instances.
    transcripts = sorted(glob.glob(os.path.join(TASKDIR, "*.output")))
    owner = {}
    ident = re.compile(r"coded_([AB])_67_shard(\d)")
    for t in transcripts:
        try:
            with io.open(t, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = ident.search(line)
                    if m:
                        key = (m.group(1), int(m.group(2)))
                        owner.setdefault(key, t)
                        break
        except OSError:
            continue

    rows, problems = [], []
    for role in ("A", "B"):
        for shard in range(4):
            p = f"corpus/raw_coding/coded_{role}_67_shard{shard}.json"
            rec = {"role": role, "shard": shard, "file": p}
            if not os.path.exists(p):
                rec.update(status="MISSING", sha256=None, n=None)
                problems.append(f"{role}{shard}: output MISSING — coder did not complete")
            else:
                st = os.stat(p)
                try:
                    n = len(json.load(io.open(p, encoding="utf-8")))
                    status = "ok"
                except ValueError as e:
                    n, status = None, f"UNPARSEABLE: {e}"
                    problems.append(f"{role}{shard}: {status}")
                rec.update(status=status, sha256=sha(p), n=n, bytes=st.st_size,
                           completed=datetime.datetime.fromtimestamp(st.st_mtime)
                           .replace(microsecond=0).isoformat())
            # Prefer an audit captured while the agent was still running. Agent transcripts in
            # this environment are written lazily and TRUNCATED TO ZERO BYTES on completion, so
            # a post-hoc transcript audit is unavailable for most instances. That is a real
            # limitation of the verification, not a finding about the coders, and it is
            # reported as such rather than glossed.
            cap = f"corpus/coder_transcripts/{role}{shard}.audit.json"
            if os.path.exists(cap):
                c = json.load(io.open(cap, encoding="utf-8"))
                rec.update(transcript=c["transcript"], self_access=c["self_access"],
                           foreign_shard_access=c["foreign_shard_access"],
                           cross_access=c["cross_access"],
                           blinding_evidence="transcript captured live")
                if c["foreign_shard_access"]:
                    problems.append(f"{role}{shard}: read a foreign shard "
                                    f"{c['foreign_shard_access']}")
                if c["cross_access"]:
                    problems.append(f"{role}{shard}: CROSS ACCESS {c['cross_access']}")
            else:
                t = owner.get((role, shard))
                res = audit_transcript(t, role, shard) if t else None
                if res and any(res):
                    selfh, shardh, crossh = res
                    rec.update(transcript=os.path.basename(t), self_access=len(selfh),
                               foreign_shard_access=sorted(set(shardh)),
                               cross_access=sorted(set(crossh)),
                               blinding_evidence="transcript read post-hoc")
                    if shardh:
                        problems.append(f"{role}{shard}: read a foreign shard "
                                        f"{sorted(set(shardh))}")
                    if crossh:
                        problems.append(f"{role}{shard}: CROSS ACCESS {sorted(set(crossh))}")
                else:
                    rec.update(transcript=None, self_access=None,
                               foreign_shard_access=None, cross_access=None,
                               blinding_evidence="UNAVAILABLE - transcript truncated on "
                                                 "completion")
            rows.append(rec)

    print(f"{'coder':6s} {'n':>3s} {'status':10s} {'completed':20s} {'sha256':18s} "
          f"{'self':>5s} {'foreign':>8s} {'cross':>6s}")
    print("-" * 92)
    for r in rows:
        print(f"{r['role']}{r['shard']:<5d} {str(r['n'] or '-'):>3s} {r['status'][:10]:10s} "
              f"{str(r.get('completed', '-')):20s} {(r['sha256'] or '-')[:16]:18s} "
              f"{str(r['self_access']):>5s} "
              f"{str(len(r['foreign_shard_access'] or [])) if r['cross_access'] is not None else '?':>8s} "
              f"{str(len(r['cross_access'] or [])) if r['cross_access'] is not None else '?':>6s}")

    # Distinguish VERIFIED-CLEAN from UNVERIFIABLE. Reporting "no contamination found" when
    # most instances could not be checked would be a green tick standing in for evidence.
    verified = [r for r in rows if r.get("blinding_evidence", "").startswith("transcript")]
    unver = [r for r in rows if not r.get("blinding_evidence", "").startswith("transcript")]

    print("\n" + "=" * 92)
    print("BLINDING VERIFICATION COVERAGE")
    print(f"  transcript-verified clean : {len(verified)} of {len(rows)}"
          + (f"  ({', '.join(r['role'] + str(r['shard']) for r in verified)})" if verified else ""))
    print(f"  UNVERIFIABLE              : {len(unver)} of {len(rows)}"
          + (f"  ({', '.join(r['role'] + str(r['shard']) for r in unver)})" if unver else ""))
    if unver:
        print("  Agent transcripts are truncated to zero bytes on completion in this")
        print("  environment, so a post-hoc audit is impossible for those instances.")
        print("  This is a limitation of the VERIFICATION, not a finding about the coders.")
        print("  Structural evidence for those instances is in")
        print("  notes/CONTAMINATION_FINDINGS_67.md (F2) and must be reported alongside.")

    print("\n" + "=" * 92)
    if problems:
        print(f"FINDINGS ({len(problems)}) — reported, not repaired:")
        for p in problems:
            print("  " + p)
    else:
        print("NO CONTAMINATION DETECTED IN THE EVIDENCE AVAILABLE.")
        print(f"  Of {len(rows)} instances, {len(verified)} could be checked directly and")
        print(f"  showed self-access only; {len(unver)} could not be checked at all.")
        print("  This is NOT a clean bill of health for all eight.")

    # What ran the instrument. Recorded 2026-10-10, as a provenance statement with its own
    # evidence and its own stated limit, because the manuscript had promised to disclose the
    # model and no artifact named anything at all.
    #
    # The family and the access route are attested by the operator and corroborated by this
    # project's own execution environment: every shard's transcript is a harness output file
    # of the form <id>.output, and seven of the eight were truncated to zero bytes on
    # completion, which is that harness's behaviour. The VERSION is not recoverable. It is
    # absent from every frozen artifact, the one surviving transcript no longer exists on
    # disk, and the session records for 2026-09-11 show two different model versions in use on
    # that date, so no version can be inferred from a neighbouring session either. An
    # identifier is therefore stated to the precision the record supports and no further.
    runtime = {
        "family": "Claude",
        "access_route": "Claude Code command-line interface",
        "version_identifier": None,
        "version_recoverable": False,
        "attested_by": "the operator; corroborated by the harness transcript artifacts",
        "n_instances": len(rows),
        "n_roles": len({r["role"] for r in rows}),
        "n_shards": len({r["shard"] for r in rows}),
        "coded_between": [min(r["completed"] for r in rows),
                          max(r["completed"] for r in rows)],
        "why_no_version": ("no version identifier appears in coder_provenance, "
                           "INSTRUMENT_FREEZE or the raw coding rows; the single surviving "
                           "transcript is no longer on disk; and two model versions were in "
                           "use on the coding date, so none can be inferred"),
    }
    json.dump({"runtime": runtime, "rows": rows, "problems": problems},
              io.open("corpus/coder_provenance.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nwrote corpus/coder_provenance.json")
    return 1 if any("CROSS ACCESS" in p or "foreign shard" in p for p in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
