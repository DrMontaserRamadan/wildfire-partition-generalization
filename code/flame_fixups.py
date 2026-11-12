"""Final consistency fixups for notes/FLAME_GENEALOGY.md."""
import io, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, 'notes', 'FLAME_GENEALOGY.md')
rows = json.load(open(os.path.join(ROOT, 'corpus', 'flame_timeline.json'), encoding='utf-8'))
n = len(rows)
nacc = sum(1 for r in rows if r.get('headline_accuracy') is not None)

s = io.open(p, encoding='utf-8').read()

subs = [
    ('Of the 353 works citing FLAME, full text was retrieved for 92 (26.1%). The timeline holds 24\npapers.',
     'Of the 353 works citing FLAME, full text was retrieved for 94 (26.6%). The timeline holds '
     + str(n) + '\npapers, of which ' + str(nacc) + ' report a headline FLAME accuracy.'),
    ('reinvented at least ten times.', 'reinvented at least a dozen times.'),
    ('Nine MDPI PDFs were pulled that way, and every agent-supplied quote from them was',
     'Eleven MDPI PDFs were pulled that way, and every agent-supplied quote from them was'),
]
for a, b in subs:
    if a in s:
        s = s.replace(a, b)
    else:
        print('NOT FOUND:', a[:60])

io.open(p, 'w', encoding='utf-8').write(s)
print('fixups applied;', n, 'rows,', nacc, 'with accuracy')
