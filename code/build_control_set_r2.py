"""Build the round-2 control set.

Round 1 used 9 papers. Two of them are gone: one is out of scope (Sentinel-1 wildfire
PROGRESSION monitoring, i.e. burned-area growth) and one was a repository landing page with
no article text behind it. Seven survive.

The seven are carried forward deliberately. Round 2 exists to test whether a revised
split_protocol category set fixes a failure diagnosed in round 1, and that comparison is only
meaningful on the same papers — a new sample would confound the category change with a change
of material. Eight further papers are drawn stratified by modality so round 2 also reports on
a larger set.

Draw is deterministic: sorted by a hash of the paper id, no RNG, so re-running reproduces the
same control set without needing a stored seed.
"""
import json
import io
import os
import hashlib
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

N_NEW = 8

old = [c["paper_id"] for c in json.load(io.open("corpus/control_set.json", encoding="utf-8"))]
to_code = {o["paper_id"]: o for o in json.load(io.open("corpus/to_code.json", encoding="utf-8"))}

carried = [p for p in old if p in to_code]
dropped = [p for p in old if p not in to_code]

# stratify the new draw by modality, proportional to the codeable pool
pool = defaultdict(list)
for pid, o in to_code.items():
    if pid not in carried:
        pool[o["modality"]].append(pid)
for m in pool:
    pool[m].sort(key=lambda p: hashlib.sha256(("r2:" + p).encode()).hexdigest())

shares = Counter(o["modality"] for p, o in to_code.items() if p not in carried)
total = sum(shares.values())
new = []
for m, n in shares.most_common():
    take = max(1, round(N_NEW * n / total))
    new.extend(pool[m][:take])
new = new[:N_NEW]

control = carried + new
out = [dict(to_code[p], role="carried_from_round1" if p in carried else "new_stratified")
       for p in control]

json.dump(out, io.open("corpus/control_set_r2.json", "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)

print(f"round-1 control set : {len(old)}")
print(f"  carried forward   : {len(carried)}")
print(f"  dropped           : {len(dropped)}")
for p in dropped:
    print(f"      {p}")
print(f"new stratified draw : {len(new)}")
print(f"ROUND-2 CONTROL SET : {len(out)}")
print("\nby modality:", dict(Counter(o["modality"] for o in out)))
print("by role    :", dict(Counter(o["role"] for o in out)))
ex = sorted(o["chars_excerpt"] for o in out)
print(f"excerpt chars: median {ex[len(ex)//2]}, min {ex[0]}, max {ex[-1]}")
print("\nNOTE: report round-2 kappa BOTH on the 7 carried papers (directly comparable to")
print("round 1 restricted to the same 7) and on all 15. A category change tested on a")
print("different sample is not a test of the category change.")
