"""Apply the written rubric to tier A, the 25 author-supplied survivors.

Tier A was scope-checked in the earlier batch against a criterion that was never written down.
It was held out of the calibration set for blindness, which was right, but leaving it out of
the rubric pass entirely would build the denominator from two different standards. The
regression test on the coding excerpts surfaced the problem: a UAV swarm NAVIGATION and
formation-control paper is sitting in tier A as an in-scope detection study.
"""
import json, io, os, re, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

import scope_fulltext_probe as P  # reuse the same extraction, same cue sets

scope = json.load(io.open('corpus/scope_final.json', encoding='utf-8'))
tierA = [r for r in scope if r['scope_tier'] == 'A']

out = []
for r in tierA:
    key = hashlib.md5(r['paper_id'].encode()).hexdigest()[:12]
    raw = io.open(f'corpus/ft/{key}.txt', encoding='utf-8', errors='replace').read()
    sents = P.sentences(raw)
    low = raw.lower()
    used = set()
    out.append({
        'paper_id': r['paper_id'], 'title': r['title'], 'chars': len(raw),
        'term_counts': {k: sum(low.count(t) for t in v) for k, v in P.DOMAIN.items()},
        'task': P.pick(sents, P.TASK, 3, used),
        'domain_wildland': P.pick(sents, P.DOMAIN['wildland'], 2, used),
        'domain_built': P.pick(sents, P.DOMAIN['built'] + P.DOMAIN['industrial'], 2, used),
        'eval': P.pick(sents, P.EVAL, 3, used),
    })

out.sort(key=lambda r: hashlib.sha256(('A:' + r['paper_id']).encode()).hexdigest())
json.dump(out, io.open('corpus/scope_tierA_packet.json', 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print(f'tier A probe packet: {len(out)} papers')
