"""Rebuild corpus/ingest_log.json from disk evidence.

The original script wrote the log fresh on each run, so the first (Elsevier) batch was
overwritten by the second (IEEE) batch and eight ingested papers had no provenance record.
Intake PDFs are named by ftkey = md5(paper_id)[:12], so the mapping is recoverable from disk
rather than from memory. Entries reconstructed this way are flagged.
"""
import json, io, os, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def L(p):
    return json.load(io.open(p, encoding='utf-8'))


universe = L('corpus/UNIVERSE_FROZEN.json')
excluded = L('corpus/excluded_reviews_records.json')

by_key = {}
for p in universe['papers']:
    by_key[p['ftkey']] = {'id': p['paper_id'], 'doi': p['doi'], 'title': p['title'],
                          'status': 'retained'}
for x in excluded:
    k = hashlib.md5(x['id'].encode()).hexdigest()[:12]
    by_key[k] = {'id': x['id'], 'doi': x.get('doi', ''), 'title': x['title'],
                 'status': 'excluded on full-text scope' if x.get('_exclusion_reason')
                           else 'excluded as review/survey'}

existing = {e.get('key'): e for e in L('corpus/ingest_log.json')}

log, recovered, orphan = [], 0, []
for fn in sorted(os.listdir('intake')):
    if not fn.lower().endswith('.pdf'):
        continue
    key = fn[:-4]
    rec = by_key.get(key)
    if rec is None:
        orphan.append(fn)
        continue
    txt = f'corpus/ft/{key}.txt'
    if key in existing:
        e = dict(existing[key])
        e.setdefault('status', rec['status'])
        e['provenance'] = 'logged at ingest time'
    else:
        e = {'file': fn, 'doi': rec['doi'], 'key': key,
             'chars': os.path.getsize(txt) if os.path.exists(txt) else 0,
             'title': rec['title'], 'status': rec['status'],
             'provenance': 'RECONSTRUCTED from intake/<ftkey>.pdf; original log entry was '
                           'overwritten by a later batch'}
        recovered += 1
    log.append(e)

json.dump(log, io.open('corpus/ingest_log.json', 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)

print(f'intake PDFs      : {len(log) + len(orphan)}')
print(f'log entries      : {len(log)}  ({recovered} reconstructed, {len(log)-recovered} original)')
print(f'orphan PDFs      : {len(orphan)} {orphan}')
from collections import Counter
for k, v in Counter(e['status'] for e in log).most_common():
    print(f'  {v:3d}  {k}')
