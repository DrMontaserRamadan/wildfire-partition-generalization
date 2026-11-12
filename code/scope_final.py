"""Emit the per-paper scope record as a LAYER over the frozen universe.

UNIVERSE_FROZEN.json is the eligible sampling FRAME and is not re-frozen here: eligibility is
what the pre-registered filter admitted, and scope is a coded finding about those papers.
Keeping them separate is what lets retrieval rates stay honest while prevalence claims move
onto the verified subset.
"""
import json, io, os, csv
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

universe = json.load(io.open('corpus/UNIVERSE_FROZEN.json', encoding='utf-8'))
frozen = json.load(io.open('corpus/scope_abstract_decisions.json', encoding='utf-8'))
packet = json.load(io.open('corpus/scope_fulltext_packet.json', encoding='utf-8'))
rows = list(csv.DictReader(io.open('corpus/retrieval_table.csv', encoding='utf-8')))

idx2pid = {r['probe_index']: r['paper_id'] for r in packet}
ft = {}
for line in io.open('corpus/scope_ft/ALL.tsv', encoding='utf-8'):
    line = line.rstrip('\n')
    if line:
        i, code, reason = line.split('\t', 2)
        ft[idx2pid[int(i)]] = (code, reason)

abst = {d['paper_id']: d for d in frozen['decisions']}
author_supplied = {r['paper_id'] for r in rows if 'author-supplied' in r['retrieval_route']}

# Tier A was scope-checked in the earlier batch against a criterion that was never written
# down, and it shows: five of its 25 papers fail the written rubric, all of them either
# burned-area mapping or network-optimisation studies wearing a wildfire application label.
# Re-coding tier A against the same rubric is what keeps the denominator on one standard.
tierA_packet = json.load(io.open('corpus/scope_tierA_packet.json', encoding='utf-8'))
tierA = {}
for line in io.open('corpus/scope_ft/tierA.tsv', encoding='utf-8'):
    line = line.rstrip('\n')
    if line:
        i, code, reason = line.split('\t', 2)
        tierA[tierA_packet[int(i)]['paper_id']] = (code, reason)

out = []
for p in universe['papers']:
    pid = p['paper_id']
    if pid in ft and ft[pid][0] != 'INSUFFICIENT':
        code, reason, tier, ev = ft[pid][0], ft[pid][1], 'B', 'full text'
    elif pid in author_supplied:
        code, reason = tierA[pid]
        tier, ev = 'A', 'full text, re-coded against the written rubric'
    else:
        a = abst[pid]
        code, reason, tier = a['abstract_code'], a['abstract_reason'], 'C'
        ev = 'abstract only (full text never obtained)' if not p['fulltext_obtained'] \
             else 'abstract only (stored text is a landing page, not the article)'
    out.append({
        'paper_id': pid, 'title': p['title'], 'publisher': p['publisher'], 'year': p['year'],
        'modality': p['modality'], 'fulltext_obtained': p['fulltext_obtained'],
        'scope_tier': tier, 'scope_evidence': ev, 'scope_code': code,
        'in_scope': not code.startswith('OUT') and code != 'UNCLEAR',
        'contested': 'BORDERLINE' in code,
        'scope_reason': reason,
    })

json.dump(out, io.open('corpus/scope_final.json', 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
with io.open('corpus/scope_table.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)

print(f'eligible frame        : {len(out)}')
print('\ntier   n   in-scope   evidence')
for t in 'ABC':
    g = [r for r in out if r['scope_tier'] == t]
    print(f'  {t}  {len(g):4d} {sum(1 for r in g if r["in_scope"]):9d}   '
          f'{Counter(r["scope_evidence"] for r in g).most_common(1)[0][0]}')
print(f'\nfull-text-verified in scope (A+B): '
      f'{sum(1 for r in out if r["scope_tier"] in "AB" and r["in_scope"])}')
print(f'out of scope, full-text verified : '
      f'{sum(1 for r in out if r["scope_tier"] in "AB" and not r["in_scope"])}')
print('\nreason for exclusion, all tiers:')
for k, v in Counter(r['scope_code'] for r in out if not r['in_scope']).most_common():
    print(f'  {k:9s} {v}')
# --- per-publisher in-scope rate, over the PRE-EXCLUSION frame ---
# The ten papers dropped on scope in the author-supplied batch were removed from
# UNIVERSE_FROZEN entirely. Scoring tier A against the surviving frame puts Elsevier and IEEE
# at 100% by construction, because only their survivors are left in it. The ten are added back
# here as out-of-scope so each publisher is scored against what it actually contributed.
excluded = json.load(io.open('corpus/excluded_reviews_records.json', encoding='utf-8'))
scope_excl = [x for x in excluded if x.get('_exclusion_reason')]

PREFIX = [("10.3390", "MDPI"), ("10.1109", "IEEE"), ("10.1016", "Elsevier"),
          ("10.1007", "Springer"), ("10.1080", "Taylor & Francis"), ("10.1002", "Wiley"),
          ("10.1038", "Nature Portfolio"), ("10.1371", "PLOS"), ("10.3389", "Frontiers")]


def pub_of(doi):
    for pre, name in PREFIX:
        if (doi or '').startswith(pre):
            return name
    return 'other/small publisher' if doi else 'no DOI'


verified = [{'publisher': r['publisher'], 'in_scope': r['in_scope']}
            for r in out if r['scope_tier'] in 'AB']
verified += [{'publisher': pub_of(x.get('doi', '')), 'in_scope': False} for x in scope_excl]

print('\nin-scope rate by publisher, full-text-verified, ten batch exclusions restored:')
for pub in sorted({r['publisher'] for r in verified}):
    g = [r for r in verified if r['publisher'] == pub]
    k = sum(1 for r in g if r['in_scope'])
    print(f'  {pub:26s} {k:3d}/{len(g):<3d} = {100*k/len(g):5.1f}%')
kk, tot = sum(1 for r in verified if r['in_scope']), len(verified)
print(f'  {"ALL":26s} {kk:3d}/{tot:<3d} = {100*kk/tot:5.1f}%')
