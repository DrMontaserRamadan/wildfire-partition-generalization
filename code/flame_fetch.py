"""Fetch full text for FLAME citing works. Stores corpus/flame_ft/<key>.txt"""
import json, os, re, sys, time, hashlib, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FT = os.path.join(ROOT, 'corpus', 'flame_ft')
os.makedirs(FT, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9"}


def get(u, t=60):
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
            open(os.path.join(FT, key + '.txt'), 'w', encoding='utf-8').write(txt)
            return kind + '|pdf'
        return None
    txt = h2t(data)
    if len(txt) > 6000 and re.search(r"(?i)\b(dataset|training set|experiment|methodolog|we (train|evaluat|test))", txt):
        open(os.path.join(FT, key + '.txt'), 'w', encoding='utf-8').write(txt)
        return kind + '|html'
    return None


def cands(r):
    doi = r.get('doi')
    if r.get('oa_pdf'):
        yield ('s2pdf', r['oa_pdf'])
    if r.get('arxiv'):
        yield ('arxiv', 'https://arxiv.org/pdf/%s' % r['arxiv'])
    if doi:
        j = get('https://api.unpaywall.org/v2/%s?email=your-email@example.org' % doi, 40)
        if j:
            try:
                locs = (json.loads(j).get('oa_locations') or [])
                locs.sort(key=lambda l: 0 if l.get('host_type') == 'repository' else 1)
                for l in locs:
                    if l.get('url_for_pdf'):
                        yield ('unpaywall', l['url_for_pdf'])
                for l in locs:
                    if l.get('url'):
                        yield ('unpaywall_html', l['url'])
            except Exception:
                pass
        j = get('https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%%22%s%%22&format=json&resultType=core'
                % urllib.parse.quote(doi), 40)
        if j:
            try:
                res = json.loads(j).get('resultList', {}).get('result', [])
                if res and res[0].get('pmcid'):
                    yield ('epmc', 'https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML' % res[0]['pmcid'])
            except Exception:
                pass
        if doi.startswith('10.3390/'):
            slug = doi.split('/', 1)[1]
            # MDPI canonical pdf route
            yield ('mdpi', 'https://www.mdpi.com/2072-4292/1/1/1/pdf')  # placeholder replaced below
    return


def mdpi_urls(doi):
    # resolve via doi.org to get the article path, then append /pdf
    try:
        req = urllib.request.Request('https://doi.org/' + doi, headers=UA)
        with urllib.request.urlopen(req, timeout=45) as f:
            final = f.geturl()
        if 'mdpi.com' in final:
            return [final.rstrip('/') + '/pdf?version=1', final.rstrip('/') + '/htm', final]
    except Exception:
        pass
    return []


def main(infile, only_keys=None):
    recs = json.load(open(infile, encoding='utf-8'))
    log = []
    for i, r in enumerate(recs):
        key = hashlib.md5((r.get('key') or r.get('doi') or r.get('title') or str(i)).encode('utf-8')).hexdigest()[:12]
        r['ftkey'] = key
        path = os.path.join(FT, key + '.txt')
        if os.path.exists(path):
            r['ft'] = 'cached'
            continue
        if only_keys and r.get('key') not in only_keys:
            continue
        got = None
        urls = list(cands(r))
        doi = r.get('doi') or ''
        if doi.startswith('10.3390/'):
            urls = [('mdpi', u) for u in mdpi_urls(doi)] + urls
        for kind, u in urls:
            if 'placeholder' in u or u.endswith('/2072-4292/1/1/1/pdf'):
                continue
            data = get(u)
            got = store(data, key, kind)
            if got:
                break
            time.sleep(0.4)
        r['ft'] = got
        log.append((r.get('doi'), got, (r.get('title') or '')[:60]))
        print(i, got, (r.get('title') or '')[:70], flush=True)
        time.sleep(0.3)
    json.dump(recs, open(infile, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = sum(1 for r in recs if r.get('ft'))
    print('DONE. with fulltext:', ok, '/', len(recs))


if __name__ == '__main__':
    main(os.path.join(ROOT, 'corpus', 'flame_citers.json'))
