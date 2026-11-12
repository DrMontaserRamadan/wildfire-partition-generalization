"""Regenerate the section 1.1 timeline table in notes/FLAME_GENEALOGY.md from the JSON."""
import json, os, io, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = json.load(open(os.path.join(ROOT, 'corpus', 'flame_timeline.json'), encoding='utf-8'))
rows.sort(key=lambda r: (r['pub_date'] or 'zzz'))

BOLD = {'RANDOM_RESPLIT', 'SUBSET_OF_UNCLEAR_PROVENANCE', 'K_FOLD_POOLED', 'INTERNALLY_INCONSISTENT'}

out = ['| # | First author | Date | Venue | DOI | Protocol | Images used | Headline | Kind |',
       '|---|---|---|---|---|---|---|---|---|']
for i, r in enumerate(rows, 1):
    p = r['protocol']
    ptxt = '**%s**' % p if p in BOLD else p
    if r['id'] == 'yan2022uda':
        ptxt = 'OFFICIAL (UDA)'
    acc = r.get('headline_accuracy')
    acctxt = '**%.2f**' % acc if acc is not None else '*(no headline)*'
    if r['id'] == 'dutta2021':
        acctxt += ' ‡'
    kind = (r.get('accuracy_kind') or '—')
    kind = kind.split(';')[0].split('(')[0].split(',')[0].strip()[:38] or '—'
    counts = (r.get('image_counts') or '—')
    counts = counts.split('||')[0].strip()
    if len(counts) > 62:
        counts = counts[:59].rstrip() + '…'
    doi = r.get('doi') or '*(no DOI)*'
    out.append('| %d | %s | %s | %s | %s | %s | %s | %s | %s |' % (
        i, r['first_author'], r['pub_date'], r['venue'], doi, ptxt, counts, acctxt, kind))

table = '\n'.join(out)

p = os.path.join(ROOT, 'notes', 'FLAME_GENEALOGY.md')
s = io.open(p, encoding='utf-8').read()
start = s.index('### 1.1 The table')
end = s.index('### 1.2 ')
head = '### 1.1 The table\n\n'
tail = """

‡ Dutta & Ghosh 2021 is the one entry whose full text was NOT read on this machine. Its 92.00%
is the highest official-protocol figure in the corpus and the only value that inverts the rank
ordering in §1.2. Treat it as provisional until resolved (§7.1).

Joshi et al. 2024 appears once, as its OFFICIAL RGB arm. Its thermal arms, which split a single
video clip into 1,204/218 and 1,306/214 and score 99.08% and 99.87%, are recorded inside that
row's `other_reported` field in the JSON and are discussed in §6.

Zhao et al. 2024 (IROS) and Bai et al. 2025 (JSTARS) report the **same experiment** — the
journal paper extends the conference paper. Treat them as one independent data point.

"""
s = s[:start] + head + table + tail + s[end:]
io.open(p, 'w', encoding='utf-8').write(s)
print('rendered %d rows' % len(rows))
