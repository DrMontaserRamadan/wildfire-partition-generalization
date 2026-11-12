import json, re
from collections import Counter
rows = json.load(open("corpus/reviews_landscape.json",encoding="utf-8"))

# must actually be a review/survey
REVW = re.compile(r"\b(review|survey|systematic|taxonom|state[- ]of[- ]the[- ]art|meta-?analys|bibliometric|scoping|overview|comparative study)\b", re.I)
# must be about detection technology, not ecology/health/policy
TECH = re.compile(r"\b(detect|monitor|sensing|sensor|surveill|deep learning|machine learning|neural|CNN|YOLO|UAV|drone|unmanned|IoT|internet of things|WSN|wireless sensor|LoRa|remote sensing|satellite|computer vision|image|edge comput|early warning|prediction|forecast|segmentation|classification)\b", re.I)
# exclude clearly off-topic domains
EXCL = re.compile(r"\b(smok(e|ing) inhalation|health effect|mental health|respirator|asthma|cardiovascul|mortalit|epidemiolog|soil|hydrolog|erosion|post-?fire vegetation recover|carbon emission|insurance|arthropod|bird|mammal|beetle|pollinator|fungal|seed|regeneration ecolog)\b", re.I)

keep=[]
for r in rows:
    blob = (r["title"]+" "+r["abstract"])
    if not REVW.search(r["title"]) and r["type"]!="review": continue
    if not TECH.search(blob): continue
    if EXCL.search(blob) and not TECH.search(r["title"]): continue
    if not r["venue"]: continue
    if re.search(r"zenodo|figshare|ssrn|preprint|osf|arxiv|research square|authorea", r["venue"], re.I): continue
    keep.append(r)

print("KEPT:", len(keep))
print("\nBY YEAR:", sorted(Counter(k["year"] for k in keep).items()))
print("\nTOP VENUES:")
for v,c in Counter(k["venue"] for k in keep).most_common(30): print(f"  {c:3d}  {v}")
json.dump(keep, open("corpus/reviews_filtered.json","w",encoding="utf-8"), indent=1, ensure_ascii=False)

print("\n=== MOST CITED (any year) ===")
for k in sorted(keep,key=lambda x:-(x["cites"] or 0))[:30]:
    print(f'{k["cites"]:5d} {k["year"]} | {k["venue"][:40]:40s} | {k["title"][:110]}')
