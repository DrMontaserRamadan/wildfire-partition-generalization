"""Build the full-text scope-evidence packet for the 80 calibration papers.

Deliberately withholds title, venue and abstract: the same person coded those from the
abstract packet, and showing them again would anchor the full-text decision onto the
frozen abstract decision and inflate the measured agreement. The packet carries only
evidence lifted from the body text, in an order shuffled independently of the abstract packet.
"""
import json, io, os, re, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

DOMAIN = {
    'wildland': ['wildfire', 'wild fire', 'forest fire', 'wildland', 'bushfire', 'grassland',
                 'woodland', 'vegetation fire', 'peat'],
    'built': ['indoor', 'residential', 'household', 'domestic', 'apartment', 'building fire',
              'warehouse', 'office', 'campus', 'urban fire', 'street'],
    'industrial': ['industrial', 'factory', 'furnace', 'reactor', 'coal mine', 'tunnel',
                   'engine room', 'ship fire', 'vehicle fire', 'chimney', 'flare'],
}
TASK = ['we propose', 'we present', 'this paper proposes', 'in this paper', 'our contribution',
        'the main contribution', 'this study proposes', 'we develop', 'this work presents']
EVAL = ['dataset', 'we train', 'training set', 'test set', 'mAP', 'accuracy of',
        'experiments were conducted', 'evaluated on', 'benchmark']


def sentences(text):
    text = re.sub(r'\s+', ' ', text)
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if 25 < len(s) < 400]


def pick(sents, cues, n, used):
    out = []
    for s in sents:
        low = s.lower()
        if any(c.lower() in low for c in cues) and s not in used:
            out.append(s)
            used.add(s)
            if len(out) >= n:
                break
    return out


universe = {p['paper_id']: p for p in
            json.load(io.open('corpus/UNIVERSE_FROZEN.json', encoding='utf-8'))['papers']}
frozen = json.load(io.open('corpus/scope_abstract_decisions.json', encoding='utf-8'))

cal = [d for d in frozen['decisions'] if d['retrieved']]

packet = []
for d in cal:
    p = universe[d['paper_id']]
    raw = io.open(f"corpus/ft/{p['ftkey']}.txt", encoding='utf-8', errors='replace').read()
    sents = sentences(raw)
    low = raw.lower()
    counts = {k: sum(low.count(t) for t in v) for k, v in DOMAIN.items()}
    used = set()
    packet.append({
        'paper_id': d['paper_id'],
        'chars': len(raw),
        'term_counts': counts,
        'task': pick(sents, TASK, 3, used),
        'domain_wildland': pick(sents, DOMAIN['wildland'], 3, used),
        'domain_built': pick(sents, DOMAIN['built'] + DOMAIN['industrial'], 3, used),
        'eval': pick(sents, EVAL, 3, used),
    })

# shuffle on a different salt than the abstract packet so position carries no memory
packet.sort(key=lambda r: hashlib.sha256(('ft:' + r['paper_id']).encode()).hexdigest())
for i, r in enumerate(packet):
    r['probe_index'] = i

json.dump(packet, io.open('corpus/scope_fulltext_packet.json', 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print(f'full-text probe packet: {len(packet)} papers')
print('median chars:', sorted(r['chars'] for r in packet)[len(packet)//2])
thin = [r for r in packet if not (r['task'] or r['domain_wildland'] or r['domain_built'])]
print('papers with no extracted evidence at all:', len(thin))
