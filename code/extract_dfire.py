import pyarrow.parquet as pq, os, io, sys
from PIL import Image
OUT="datasets/dfire_test"
os.makedirs(OUT,exist_ok=True)
n=0
for f in sorted(os.listdir("datasets/dfire_pq")):
    if not f.endswith(".parquet"): continue
    p=os.path.join("datasets/dfire_pq",f)
    if os.path.getsize(p)<1000: continue
    pf=pq.ParquetFile(p)
    print(f"{f}: {pf.metadata.num_rows} rows, cols={pf.schema_arrow.names}",flush=True)
    for batch in pf.iter_batches(batch_size=64):
        d=batch.to_pydict()
        imgs=d.get("image") or d.get("img")
        if imgs is None:
            print("  no image column"); break
        for i,rec in enumerate(imgs):
            b = rec.get("bytes") if isinstance(rec,dict) else rec
            if not b: continue
            try:
                im=Image.open(io.BytesIO(b)); im.load()
                im.convert("RGB").save(os.path.join(OUT,f"dfire_{n:06d}.jpg"),quality=92)
                n+=1
            except Exception: pass
        if n and n%500==0: print(f"  extracted {n}",flush=True)
print("TOTAL EXTRACTED:",n)
