"""Harvest the FLAME citation graph from Semantic Scholar + OpenAlex.

Writes corpus/flame_citers.json  (union of S2 and OpenAlex citing works)
"""
import json, os, sys, time, urllib.request, urllib.error

UA = 'flame-audit/1.0 (mailto:your-email@example.org)'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get(url, tries=6, sleep=2.0):
    last = None
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(r, timeout=90) as f:
                return json.load(f)
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(sleep * (i + 1) * 2)
                continue
            raise
        except Exception as e:
            last = e
            time.sleep(sleep * (i + 1))
    raise last


def s2_citations(pid):
    out = []
    off = 0
    fields = 'title,year,publicationDate,venue,externalIds,abstract,citationCount,authors,openAccessPdf,publicationTypes'
    while True:
        u = f'https://api.semanticscholar.org/graph/v1/paper/{pid}/citations?fields={fields}&limit=100&offset={off}'
        d = get(u)
        data = d.get('data', [])
        out.extend([x['citingPaper'] for x in data if x.get('citingPaper')])
        if not d.get('next'):
            break
        off = d['next']
        time.sleep(1.5)
    return out


def oa_citations(oaid):
    out = []
    cursor = '*'
    while True:
        u = ('https://api.openalex.org/works?filter=cites:' + oaid +
             '&per-page=200&cursor=' + cursor + '&mailto=your-email@example.org')
        d = get(u)
        out.extend(d['results'])
        cursor = d['meta'].get('next_cursor')
        if not cursor or not d['results']:
            break
        time.sleep(1.0)
    return out


def inv2abs(inv):
    if not inv:
        return None
    m = {}
    for w, ps in inv.items():
        for p in ps:
            m[p] = w
    return ' '.join(m[k] for k in sorted(m))


if __name__ == '__main__':
    FLAME_S2 = '76a116d0463614ec57f5bc1d39ab797d3ac0da18'
    recs = {}

    print('S2 citations...', flush=True)
    for c in s2_citations(FLAME_S2):
        ex = c.get('externalIds') or {}
        doi = (ex.get('DOI') or '').lower() or None
        key = doi or ('s2:' + c['paperId'])
        recs[key] = {
            'key': key, 'doi': doi, 'title': c.get('title'),
            'year': c.get('year'), 'date': c.get('publicationDate'),
            'venue': c.get('venue'), 'cites': c.get('citationCount'),
            'authors': [a.get('name') for a in (c.get('authors') or [])],
            'abstract': c.get('abstract'),
            'arxiv': ex.get('ArXiv'), 'pmid': ex.get('PubMed'),
            'oa_pdf': (c.get('openAccessPdf') or {}).get('url'),
            'src': ['s2'], 'types': c.get('publicationTypes'),
        }
    print('  s2:', len(recs), flush=True)

    # OpenAlex: FLAME has duplicate records (journal + preprint). Collect citers of each.
    oaids = []
    try:
        d = get('https://api.openalex.org/works?filter=title.search:%22pile%20burn%20detection%22&per-page=25&mailto=your-email@example.org')
        for w in d['results']:
            oaids.append((w['id'].rsplit('/', 1)[-1], w.get('doi'), w['cited_by_count'], w['display_name']))
    except Exception as e:
        print('  oa search failed', e)
    print('  OA candidate records:', oaids, flush=True)

    for oid, doi, cbc, name in oaids:
        if cbc < 3:
            continue
        print('OA citations of', oid, cbc, flush=True)
        try:
            ws = oa_citations(oid)
        except Exception as e:
            print('  fail', e); continue
        for w in ws:
            wdoi = (w.get('doi') or '').replace('https://doi.org/', '').lower() or None
            key = wdoi or ('oa:' + w['id'].rsplit('/', 1)[-1])
            if key in recs:
                recs[key]['src'].append('openalex')
                recs[key].setdefault('oa_id', w['id'])
                if not recs[key].get('date'):
                    recs[key]['date'] = w.get('publication_date')
                if not recs[key].get('abstract'):
                    recs[key]['abstract'] = inv2abs(w.get('abstract_inverted_index'))
                if not recs[key].get('oa_pdf'):
                    recs[key]['oa_pdf'] = (w.get('best_oa_location') or {}).get('pdf_url')
                recs[key]['venue'] = recs[key].get('venue') or ((w.get('primary_location') or {}).get('source') or {}).get('display_name')
                continue
            recs[key] = {
                'key': key, 'doi': wdoi, 'title': w.get('display_name'),
                'year': w.get('publication_year'), 'date': w.get('publication_date'),
                'venue': ((w.get('primary_location') or {}).get('source') or {}).get('display_name'),
                'cites': w.get('cited_by_count'),
                'authors': [a['author']['display_name'] for a in (w.get('authorships') or [])],
                'abstract': inv2abs(w.get('abstract_inverted_index')),
                'oa_pdf': (w.get('best_oa_location') or {}).get('pdf_url'),
                'oa_id': w['id'], 'src': ['openalex'],
                'types': [w.get('type')],
            }

    out = os.path.join(ROOT, 'corpus', 'flame_citers.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(list(recs.values()), f, ensure_ascii=False, indent=1)
    print('TOTAL', len(recs), '->', out)
