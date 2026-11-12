import json, random, re
from collections import Counter, defaultdict
random.seed(20260909)
rows=json.load(open("corpus/primary_clean.json",encoding="utf-8"))

# eligibility: real detection-methods papers 2020+, indexed venue, has abstract
BAD=re.compile(r"arXiv|Research Square|DOAJ|Preprints|eBooks|international archives|Biodiversidade|Coimbra",re.I)
# must be a DETECTION/RECOGNITION methods paper, not spread/susceptibility/severity/ecology
DET=re.compile(r"\b(detect\w*|recogni\w*|classif\w*|identif\w*|segment\w*|early warning|monitor\w*|surveillance|localiz\w*|alarm)\b",re.I)
OFF=re.compile(r"\b(burn severity|susceptibilit|spread (model|predict|simulat)|risk (mapping|assess)|fuel (load|moisture|mapping)|post-?fire|emission|air quality|health|smoke exposure|evacuat|insurance|policy|recovery|regeneration|soil|hydrolog|carbon)\b",re.I)

elig=[]
for r in rows:
    if r["year"]<2020 or not r["venue"] or BAD.search(r["venue"]): continue
    blob=r["title"]+" "+r["abstract"]
    if not DET.search(r["title"]): continue
    # off-topic unless detection is clearly the subject of the title
    if OFF.search(r["title"]) and not re.search(r"\bdetect\w*|early warning|recogni\w*",r["title"],re.I): continue
    if len(r["abstract"])<250: continue
    elig.append(r)
print(f"Eligible detection-methods papers 2020+: {len(elig)}")

# primary modality (first matching, priority order) so strata are disjoint
def modality(r):
    t=set(r["tags"])
    if "iot" in t: return "iot"
    if "uav" in t: return "uav"
    if "sat" in t: return "satellite"
    if "edge" in t: return "edge"
    return "vision"
for r in elig: r["mod"]=modality(r)
print("Modality mix:",Counter(r["mod"] for r in elig))
print("Year mix:",sorted(Counter(r["year"] for r in elig).items()))

# Stratify: modality x year-band. Within stratum, take top-cited half + random half
# (so the sample is neither purely citation-biased nor purely random)
def band(y): return "2020-21" if y<=2021 else ("2022-23" if y<=2023 else "2024-26")
strata=defaultdict(list)
for r in elig: strata[(r["mod"],band(r["year"]))].append(r)

TARGET=180
tot=len(elig)
sample=[]
for k,v in sorted(strata.items()):
    n=max(4,round(TARGET*len(v)/tot))
    v_sorted=sorted(v,key=lambda x:-(x["cites"] or 0))
    n_top=n//2
    top=v_sorted[:n_top]
    rest=[x for x in v_sorted[n_top:]]
    rnd=random.sample(rest,min(n-n_top,len(rest)))
    picked=top+rnd
    sample.extend(picked)
    print(f"  {k[0]:10s} {k[1]:8s} pool={len(v):5d} -> n={len(picked):3d} (top{n_top}+rand{len(rnd)})")

# ensure the seed paper is in the sample (self-inclusion is the paper's credibility anchor)
seed=[r for r in rows if "10.1016/j.iot.2024.101248" in (r["doi"] or "")]
if seed and seed[0]["id"] not in {s["id"] for s in sample}:
    seed[0]["mod"]="iot"; sample.append(seed[0]); print("  + seed paper (Ramadan 2024) force-included")
elif seed: print("  seed paper already sampled")
else: print("  !! seed paper NOT FOUND in corpus - check")

print(f"\nSAMPLE SIZE: {len(sample)}")
print("by modality:",Counter(s["mod"] for s in sample))
print("by year:",sorted(Counter(s["year"] for s in sample).items()))
print("OA (fetchable):",sum(1 for s in sample if s.get("oa")),"/",len(sample))
json.dump(sample,open("corpus/sample.json","w",encoding="utf-8"),indent=1,ensure_ascii=False)
