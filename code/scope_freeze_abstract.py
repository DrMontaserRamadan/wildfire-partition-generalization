"""Freeze the blind abstract-screen decisions.

Run BEFORE any full text is opened. The output carries a SHA-256 so that the calibration in
scope_calibrate.py cannot be accused of having been fitted after the fact.
"""
import json, io, os, csv, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

packet = json.load(io.open('corpus/scope_screen_packet.json', encoding='utf-8'))

rows = {}
with io.open('corpus/scope/ALL.tsv', encoding='utf-8') as f:
    for line in f:
        line = line.rstrip('\n')
        if not line:
            continue
        idx, code, reason = line.split('\t', 2)
        rows[int(idx)] = (code, reason)

assert len(rows) == len(packet), f'{len(rows)} decisions for {len(packet)} papers'

VALID = {'IN', 'IN_BORDERLINE', 'OUT_S1', 'OUT_S2', 'OUT_S3', 'UNCLEAR'}
out = []
for i, p in enumerate(packet):
    code, reason = rows[i]
    assert code in VALID, f'bad code {code} at {i}'
    out.append({
        'paper_id': p['paper_id'],
        'title': p['title'],
        'retrieved': p['retrieved'],
        'abstract_code': code,
        'abstract_verdict': 'OUT' if code.startswith('OUT') else ('UNCLEAR' if code == 'UNCLEAR' else 'IN'),
        'abstract_reason': reason,
    })

payload = {
    'frozen_at': '2026-09-11',
    'rubric': 'notes/SCOPE_SCREEN_RUBRIC.md',
    'coder': 'single coder, blind to full text at the time of coding',
    'n': len(out),
    'decisions': out,
}
payload['sha256'] = hashlib.sha256(
    json.dumps(out, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()

json.dump(payload, io.open('corpus/scope_abstract_decisions.json', 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)

from collections import Counter
print(f"FROZEN  n={len(out)}  sha256={payload['sha256'][:16]}...")
print('\ncode                 all   retrieved(cal)   unretrieved')
for k, v in Counter(r['abstract_code'] for r in out).most_common():
    a = sum(1 for r in out if r['abstract_code'] == k and r['retrieved'])
    b = v - a
    print(f'  {k:16s} {v:5d} {a:12d} {b:13d}')
print('\nverdict              all   retrieved(cal)   unretrieved')
for k, v in Counter(r['abstract_verdict'] for r in out).most_common():
    a = sum(1 for r in out if r['abstract_verdict'] == k and r['retrieved'])
    b = v - a
    print(f'  {k:16s} {v:5d} {a:12d} {b:13d}')
