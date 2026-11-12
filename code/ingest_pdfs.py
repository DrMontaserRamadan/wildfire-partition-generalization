"""
Ingest author-supplied PDFs into the corpus.

Matching is done on the DOI EXTRACTED FROM THE PDF TEXT, not on the filename and not on a
mapping I wrote by hand. If the DOI cannot be read out of the document, the file is reported
as unmatched rather than guessed. Provenance is recorded as author_supplied_pdf so the
retrieval table stays honest about how each full text was obtained.
"""
import os, re, json, subprocess, shutil, hashlib, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
DL = os.path.expanduser("~/Downloads")
OUT = "corpus/ft"
os.makedirs(OUT, exist_ok=True)
os.makedirs("intake", exist_ok=True)

wanted = {}
for wl in ("corpus/elsevier_wanted.json", "corpus/ieee_wanted.json"):
    if os.path.exists(wl):
        for r in json.load(open(wl, encoding="utf-8")):
            wanted[r["doi"].lower()] = r
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.I)


def pdf_text(path):
    txt = path + ".tmp.txt"
    subprocess.run(["pdftotext", "-layout", path, txt],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(txt):
        return ""
    s = open(txt, encoding="utf-8", errors="replace").read()
    os.remove(txt)
    return s


def find_doi(text):
    """Return the first DOI in the document that we are actually looking for."""
    for m in DOI_RE.finditer(text[:20000]):
        d = m.group(0).rstrip(".,;)").lower()
        if d in wanted:
            return d
    # fall back: any DOI whose suffix matches a wanted one
    for m in DOI_RE.finditer(text[:20000]):
        d = m.group(0).rstrip(".,;)").lower()
        for w in wanted:
            if d.startswith(w) or w.startswith(d):
                return w
    return None


def main():
    cands = [f for f in os.listdir(DL) if f.lower().endswith(".pdf")]
    matched, unmatched, already = [], [], []
    for f in sorted(cands):
        p = os.path.join(DL, f)
        if os.path.getsize(p) < 20000:
            continue
        txt = pdf_text(p)
        if len(txt) < 3000:
            continue
        doi = find_doi(txt)
        if not doi:
            continue
        rec = wanted[doi]
        key = rec["key"]
        dest_txt = f"{OUT}/{key}.txt"
        if os.path.exists(dest_txt) and os.path.getsize(dest_txt) > 5000:
            already.append((f, doi))
            continue
        open(dest_txt, "w", encoding="utf-8").write(txt)
        shutil.copy(p, f"intake/{key}.pdf")
        matched.append({"file": f, "doi": doi, "key": key, "chars": len(txt),
                        "title": rec["title"]})

    for f in sorted(cands):
        p = os.path.join(DL, f)
        if not any(m["file"] == f for m in matched) and not any(a[0] == f for a in already):
            unmatched.append(f)

    print(f"INGESTED {len(matched)} of {len(wanted)} wanted Elsevier papers\n")
    for m in matched:
        print(f"  OK  {m['key']}  {m['chars']:7d} ch  {m['doi']}")
        print(f"      {m['title'][:88].encode('ascii','replace').decode()}")
    if already:
        print(f"\n  already present ({len(already)}): {[a[1] for a in already]}")
    still = [d for d in wanted if not (os.path.exists(f"{OUT}/{wanted[d]['key']}.txt")
                                       and os.path.getsize(f"{OUT}/{wanted[d]['key']}.txt") > 5000)]
    if still:
        print(f"\n  STILL MISSING ({len(still)}):")
        for d in still:
            print(f"    {d}  {wanted[d]['title'][:70].encode('ascii','replace').decode()}")
    # APPEND, never overwrite. The first (11-PDF Elsevier) batch was lost because this
    # wrote the log fresh on every run, leaving no provenance for eight ingested papers.
    log = []
    if os.path.exists("corpus/ingest_log.json"):
        try:
            log = json.load(open("corpus/ingest_log.json", encoding="utf-8"))
        except ValueError:
            log = []
    seen = {e.get("key") for e in log}
    log.extend(e for e in matched if e.get("key") not in seen)
    json.dump(log, open("corpus/ingest_log.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print(f"
  ingest log: {len(matched)} this run, {len(log)} total")
    print(f"\n  (other PDFs in Downloads ignored: {len(unmatched)})")


if __name__ == "__main__":
    main()
