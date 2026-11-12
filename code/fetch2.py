import json,urllib.request,urllib.parse,os,re,time,sys,hashlib
os.makedirs("corpus/ft",exist_ok=True)
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept":"text/html,application/xhtml+xml,application/pdf,*/*","Accept-Language":"en-US,en;q=0.9"}
def get(u,timeout=60):
    try:
        return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=timeout).read()
    except Exception: return None

def save_pdf(data,key):
    p=f"corpus/ft/{key}.pdf"; t=f"corpus/ft/{key}.txt"
    open(p,"wb").write(data)
    os.system(f'pdftotext -layout "{p}" "{t}" 2>/dev/null')
    if os.path.exists(t) and os.path.getsize(t)>4000: return "pdf"
    if os.path.exists(t): os.remove(t)
    os.remove(p); return None

def save_txt(text,key):
    t=f"corpus/ft/{key}.txt"
    if len(text)>4000: open(t,"w",encoding="utf-8").write(text); return "html"
    return None

def html2text(b):
    try: s=b.decode("utf-8","ignore")
    except: return ""
    s=re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>"," ",s)
    s=re.sub(r"(?is)<br\s*/?>|</p>|</div>|</h\d>","\n",s)
    s=re.sub(r"(?s)<[^>]+>"," ",s)
    s=re.sub(r"&nbsp;|&#160;"," ",s); s=re.sub(r"&amp;","&",s)
    s=re.sub(r"&lt;","<",s); s=re.sub(r"&gt;",">",s); s=re.sub(r"&quot;",'"',s)
    return re.sub(r"[ \t]{2,}"," ",re.sub(r"\n{3,}","\n\n",s))

def routes(r):
    doi=r["doi"]
    # A: unpaywall -> repository & publisher pdfs
    if doi:
        j=get(f"https://api.unpaywall.org/v2/{doi}?email=your-email@example.org",45)
        if j:
            try:
                o=json.loads(j); locs=o.get("oa_locations") or []
                locs.sort(key=lambda l:(l.get("host_type")!="repository",))
                for l in locs:
                    for u in (l.get("url_for_pdf"),l.get("url")):
                        if u: yield ("unpaywall",u)
            except Exception: pass
    # B: europepmc full text
    if doi:
        j=get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%22{urllib.parse.quote(doi)}%22&format=json&resultType=core",45)
        if j:
            try:
                res=json.loads(j).get("resultList",{}).get("result",[])
                if res:
                    pmcid=res[0].get("pmcid")
                    if pmcid: yield ("epmc",f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML")
            except Exception: pass
    # C: MDPI direct (doi 10.3390) -> /pdf and /htm
    if doi.startswith("10.3390"):
        yield ("mdpi_htm", f"https://doi.org/{doi}")
    # D: oa_url from openalex last
    if r.get("oa_url"): yield ("oa_url",r["oa_url"])

sample=json.load(open("corpus/sample.json",encoding="utf-8"))
log=[]
lim=int(sys.argv[1]) if len(sys.argv)>1 else len(sample)
for i,r in enumerate(sample[:lim]):
    key=hashlib.md5(r["id"].encode()).hexdigest()[:12]; r["ftkey"]=key
    if os.path.exists(f"corpus/ft/{key}.txt"):
        r["ft"]="cached"; log.append(r); continue
    got=None
    for tag,u in routes(r):
        d=get(u)
        if not d: continue
        if d[:4]==b"%PDF": got=save_pdf(d,key)
        elif b"<article" in d[:4000] or b"<!DOCTYPE" in d[:200] or b"<html" in d[:200].lower():
            txt=html2text(d)
            if re.search(r"(?i)\b(method|dataset|experiment|result)",txt): got=save_txt(txt,key)
        if got: r["ft"]=tag; break
        time.sleep(0.3)
    if not got: r["ft"]=None
    log.append(r)
    st="OK " if got else "-- "
    print(f"{st}{i+1:3d}/{lim} [{r.get('ft') or 'FAIL'}] {r['title'][:62].encode('ascii','replace').decode()}",flush=True)
    time.sleep(0.4)
json.dump(log,open("corpus/sample_ft.json","w",encoding="utf-8"),indent=1,ensure_ascii=False)
ok=sum(1 for r in log if r.get("ft"))
print(f"\n=== FULL TEXT ACQUIRED: {ok}/{len(log)} ===")
from collections import Counter
print(Counter(r.get("ft") or "FAIL" for r in log))
