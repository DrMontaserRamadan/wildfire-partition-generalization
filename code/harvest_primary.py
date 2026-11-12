import urllib.request, urllib.parse, json, time, sys, re
MAIL="your-email@example.org"; BASE="https://api.openalex.org/works"
SEL="id,doi,title,publication_year,type,cited_by_count,primary_location,authorships,abstract_inverted_index,open_access,referenced_works_count"

def q(filters,cursor="*"):
    p={"filter":",".join(filters),"per_page":"200","cursor":cursor,"mailto":MAIL,"select":SEL}
    url=BASE+"?"+urllib.parse.urlencode(p,safe=":,|<>-")
    for a in range(5):
        try:
            with urllib.request.urlopen(url,timeout=120) as r: return json.load(r)
        except Exception as e:
            if a==4: raise
            time.sleep(3*(a+1))

def harvest(filters,label,cap=6000):
    out,cur=[],"*"
    while True:
        d=q(filters,cur); out.extend(d["results"])
        cur=d["meta"].get("next_cursor")
        if not cur or not d["results"] or len(out)>=cap: break
    print(f"  {label}: {len(out)}",file=sys.stderr); return out

FIRE='(wildfire OR wildfires OR "forest fire" OR "forest fires" OR "wildland fire" OR bushfire OR "flame detection" OR "smoke detection")'
QUERIES = {
 "vision":  f'title_and_abstract.search:{FIRE} AND ("deep learning" OR CNN OR "convolutional" OR YOLO OR "computer vision" OR "neural network" OR transformer OR "image classification" OR "object detection")',
 "uav":     f'title_and_abstract.search:{FIRE} AND (UAV OR "unmanned aerial" OR drone OR "aerial vehicle" OR quadcopter)',
 "iot":     f'title_and_abstract.search:{FIRE} AND ("internet of things" OR IoT OR "wireless sensor network" OR WSN OR LoRa OR LoRaWAN OR ZigBee OR "sensor node" OR "sensor nodes")',
 "edge":    f'title_and_abstract.search:{FIRE} AND ("edge computing" OR "edge AI" OR TinyML OR embedded OR microcontroller OR "on-device" OR "real-time detection")',
 "sat":     f'title_and_abstract.search:{FIRE} AND (satellite OR MODIS OR VIIRS OR Sentinel OR Landsat OR "remote sensing") AND (detect OR "active fire" OR "early detection")',
}
all_w={}
for k,f in QUERIES.items():
    for w in harvest([f,"from_publication_date:2019-01-01","type:article|preprint|book-chapter|proceedings-article"],k):
        all_w.setdefault(w["id"],{"w":w,"tags":set()})["tags"].add(k)

def inv2abs(inv):
    if not inv: return ""
    pos={}
    for word,idxs in inv.items():
        for i in idxs: pos[i]=word
    return " ".join(pos[i] for i in sorted(pos))[:2500]

rows=[]
for rec in all_w.values():
    w=rec["w"]; loc=w.get("primary_location") or {}; src=(loc.get("source") or {}) or {}
    rows.append({"id":w["id"].split("/")[-1],"doi":(w.get("doi") or "").replace("https://doi.org/",""),
      "title":w.get("title") or "","year":w.get("publication_year"),"type":w.get("type"),
      "cites":w.get("cited_by_count"),"venue":src.get("display_name") or "",
      "src_type":src.get("type") or "","publisher":src.get("host_organization_name") or "",
      "oa":(w.get("open_access") or {}).get("is_oa"),
      "oa_url":(w.get("open_access") or {}).get("oa_url") or "",
      "nrefs":w.get("referenced_works_count"),
      "authors":[a["author"]["display_name"] for a in (w.get("authorships") or [])][:12],
      "tags":sorted(rec["tags"]),"abstract":inv2abs(w.get("abstract_inverted_index"))})
rows.sort(key=lambda r:(-(r["cites"] or 0)))
json.dump(rows,open("corpus/primary_raw.json","w",encoding="utf-8"),indent=1,ensure_ascii=False)
from collections import Counter
print("TOTAL UNIQUE:",len(rows))
print("by tag:",Counter(t for r in rows for t in r["tags"]))
print("by year:",sorted(Counter(r["year"] for r in rows).items()))
