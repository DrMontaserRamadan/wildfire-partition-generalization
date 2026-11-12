"""Print targeted protocol evidence for one or more FLAME-citing papers."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scan = json.load(open(os.path.join(ROOT, 'corpus', 'flame_scan.json'), encoding='utf-8'))
IDX = {}
for x in scan:
    IDX[(x['doi'] or '').lower()] = x
    IDX[x['ftkey']] = x

PATS = [
    r'8,?617', r'39,?375', r'25,?018', r'14,?357', r'5,?137', r'3,?480',
    r'(?i)train\w{0,4}\s*(?:set|data|dataset)?\s*(?:was|were|is|are)?\s*(?:randomly\s+)?(?:split|divided|partition)',
    r'(?i)\b(?:80|70|75|85|90|60)\s?[%:/]\s?(?:\d{1,2}\s?[%:/]\s?)?\d{1,2}\s?%?',
    r'(?i)shuffl',
    r'(?i)k-?fold|cross[- ]validation',
    r'(?i)test (?:set|dataset|images|data)[^.]{0,120}',
    r'(?i)phantom|matrice|zenmuse',
]


def dump(key, win=280, maxper=3):
    x = IDX.get(key.lower())
    if not x:
        print('!! not found', key); return
    p = os.path.join(ROOT, 'corpus', 'flame_ft', x['ftkey'] + '.txt')
    t = re.sub(r'\s+', ' ', open(p, encoding='utf-8', errors='ignore').read())
    print('=' * 110)
    print(key, '|', x.get('date'), '|', x.get('venue'), '| cites', x.get('cites'), '| route', x.get('ft_route'))
    print('TITLE:', x.get('title'))
    print('AUTH:', '; '.join(x.get('authors') or []))
    seen = set()
    for pat in PATS:
        n = 0
        for m in re.finditer(pat, t):
            frag = t[max(0, m.start() - win):m.end() + win]
            kk = frag[:60]
            if kk in seen:
                continue
            seen.add(kk)
            print('  <%s> ...%s...' % (pat[:22], frag))
            n += 1
            if n >= maxper:
                break
    print()


if __name__ == '__main__':
    for k in sys.argv[1:]:
        dump(k)
