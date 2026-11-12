"""Scan FLAME-citing full texts for protocol signatures.

Emits corpus/flame_scan.json with, per paper:
  flame_mentions, official markers, resplit markers, unusual image counts,
  candidate split sentences, candidate accuracy sentences near 'FLAME'.
No classification is decided here - this is evidence extraction for manual coding.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FT = os.path.join(ROOT, 'corpus', 'flame_ft')

OFFICIAL_COUNTS = ['8617', '8,617', '39375', '39,375', '31501', '25018', '14357', '5137', '3480']
RESPLIT_COUNTS = ['1452', '1,452', '5615', '5,615', '35600', '35,600', '47992', '47,992',
                  '14400', '14,400', '2003', '1176', '1204', '1306']

SPLIT_PAT = re.compile(
    r'(?i)[^.\n]{0,300}?\b('
    r'split\s+into|randomly\s+(?:split|divided|selected|partition)|shuffl\w*|'
    r'train(?:ing)?[/\-: ]+(?:and\s+)?(?:test|validation)\s+(?:set|ratio|split)|'
    r'divided\s+into\s+\d+%|'
    r'\d{2}\s?%\s?(?:for\s)?train\w*|'
    r'\d{2}\s?:\s?\d{2}\s+ratio|'
    r'80/20|70/30|90/10|80/10/10|85/10/5|70/20/10|75/25|60/20/20|'
    r'k-?fold|cross[- ]validation|'
    r'merged\s+the\s+train|combined\s+the\s+train'
    r')[^.\n]{0,300}\.', re.I)

FLAME_ACC = re.compile(r'(?i)[^.\n]{0,250}\bFLAME\b[^.\n]{0,250}\.')
ACC_PAT = re.compile(r'(?i)[^.\n]{0,200}\b(accuracy|acc\.)\b[^.\n]{0,120}?(\d{2}(?:\.\d{1,2})?)\s?%[^.\n]{0,80}\.')

CAMERA_PAT = re.compile(r'(?i)(zenmuse|matrice\s*200|phantom\s*3|phantom drone|no overlap exists|camera[- ]disjoint)')


def sents(txt, pat, limit=14):
    out = []
    for m in pat.finditer(txt):
        s = re.sub(r'\s+', ' ', m.group(0)).strip()
        if s not in out:
            out.append(s)
        if len(out) >= limit:
            break
    return out


def main():
    recs = json.load(open(os.path.join(ROOT, 'corpus', 'flame_citers.json'), encoding='utf-8'))
    out = []
    for r in recs:
        p = os.path.join(FT, (r.get('ftkey') or '') + '.txt')
        if not r.get('ftkey') or not os.path.exists(p):
            continue
        t = open(p, encoding='utf-8', errors='ignore').read()
        tn = re.sub(r'\s+', ' ', t)
        nflame = len(re.findall(r'(?i)\bFLAME\b', tn))
        if nflame == 0:
            continue
        off = [c for c in OFFICIAL_COUNTS if c in tn]
        res = [c for c in RESPLIT_COUNTS if c in tn]
        rec = {
            'doi': r.get('doi'), 'title': r.get('title'), 'year': r.get('year'),
            'date': r.get('date'), 'venue': r.get('venue'), 'cites': r.get('cites'),
            'authors': (r.get('authors') or [])[:4], 'ftkey': r['ftkey'],
            'ft_route': r.get('ft'), 'chars': len(t),
            'n_flame': nflame,
            'official_counts': off, 'resplit_counts': res,
            'camera_markers': sorted(set(m.group(0).lower() for m in CAMERA_PAT.finditer(tn))),
            'split_sentences': sents(tn, SPLIT_PAT),
            'flame_sentences': sents(tn, FLAME_ACC, 10),
            'accuracy_sentences': sents(tn, ACC_PAT, 10),
            'has_shamsoshoara_ref': bool(re.search(r'(?i)shamsoshoara', tn)),
        }
        out.append(rec)
    out.sort(key=lambda x: (-x['n_flame']))
    json.dump(out, open(os.path.join(ROOT, 'corpus', 'flame_scan.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('full texts scanned with FLAME mention:', len(out))
    print('with official counts:', sum(1 for x in out if x['official_counts']))
    print('with resplit counts:', sum(1 for x in out if x['resplit_counts']))
    print('citing Shamsoshoara by name:', sum(1 for x in out if x['has_shamsoshoara_ref']))


if __name__ == '__main__':
    main()
