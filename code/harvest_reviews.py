import urllib.request, urllib.parse, json, time, re, sys

MAIL = "your-email@example.org"
BASE = "https://api.openalex.org/works"

def q(filters, per_page=200, cursor="*", select=None):
    p = {"filter": ",".join(filters), "per_page": str(per_page), "cursor": cursor, "mailto": MAIL}
    if select: p["select"] = select
    url = BASE + "?" + urllib.parse.urlencode(p, safe=":,|<>-")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 3: raise
            time.sleep(3*(attempt+1))

SEL = "id,doi,title,publication_year,type,cited_by_count,primary_location,authorships,abstract_inverted_index"

def harvest(filters, label):
    out, cursor = [], "*"
    while True:
        d = q(filters, cursor=cursor, select=SEL)
        out.extend(d["results"])
        cursor = d["meta"].get("next_cursor")
        if not cursor or not d["results"]: break
        if len(out) > 4000: break
    print(f"{label}: {len(out)}", file=sys.stderr)
    return out

TOPIC = "(wildfire OR wildfires OR \"forest fire\" OR \"forest fires\" OR bushfire OR \"wildland fire\")"

# 1. All review-type works about fire detection since 2019
rev = harvest([
    f"title_and_abstract.search:{TOPIC} AND (detection OR monitoring OR sensing OR prediction)",
    "type:review",
    "from_publication_date:2019-01-01",
], "reviews(type=review)")

# 2. Works with review/survey in the TITLE (many are typed 'article')
rev2 = harvest([
    f"title.search:{TOPIC} AND (review OR survey OR \"systematic\" OR taxonomy OR \"state of the art\")",
    "from_publication_date:2019-01-01",
], "reviews(title match)")

seen, merged = set(), []
for w in rev + rev2:
    if w["id"] in seen: continue
    seen.add(w["id"]); merged.append(w)

def inv2abs(inv):
    if not inv: return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs: pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))[:1800]

rows = []
for w in merged:
    loc = w.get("primary_location") or {}
    src = (loc.get("source") or {}) or {}
    rows.append({
        "id": w["id"].split("/")[-1],
        "doi": (w.get("doi") or "").replace("https://doi.org/",""),
        "title": w.get("title") or "",
        "year": w.get("publication_year"),
        "type": w.get("type"),
        "cites": w.get("cited_by_count"),
        "venue": src.get("display_name") or "",
        "issn_l": src.get("issn_l") or "",
        "publisher": src.get("host_organization_name") or "",
        "abstract": inv2abs(w.get("abstract_inverted_index")),
    })
rows.sort(key=lambda r: (-(r["year"] or 0), -(r["cites"] or 0)))
json.dump(rows, open("corpus/reviews_landscape.json","w",encoding="utf-8"), indent=1, ensure_ascii=False)
print("TOTAL merged:", len(rows))
from collections import Counter
print("by year:", sorted(Counter(r["year"] for r in rows).items()))
print("top venues:", Counter(r["venue"] for r in rows).most_common(25))
