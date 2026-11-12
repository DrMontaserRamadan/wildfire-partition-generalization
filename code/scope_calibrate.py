"""Calibrate the abstract scope screen against the full-text decision.

The abstract codes were frozen (corpus/scope_abstract_decisions.json) before any full text was
read, and the full-text pass was run on evidence packets stripped of title and abstract. This
script measures how well the abstract screen predicts the full-text verdict on the 80-paper
calibration set, then applies the result to the 54 papers whose full text we will never have.
"""
import json, io, os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

frozen = json.load(io.open('corpus/scope_abstract_decisions.json', encoding='utf-8'))
packet = json.load(io.open('corpus/scope_fulltext_packet.json', encoding='utf-8'))
idx2pid = {r['probe_index']: r['paper_id'] for r in packet}

ft = {}
for line in io.open('corpus/scope_ft/ALL.tsv', encoding='utf-8'):
    line = line.rstrip('\n')
    if not line:
        continue
    i, code, reason = line.split('\t', 2)
    ft[idx2pid[int(i)]] = (code, reason)

abst = {d['paper_id']: d for d in frozen['decisions']}


def verdict(code):
    return 'OUT' if code.startswith('OUT') else ('UNCLEAR' if code == 'UNCLEAR' else 'IN')


cal = [(pid, abst[pid]['abstract_verdict'], verdict(c))
       for pid, (c, _) in ft.items() if c != 'INSUFFICIENT']
insufficient = [pid for pid, (c, _) in ft.items() if c == 'INSUFFICIENT']

print(f'calibration set : {len(cal)} papers')
print(f'unusable        : {len(insufficient)} "retrieved" papers whose stored text is only a landing page')

# --- confusion, treating UNCLEAR as its own row (it is never silently folded into IN) ---
cm = Counter((a, f) for _, a, f in cal)
rows = ['IN', 'UNCLEAR']
print('\nconfusion (abstract screen vs full-text truth)')
print(f"{'abstract':>10} | {'FT=IN':>6} {'FT=OUT':>7} | total")
for a in rows + ['OUT']:
    i, o = cm[(a, 'IN')], cm[(a, 'OUT')]
    print(f'{a:>10} | {i:6d} {o:7d} | {i+o:5d}')

# --- primary analysis: the screen's decision rule is IN vs not-IN, UNCLEAR resolved BOTH ways ---
def stats(unclear_as):
    tp = fp = fn = tn = 0
    for _, a, f in cal:
        pred = a if a != 'UNCLEAR' else unclear_as
        if pred == 'IN' and f == 'IN':
            tp += 1
        elif pred == 'IN' and f == 'OUT':
            fp += 1
        elif pred == 'OUT' and f == 'IN':
            fn += 1
        else:
            tn += 1
    n = tp + fp + fn + tn
    acc = (tp + tn) / n
    po = acc
    pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float('nan')
    sens = tp / (tp + fn) if tp + fn else float('nan')
    spec = tn / (tn + fp) if tn + fp else float('nan')
    ppv = tp / (tp + fp) if tp + fp else float('nan')
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, acc=acc, kappa=kappa,
                sens=sens, spec=spec, ppv=ppv)


print('\n                      acc    kappa   sens   spec    PPV   (fp, fn)')
for lab, ua in [('UNCLEAR treated as IN ', 'IN'), ('UNCLEAR treated as OUT', 'OUT')]:
    s = stats(ua)
    print(f"{lab}  {s['acc']:.3f}  {s['kappa']:.3f}  {s['sens']:.3f}  {s['spec']:.3f}  "
          f"{s['ppv']:.3f}   ({s['fp']}, {s['fn']})")

THRESHOLD = 0.60
best = max(stats('IN')['kappa'], stats('OUT')['kappa'])
worst = min(stats('IN')['kappa'], stats('OUT')['kappa'])
print(f"\npre-registered threshold kappa >= {THRESHOLD}: "
      f"{'MET' if worst >= THRESHOLD else 'NOT MET'} under both UNCLEAR resolutions "
      f"(range {worst:.3f} to {best:.3f})")

# --- apply to the 54 ---
unret = [d for d in frozen['decisions'] if not d['retrieved']]
c = Counter(d['abstract_verdict'] for d in unret)
print(f"\n--- the {len(unret)} papers with no obtainable full text ---")
for k in ('IN', 'OUT', 'UNCLEAR'):
    print(f'  abstract screen says {k:8s}: {c[k]}')

s_in, s_out = stats('IN'), stats('OUT')
lo = c['IN'] * s_out['ppv']
hi = (c['IN'] + c['UNCLEAR']) * s_in['ppv']
print(f"\n  projected in-scope among the 54, using the calibrated PPV:")
print(f"    lower (UNCLEAR out, PPV {s_out['ppv']:.3f}): {lo:.1f}")
print(f"    upper (UNCLEAR in,  PPV {s_in['ppv']:.3f}): {hi:.1f}")

ft_in = sum(1 for _, (code, _) in ft.items() if code == 'IN')

# Tier A is NOT assumed to be all in scope. It was re-coded against the written rubric after
# the regression test surfaced a UAV-navigation paper sitting in it as a detection study;
# seven of its 25 fail. Hardcoding 24 here printed a superseded denominator (94-101) long
# after scope_final.py had moved to the correct one. Read the coded result instead.
try:
    _final = json.load(io.open('corpus/scope_final.json', encoding='utf-8'))
    tierA = sum(1 for r in _final if r['scope_tier'] == 'A' and r['in_scope'])
    tierA_n = sum(1 for r in _final if r['scope_tier'] == 'A')
    _src = 're-coded against the written rubric'
except (OSError, ValueError):
    tierA, tierA_n, _src = None, None, 'NOT AVAILABLE - run scope_final.py first'

print('\n=== DENOMINATORS ===')
print('  NOTE: the authoritative figures are produced by scope_final.py and')
print('        scope_sensitivity.py. This block is a cross-check, not the source.')
print(f'  eligible frame (post batch-exclusions)           : 159')
print(f'  initially eligible candidate corpus              : 169')
if tierA is None:
    print('  A  tier A                                        : ' + _src)
else:
    print(f'  A  full-text verified, earlier batch             : {tierA} of {tierA_n} ({_src})')
    print(f'  B  full-text verified here                       : {ft_in}   (of {len(cal)} checkable)')
    print(f'  -- full-text-verified IN-SCOPE  A + B            : {tierA + ft_in}')
    print(f'  -- full-text-verified DENOMINATOR (incl. the 10) : '
          f'{tierA_n + len(cal) + len(insufficient) + 10 - len(insufficient)}')
    print(f'  C1 retrieved but text unusable, abstract only    : {len(insufficient)}')
    print(f'  C2 never retrieved, abstract only                : {len(unret)}')
    print(f'  -- abstract-screened addition (PPV range)        : {lo:.0f} to {hi:.0f}')
    print('\n  The TOTAL in-scope estimate is deliberately NOT printed here. This block')
    print('  applies the PPV range to the primary coding only; scope_sensitivity.py also')
    print('  varies the nine contested and six UNCLEAR cases, and treats the four')
    print('  landing-page papers consistently. Two scripts printing two different totals')
    print('  is how a superseded number reaches a manuscript.')
    print('  AUTHORITATIVE TOTAL -> scope_sensitivity.py  (81 to 93 of 169)')

json.dump({'calibration_n': len(cal),
           'insufficient': insufficient,
           'unclear_as_IN': s_in, 'unclear_as_OUT': s_out,
           'threshold': THRESHOLD,
           'threshold_met': bool(worst >= THRESHOLD),
           'unretrieved_counts': dict(c),
           'projected_in_scope_low': lo, 'projected_in_scope_high': hi,
           'tierA': tierA, 'tierB_in': ft_in},
          io.open('corpus/scope_calibration.json', 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
