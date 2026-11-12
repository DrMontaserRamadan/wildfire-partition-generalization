import json, urllib.request, os, re, sys, time, hashlib
os.makedirs("corpus/ft", exist_ok=True)
rows=json.load(open("corpus/primary_clean.json",encoding="utf-8"))
q=[r for r in rows if r.get("oa") and r.get("oa_url") and (r["cites"] or 0)>=5 and r["year"]>=2020]
q.sort(key=lambda r:-(r["cites"] or 0))
sample=q[:int(sys.argv[1]) if len(sys.argv)>1 else 15]
UA={"User-Agent":"Mozilla/5.0 (research; your-email@example.org)"}
ok=fail=0
for r in sample:
    h=hashlib.md5(r["id"].encode()).hexdigest()[:12]
    pdf=f"corpus/ft/{h}.pdf"; txt=f"corpus/ft/{h}.txt"
    if os.path.exists(txt): ok+=1; continue
    try:
        req=urllib.request.Request(r["oa_url"],headers=UA)
        data=urllib.request.urlopen(req,timeout=60).read()
        if data[:4]==b"%PDF":
            open(pdf,"wb").write(data)
            os.system(f'pdftotext -layout "{pdf}" "{txt}" 2>/dev/null')
            if os.path.exists(txt) and os.path.getsize(txt)>3000:
                ok+=1; print(f"  OK  {os.path.getsize(txt):7d}B  {r['title'][:65].encode('ascii','replace').decode()}")
            else: fail+=1; print(f"  THIN {r['oa_url'][:60]}")
        else:
            fail+=1; print(f"  NOTPDF {r['oa_url'][:70]}")
    except Exception as e:
        fail+=1; print(f"  ERR {type(e).__name__} {r['oa_url'][:60]}")
    time.sleep(0.6)
print(f"\nFetched OK={ok} FAIL={fail}  (pool of eligible OA papers: {len(q)})")
