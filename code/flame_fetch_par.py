"""Parallel full-text fetch for FLAME citing works -> corpus/flame_ft/<ftkey>.txt"""
import json, os, re, sys, time, hashlib, threading
import urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FT = os.path.join(ROOT, 'corpus', 'flame_ft')
os.makedirs(FT, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9"}
LOCK = threading.Lock()


def get(u, t=45):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()
    except Exception:
        return None


def h2t(b):
    s = b.decode('utf-8', 'ignore')
    s = re.sub(r"(?is)<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</h\d>|</li>|</tr>", "\n", s)
    s = re.sub(r"(?is)</t[dh]>", " | ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    for a, b2 in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                  ("&quot;", '"'), ("&#x2014;", "-"), ("&#8217;", "'"), ("&ndash;", "-")]:
        s = s.replace(a, b2)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]{2,}", " ", s))


def pdf2txt(data):
    try:
        import fitz
        doc = fitz.open(stream=data, filetype='pdf')
        return "\n".join(p.get_text() for p in doc)
    except Exception:
        return ''


def store(data, key, kind):
    if not data or len(data) < 3000:
        return None
    if data[:4] == b'%PDF':
        txt = pdf2txt(data)
        if len(txt) > 5000:
            with open(os.path.join(FT, key + '.txt'), 'w', encoding='utf-8') as f:
                f.write(txt)
            return kind + '|pdf'
        return None
    txt = h2t(data)
    if len(txt) > 6000 and re.search(r"(?i)\b(dataset|training set|experiment|methodolog|we (train|evaluat|test))", txt):
        with open(os.path.join(FT, key + '.txt'), 'w', encoding='utf-8') as f:
            f.write(txt)
        return kind + '|html'
    return None


def resolve(doi):
    try:
        req = urllib.request.Request('https://doi.org/' + doi, headers=UA)
        with urllib.request.urlopen(req, timeout=40) as f:
            return f.geturl()
    except Exception:
        return None


def urls_for(r):
    out = []
    doi = (r.get('doi') or '')
    if doi.startswith('10.3390/'):
        fin = resolve(doi)
        if fin and 'mdpi.com' in fin:
            out += [('mdpi', fin.rstrip('/') + '/pdf?version=1'), ('mdpi', fin.rstrip('/'))]
    if r.get('oa_pdf'):
        out.append(('s2pdf', r['oa_pdf']))
    if r.get('arxiv'):
        out.append(('arxiv', 'https://arxiv.org/pdf/%s' % r['arxiv']))
    if doi:
        j = get('https://api.unpaywall.org/v2/%s?email=your-email@example.org' % urllib.parse.quote(doi), 35)
        if j:
            try:
                locs = (json.loads(j).get('oa_locations') or [])
                locs.sort(key=lambda l: 0 if l.get('host_type') == 'repository' else 1)
                out += [('unpaywall', l['url_for_pdf']) for l in locs if l.get('url_for_pdf')]
                out += [('unpaywall_html', l['url']) for l in locs if l.get('url')]
            except Exception:
                pass
        j = get('https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%%22%s%%22&format=json&resultType=core'
                % urllib.parse.quote(doi), 35)
        if j:
            try:
                res = json.loads(j).get('resultList', {}).get('result', [])
                if res and res[0].get('pmcid'):
                    out.append(('epmc', 'https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML' % res[0]['pmcid']))
            except Exception:
                pass
        if doi.startswith('10.1155/') or doi.startswith('10.1038/') or doi.startswith('10.1007/'):
            fin = resolve(doi)
            if fin:
                out.append(('pub', fin))
    seen = set(); ded = []
    for k, u in out:
        if u in seen:
            continue
        seen.add(u); ded.append((k, u))
    return ded[:10]


def work(r):
    key = r['ftkey']
    path = os.path.join(FT, key + '.txt')
    if os.path.exists(path) and os.path.getsize(path) > 5000:
        return key, 'cached'
    for kind, u in urls_for(r):
        got = store(get(u), key, kind)
        if got:
            return key, got
    return key, None


def main():
    inf = os.path.join(ROOT, 'corpus', 'flame_citers.json')
    recs = json.load(open(inf, encoding='utf-8'))
    for i, r in enumerate(recs):
        r['ftkey'] = hashlib.md5((r.get('key') or r.get('doi') or r.get('title') or str(i)).encode('utf-8')).hexdigest()[:12]
    todo = [r for r in recs if not (os.path.exists(os.path.join(FT, r['ftkey'] + '.txt'))
                                    and os.path.getsize(os.path.join(FT, r['ftkey'] + '.txt')) > 5000)]
    print('todo', len(todo), 'of', len(recs), flush=True)
    res = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(work, r): r for r in todo}
        for n, f in enumerate(as_completed(futs)):
            r = futs[f]
            try:
                k, got = f.result()
            except Exception as e:
                k, got = r['ftkey'], 'ERR:%s' % e
            res[k] = got
            if n % 20 == 0:
                print(n, got, (r.get('title') or '')[:60], flush=True)
    for r in recs:
        p = os.path.join(FT, r['ftkey'] + '.txt')
        r['ft'] = res.get(r['ftkey']) if r['ftkey'] in res else ('cached' if os.path.exists(p) else None)
    json.dump(recs, open(inf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('DONE. with fulltext:', sum(1 for r in recs if r.get('ft')), '/', len(recs))


if __name__ == '__main__':
    main()
