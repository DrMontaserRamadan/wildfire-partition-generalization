"""Full-text scope-evidence packet for the hand-retrieved papers.

Same construction as scripts/scope_fulltext_probe.py, on the same cue lists, so the full-text
scope decision for these papers is made on the same evidence shape as the 80 already screened.
Title, venue and abstract are withheld for the same reason: these papers were coded IN from
their abstracts, and showing the abstract again anchors the full-text decision onto it.

The shuffle uses a third salt, so packet position carries no memory of either earlier packet.
"""
import hashlib
import io
import json
import os
import re

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
# the three criteria the rubric turns on, kept verbatim from the registered rubric
REVIEW = ['this review', 'this survey', 'we review', 'literature review', 'systematic review',
          'bibliometric', 'taxonomy of', 'we surveyed']


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


man = json.load(io.open('corpus/ft_incoming_manifest.json', encoding='utf-8'))
# only papers not already screened at full text on this pass
done = {d['paper_id'] for d in
        json.load(io.open('corpus/scope_incoming_decisions.json', encoding='utf-8'))['decisions']}
packet = []
for r in man['records']:
    if r['paper_id'] in done:
        continue
    pid = r['paper_id']
    raw = io.open(f'corpus/ft_incoming/txt/{pid}.txt', encoding='utf-8', errors='replace').read()
    sents = sentences(raw)
    low = raw.lower()
    counts = {k: sum(low.count(t) for t in v) for k, v in DOMAIN.items()}
    used = set()
    packet.append({
        'paper_id': pid,
        'chars': len(raw),
        'term_counts': counts,
        'task': pick(sents, TASK, 3, used),
        'domain_wildland': pick(sents, DOMAIN['wildland'], 3, used),
        'domain_built': pick(sents, DOMAIN['built'] + DOMAIN['industrial'], 3, used),
        'eval': pick(sents, EVAL, 3, used),
        'review_cues': pick(sents, REVIEW, 2, used),
    })

packet.sort(key=lambda r: hashlib.sha256(('ftin:' + r['paper_id']).encode()).hexdigest())
for i, r in enumerate(packet):
    r['probe_index'] = i

json.dump(packet, io.open('corpus/scope_fulltext_packet_exclcheck.json', 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print(f'full-text probe packet: {len(packet)} papers')
print('median chars:', sorted(r['chars'] for r in packet)[len(packet) // 2])
thin = [r for r in packet if not (r['task'] or r['domain_wildland'] or r['domain_built'])]
print('papers with no extracted evidence at all:', len(thin), [r['paper_id'] for r in thin])
