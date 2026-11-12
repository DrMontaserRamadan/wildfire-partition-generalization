"""Capture a blinding audit from each coder transcript WHILE the agent is still running.

Agent transcripts in this environment are written lazily and truncated to zero bytes once the
agent completes, so a post-hoc audit is impossible for most instances. This must therefore be
run repeatedly during the coding run. Each capture is written once and never overwritten, so an
audit taken while a transcript was still populated survives the truncation.

Records, per instance: how many tool calls touched its OWN output (harmless), any FOREIGN shard
(a breach of the allocation), and any CROSS access to another role's output, an earlier round,
the analysis plan, or a results document (the breach that would invalidate independence).
"""
import glob
import io
import os
import re
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TD = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Temp", "claude",
    "C--Users-info-Documents-my-project-new-papers-review-paper-fire-detection",
    "d3253af5-b958-4303-bb8c-1e692a65799d", "tasks")
OUT = "corpus/coder_transcripts"

IDENT = re.compile(r"coded_([AB])_67_shard(\d)")
TOOL = re.compile(r'"name"\s*:\s*"(Read|Bash|Grep|Glob|Edit|Write)"')
CROSS = [r"coded_[AB]_r2", r"coded_[AB]\.json", r"agreement", r"PRE_CODING_FREEZE",
         r"RESULTS_", r"CHECKPOINT", r"CLAIM_LEDGER", r"prevalence", r"reliability_",
         r"scope_sensitivity", r"\blopo\b", r"NOVELTY", r"verify_headlines"]


def main():
    os.makedirs(OUT, exist_ok=True)
    new = 0
    for t in sorted(glob.glob(os.path.join(TD, "*.output"))):
        if os.path.getsize(t) == 0:
            continue
        key = None
        with io.open(t, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = IDENT.search(line)
                if m:
                    key = (m.group(1), int(m.group(2)))
                    break
        if key is None:
            continue
        role, shard = key
        dest = os.path.join(OUT, f"{role}{shard}.audit.json")
        if os.path.exists(dest):
            continue  # never overwrite an earlier capture
        selfn, foreign, cross = 0, [], []
        with io.open(t, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"name"' not in line:
                    continue
                for m in TOOL.finditer(line):
                    seg = line[m.start():m.start() + 1500]
                    if f"coded_{role}_67_shard{shard}" in seg:
                        selfn += 1
                        continue
                    mo = re.search(r"shard_(\d)\.json", seg)
                    if mo and int(mo.group(1)) != shard:
                        foreign.append(mo.group(0))
                    other = "B" if role == "A" else "A"
                    if re.search(rf"coded_{other}_67", seg):
                        cross.append("other-role output")
                    for pat in CROSS:
                        if re.search(pat, seg):
                            cross.append(pat)
        json.dump({"role": role, "shard": shard, "transcript": os.path.basename(t),
                   "bytes": os.path.getsize(t), "self_access": selfn,
                   "foreign_shard_access": sorted(set(foreign)),
                   "cross_access": sorted(set(cross)),
                   "captured_while": "transcript still populated"},
                  io.open(dest, "w", encoding="utf-8"), indent=1)
        print(f"  captured {role}{shard}: self={selfn} foreign={sorted(set(foreign))} "
              f"cross={sorted(set(cross))}")
        new += 1
    have = sorted(os.path.basename(p)[:2] for p in glob.glob(os.path.join(OUT, "*.audit.json")))
    print(f"\n{new} new capture(s). Held: {have} ({len(have)} of 8)")


if __name__ == "__main__":
    main()
