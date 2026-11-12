import json,urllib.request,urllib.parse,os,re,time,sys,hashlib
os.makedirs("corpus/ft",exist_ok=True)
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
 "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"en-US,en;q=0.9"}
def get(u,t=50):
    try: return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=t).read()
    except Exception: return None
def h2t(b):
    s=b.decode("utf-8","ignore")
    s=re.sub(r"(?is)<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>"," ",s)
    s=re.sub(r"(?is)<br\s*/?>|</p>|</div>|</h\d>|</li>","\n",s)
    s=re.sub(r"(?s)<[^>]+>"," ",s)
    for a,b2 in [("&nbsp;"," "),("&amp;","&"),("&lt;","<"),("&gt;",">"),("&quot;",'"'),("&#x2014;","-")]: s=s.replace(a,b2)
    return re.sub(r"\n{3,}","\n\n",re.sub(r"[ \t]{2,}"," ",s))
def store(data,key,kind):
    if data[:4]==b"%PDF":
        p=f"corpus/ft/{key}.pdf"; open(p,"wb").write(data)
        os.system(f'pdftotext -layout "{p}" "corpus/ft/{key}.txt" 2>/dev/null')
        if os.path.exists(f"corpus/ft/{key}.txt") and os.path.getsize(f"corpus/ft/{key}.txt")>5000: return kind+"|pdf"
        for f in (p,f"corpus/ft/{key}.txt"):
            if os.path.exists(f): os.remove(f)
        return None
    txt=h2t(data)
    if len(txt)>6000 and re.search(r"(?i)\b(dataset|training set|experiment|methodolog|we (train|evaluat|test))",txt):
        open(f"corpus/ft/{key}.txt","w",encoding="utf-8").write(txt); return kind+"|html"
    return None

def cands(r):
    doi=r["doi"]
    if doi:
        j=get(f"https://api.unpaywall.org/v2/{doi}?email=your-email@example.org",40)
        if j:
            try:
                locs=(json.loads(j).get("oa_locations") or [])
                locs.sort(key=lambda l: 0 if l.get("host_type")=="repository" else 1)
                for l in locs:
                    if l.get("url_for_pdf"): yield ("repo" if l.get("host_type")=="repository" else "pub", l["url_for_pdf"])
                    if l.get("url"): yield ("repo" if l.get("host_type")=="repository" else "pub", l["url"])
            except Exception: pass
        j=get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%22{urllib.parse.quote(doi)}%22&format=json&resultType=core",40)
        if j:
            try:
                res=json.loads(j).get("resultList",{}).get("result",[])
                if res and res[0].get("pmcid"):
                    yield ("epmc",f"https://www.ebi.ac.uk/europepmc/webservices/rest/{res[0]['pmcid']}/fullTextXML")
            except Exception: pass
        j=get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf,externalIds",35)
        if j:
            try:
                o=json.loads(j)
                ax=(o.get("externalIds") or {}).get("ArXiv")
                if ax: yield ("arxiv",f"https://arxiv.org/pdf/{ax}")
                p=(o.get("openAccessPdf") or {}).get("url")
                if p: yield ("s2",p)
            except Exception: pass
    if r.get("oa_url"): yield ("oa",r["oa_url"])

sample=json.load(open("corpus/sample.json",encoding="utf-8"))
out=[]
for i,r in enumerate(sample):
    key=hashlib.md5(r["id"].encode()).hexdigest()[:12]; r["ftkey"]=key
    if os.path.exists(f"corpus/ft/{key}.txt") and os.path.getsize(f"corpus/ft/{key}.txt")>5000:
        r["ft"]="cached"; out.append(r); print(f"OK  {i+1}/182 [cached]",flush=True); continue
    r["ft"]=None; r["tried"]=[]
    for kind,u in cands(r):
        if not u: continue
        r["tried"].append(u[:110])
        d=get(u)
        if not d: continue
        res=store(d,key,kind)
        if res: r["ft"]=res; break
        time.sleep(0.2)
    print(f"{'OK ' if r['ft'] else '-- '}{i+1}/182 [{r['ft'] or 'FAIL'}] {r['title'][:58].encode('ascii','replace').decode()}",flush=True)
    out.append(r); time.sleep(0.3)
json.dump(out,open("corpus/sample_ft.json","w",encoding="utf-8"),indent=1,ensure_ascii=False)
from collections import Counter
print("\n=== ACQUIRED",sum(1 for r in out if r["ft"]),"/",len(out),"===")
print(Counter((r["ft"] or "FAIL").split("|")[0] for r in out))
