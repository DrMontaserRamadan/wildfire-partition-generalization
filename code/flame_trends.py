"""Compute apparent vs protocol-normalised best-accuracy trends from the FLAME timeline."""
import json, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fit(xs, ys):
    """OLS slope/intercept + R^2 without numpy."""
    n = len(xs)
    if n < 2:
        return None, None, None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return None, None, None
    b = sxy / sxx
    a = my - b * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot if ss_tot else None
    return b, a, r2


def series(rows, predicate, label):
    byyear = collections.defaultdict(list)
    for r in rows:
        if not predicate(r):
            continue
        acc = r.get('headline_accuracy')
        if acc is None:
            continue
        byyear[r['year']].append((acc, r['first_author']))
    print('\n== %s ==' % label)
    xs, ys = [], []
    for y in sorted(byyear):
        vals = byyear[y]
        best = max(vals)
        print('  %d  best=%6.2f  n=%d  (best: %s)' % (y, best[0], len(vals), best[1]))
        xs.append(y); ys.append(best[0])
    b, a, r2 = fit(xs, ys)
    if b is not None:
        print('  trend: %+.2f pts/year  (intercept %.1f, R2=%.3f, %d year-points, %d papers)'
              % (b, a, r2, len(xs), sum(len(v) for v in byyear.values())))
    return byyear, (b, a, r2)


if __name__ == '__main__':
    rows = json.load(open(os.path.join(ROOT, 'corpus', 'flame_timeline.json'), encoding='utf-8'))
    rows = [r for r in rows if r.get('headline_accuracy') is not None]
    series(rows, lambda r: True, '(a) APPARENT: all published FLAME numbers, protocol ignored')
    series(rows, lambda r: r['protocol'] == 'OFFICIAL',
           '(b) NORMALISED: verified official 8,617-frame test set only')
    series(rows, lambda r: r['protocol'] in ('RANDOM_RESPLIT', 'SUBSET_OF_UNCLEAR_PROVENANCE',
                                             'K_FOLD_POOLED', 'INTERNALLY_INCONSISTENT'),
           '(c) NON-OFFICIAL protocols only')
    print('\ncounts by protocol:', collections.Counter(r['protocol'] for r in rows))
