"""Build the blind abstract-screen packet.

Emits corpus/scope_screen_packet.json: every eligible paper that has NEVER had a full-text
scope check, i.e. all 159 minus the 24 survivors of the author-supplied 34-paper batch.
Full text is deliberately NOT included. Order is deterministic-shuffled so that publisher and
retrieval status do not cue the coder.
"""
import json, io, os, csv, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def L(p):
    return json.load(io.open(os.path.join(ROOT, p), encoding='utf-8'))

universe = L('corpus/UNIVERSE_FROZEN.json')
prim = {p['id']: p for p in L('corpus/primary_clean.json')}

# the 24 survivors of the full-text-checked batch
rows = list(csv.DictReader(io.open(os.path.join(ROOT, 'corpus/retrieval_table.csv'), encoding='utf-8')))
checked = {r['paper_id'] for r in rows if 'author-supplied' in r['retrieval_route']}

packet = []
for p in universe['papers']:
    if p['paper_id'] in checked:
        continue
    src = prim.get(p['paper_id'], {})
    packet.append({
        'paper_id': p['paper_id'],
        'title': p['title'],
        'year': p['year'],
        'venue': p['venue'],
        'abstract': src.get('abstract', ''),
        'retrieved': bool(p['fulltext_obtained']),
    })

# deterministic shuffle keyed on the paper id, so publisher/retrieval order carries no signal
packet.sort(key=lambda r: hashlib.sha256(r['paper_id'].encode()).hexdigest())

out = os.path.join(ROOT, 'corpus/scope_screen_packet.json')
with io.open(out, 'w', encoding='utf-8') as f:
    json.dump(packet, f, ensure_ascii=False, indent=1)

n_ret = sum(1 for r in packet if r['retrieved'])
print(f'packet: {len(packet)} papers never full-text scope-checked')
print(f'  retrieved (full text on disk, used later for calibration): {n_ret}')
print(f'  not retrieved (abstract is all we will ever have):        {len(packet)-n_ret}')
print(f'  already full-text checked, held out of this packet:       {len(checked)}')
