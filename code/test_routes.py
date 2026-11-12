import json,urllib.request,urllib.parse,os,re,time,sys
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
def tryget(u,tag):
    try:
        d=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=45).read()
        return d
    except Exception as e:
        return None

rows=json.load(open("corpus/primary_clean.json",encoding="utf-8"))
dois=[r["doi"] for r in rows if r["doi"]][:6]
print("=== Route A: Unpaywall repository copies ===")
for d in dois[:5]:
    j=tryget(f"https://api.unpaywall.org/v2/{d}?email=your-email@example.org","")
    if j:
        o=json.loads(j); locs=o.get("oa_locations") or []
        repo=[l for l in locs if l.get("host_type")=="repository" and l.get("url_for_pdf")]
        print(f"  {d}: {len(locs)} oa_locs, {len(repo)} repo-pdf  {(repo[0]['url_for_pdf'][:70] if repo else '-')}")
    else: print(f"  {d}: unpaywall FAIL")

print("\n=== Route B: Europe PMC full text ===")
j=tryget("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%28wildfire%20OR%20%22forest%20fire%22%29%20AND%20%28detection%29%20AND%20OPEN_ACCESS%3AY&format=json&pageSize=1","")
print("  europepmc:", json.loads(j)["hitCount"] if j else "FAIL")

print("\n=== Route C: arXiv (425 in corpus) ===")
d=tryget("http://export.arxiv.org/api/query?search_query=all:wildfire+AND+all:detection&max_results=1","")
print("  arxiv:", "OK" if d and b"<entry>" in d else "FAIL")

print("\n=== Route D: MDPI with browser-ish headers (Fire/Forests/Sensors/RS = 700+ papers) ===")
d=tryget("https://www.mdpi.com/2571-6255/6/8/315/pdf","")
print("  mdpi pdf:", (d[:4] if d else "FAIL"), len(d) if d else "")

print("\n=== Route E: CORE ===")
d=tryget("https://api.core.ac.uk/v3/search/works?q=wildfire%20detection&limit=1","")
print("  core:", "OK" if d else "FAIL(needs key)")

print("\n=== Route F: OpenAlex all locations (repo PDFs) ===")
u="https://api.openalex.org/works?filter=title_and_abstract.search:wildfire%20detection,is_oa:true&per_page=25&select=id,title,locations&mailto=your-email@example.org"
j=tryget(u,"")
if j:
    ws=json.loads(j)["results"]; n=0
    for w in ws:
        pdfs=[l for l in (w.get("locations") or []) if l.get("pdf_url")]
        if pdfs: n+=1
    print(f"  {n}/{len(ws)} works expose >=1 direct pdf_url in locations")
