"""Construct and document the partition-granularity ladder for Pyro-SDIS.

Every rung is built from metadata the dataset ships as typed columns (partner, camera, date).
Nothing is inferred from image content, which is the condition the whole experiment rests on: a
grouping invented from appearance would commit the error the manuscript documents.

The ladder is nested by construction, coarsening at each step:

    image  <  event  <  camera  <  partner

An event is a run of images from ONE camera with no gap longer than EVENT_GAP_MIN. Pyro-SDIS is a
wildfire-watch network, so a detection produces a burst of frames from a single camera over a short
window; that burst is the natural unit between the frame and the camera. Because events are defined
within a camera, and no camera appears under more than one partner, the nesting is exact rather
than approximate, and it is verified below rather than assumed.

Temporal is reported alongside but is NOT a rung: it cuts across the hierarchy instead of
coarsening it, and Pyro-SDIS spans only eight months of one year, so it tests short-horizon drift
within a single fire season and must be described as that.

The images are pooled once and re-partitioned under each protocol at identical proportions.
Comparing a 70/10/20 protocol against the shipped 88/12 split would confound the allocation rule
with the training-set size. For the same reason every run subsamples its training set to a common
N, reported at the end.

A single grouped split is one draw from a lottery: which cameras happen to land in test moves the
score. Each protocol is therefore replicated across independent assignments, and the spread across
replicates of the RANDOM protocol is the split-noise floor against which any rank movement at a
coarser rung has to be judged.

This script trains nothing. It documents the design, and it decides nothing the frozen protocol
does not already state.
"""
import io
import json
import os
import random
import sys
from collections import defaultdict
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TARGET = (0.70, 0.10, 0.20)
EVENT_GAP_MIN = 30
N_REPLICATES = 5
SEEDS = [20260911 + i for i in range(N_REPLICATES)]
CACHE = "corpus/pyrosdis_rows.json"


def load_rows():
    rows = json.load(io.open(CACHE, encoding="utf-8"))
    for r in rows:
        r["t"] = datetime.strptime(r["date"], "%Y-%m-%dT%H-%M-%S")
    return rows


def assign_events(rows):
    """Label each image with its event id: a within-camera burst with no gap > EVENT_GAP_MIN."""
    by = defaultdict(list)
    for r in rows:
        by[r["camera"]].append(r)
    n = 0
    for cam, rs in by.items():
        rs.sort(key=lambda x: x["t"])
        rs[0]["event"] = f"{cam}#0"
        k = 0
        for a, b in zip(rs, rs[1:]):
            if (b["t"] - a["t"]).total_seconds() / 60 > EVENT_GAP_MIN:
                k += 1
            b["event"] = f"{cam}#{k}"
        n += k + 1
    return n


def verify_nesting(rows):
    """The ladder is only a ladder if each level refines the one above it."""
    ok = True
    for fine, coarse in (("event", "camera"), ("camera", "partner")):
        bad = [g for g, vals in
               ((g, {r[coarse] for r in rs}) for g, rs in group_by(rows, fine).items())
               if len(vals) > 1]
        print(f"  every {fine:7s} sits inside exactly one {coarse:8s}: "
              f"{'YES' if not bad else f'NO ({len(bad)} violations)'}")
        ok &= not bad
    return ok


def group_by(rows, key):
    g = defaultdict(list)
    for r in rows:
        g[r[key]].append(r)
    return g


def describe(rows, idx, label):
    total = sum(len(idx[a]) for a in ("train", "val", "test"))
    out = {"label": label}
    for arm in ("train", "val", "test"):
        sub = [rows[i] for i in idx[arm]]
        out[arm] = {
            "n": len(sub), "pct": round(100 * len(sub) / total, 2),
            "pos_rate": round(100 * sum(1 for r in sub if r["pos"]) / len(sub), 2),
            "boxes": sum(r["nbox"] for r in sub),
            "events": len({r["event"] for r in sub}),
            "cameras": len({r["camera"] for r in sub}),
            "partners": len({r["partner"] for r in sub}),
            "date_min": min(r["date"] for r in sub)[:10],
            "date_max": max(r["date"] for r in sub)[:10],
        }
    for axis in ("event", "camera", "partner"):
        tr = {rows[i][axis] for i in idx["train"]}
        te = {rows[i][axis] for i in idx["test"]}
        out[f"{axis}_leak"] = len(tr & te)
    out["prevalence_spread_pp"] = round(
        max(out[a]["pos_rate"] for a in ("train", "val", "test"))
        - min(out[a]["pos_rate"] for a in ("train", "val", "test")), 2)
    return out


def split_random(rows, _axis, seed):
    rng = random.Random(seed)
    order = list(range(len(rows)))
    rng.shuffle(order)
    a = int(TARGET[0] * len(order))
    b = a + int(TARGET[1] * len(order))
    return {"train": order[:a], "val": order[a:b], "test": order[b:]}


def split_grouped(rows, axis, seed):
    """Whole groups to whichever arm is furthest below quota; groups shuffled first.

    Largest-first packing would balance the arms better but make the assignment near-deterministic,
    which would destroy the replicate variance we specifically want to measure.
    """
    rng = random.Random(seed)
    groups = group_by(list(range(len(rows))), None) if False else defaultdict(list)
    for i, r in enumerate(rows):
        groups[r[axis]].append(i)
    keys = sorted(groups)
    rng.shuffle(keys)
    n = len(rows)
    quota = {"train": TARGET[0] * n, "val": TARGET[1] * n, "test": TARGET[2] * n}
    idx = {"train": [], "val": [], "test": []}
    for k in keys:
        arm = max(quota, key=lambda a: quota[a] - len(idx[a]))
        idx[arm].extend(groups[k])
    return idx


def split_partner_lopo(rows, _axis, seed):
    """Leave-one-partner-out. Three partners cannot make a 70/10/20 split.

    Attempting one empties an arm outright, which is the honest signal that this rung does not
    support the same design as the others. Each fold therefore holds out one whole partner as test
    and splits the remaining two into train/val at the EVENT level, so the training pool is still
    free of within-event leakage. The fold index is carried in the seed: seeds map to partners in
    sorted order, and a seed beyond the third returns None so the caller can skip it.
    """
    partners = sorted({r["partner"] for r in rows})
    fold = (seed - SEEDS[0]) % len(partners)
    if seed - SEEDS[0] >= len(partners):
        return None
    held = partners[fold]
    test = [i for i, r in enumerate(rows) if r["partner"] == held]
    rest = [i for i, r in enumerate(rows) if r["partner"] != held]
    ev = defaultdict(list)
    for i in rest:
        ev[rows[i]["event"]].append(i)
    keys = sorted(ev)
    random.Random(seed).shuffle(keys)
    want_val = 0.125 * len(rest)
    val, train = [], []
    for k in keys:
        (val if len(val) < want_val else train).extend(ev[k])
    return {"train": train, "val": val, "test": test}


def split_temporal(rows, _axis, _seed):
    order = sorted(range(len(rows)), key=lambda i: rows[i]["date"])
    a = int(TARGET[0] * len(order))
    b = a + int(TARGET[1] * len(order))
    return {"train": order[:a], "val": order[a:b], "test": order[b:]}


def main():
    rows = load_rows()
    n_ev = assign_events(rows)
    print(f"pooled {len(rows)} images | {n_ev} events (gap > {EVENT_GAP_MIN} min) | "
          f"{len({r['camera'] for r in rows})} cameras | {len({r['partner'] for r in rows})} partners")
    print(f"dates {min(r['date'] for r in rows)[:10]} .. {max(r['date'] for r in rows)[:10]}")
    print(f"positives {sum(1 for r in rows if r['pos'])}  boxes {sum(r['nbox'] for r in rows)}")

    print("\nNESTING CHECK (the ladder must actually refine)")
    nested = verify_nesting(rows)
    if not nested:
        print("  ABORT: the hierarchy is not nested; the ladder framing would be false.")
        return 1

    sizes = {k: len(group_by(rows, k)) for k in ("event", "camera", "partner")}
    print(f"\nRUNGS: image {len(rows)} > event {sizes['event']} > camera {sizes['camera']} "
          f"> partner {sizes['partner']}")

    report = {"n_pooled": len(rows), "target": TARGET, "seeds": SEEDS,
              "event_gap_min": EVENT_GAP_MIN, "rung_sizes": sizes,
              "nesting_verified": nested, "protocols": {}}

    specs = [
        ("P1_random_image", split_random, None, SEEDS),
        ("P2_event_disjoint", split_grouped, "event", SEEDS),
        ("P3_camera_disjoint", split_grouped, "camera", SEEDS),
        ("P4_partner_lopo", split_partner_lopo, "partner", SEEDS[:3]),
        ("P5_temporal", split_temporal, None, SEEDS[:1]),
    ]

    for name, fn, axis, seeds in specs:
        print(f"\n{'='*100}\n{name}\n{'='*100}")
        reps = []
        for s in seeds:
            idx = fn(rows, axis, s)
            if idx is None:
                continue
            d = describe(rows, idx, name)
            reps.append(d)
            tr, va, te = d["train"], d["val"], d["test"]
            print(f"  seed {s} | train {tr['n']:6d} ({tr['pct']:5.1f}%) pos {tr['pos_rate']:5.1f}% "
                  f"{tr['cameras']:2d}cam | val {va['n']:5d} ({va['pct']:4.1f}%) "
                  f"| test {te['n']:6d} ({te['pct']:5.1f}%) pos {te['pos_rate']:5.1f}% "
                  f"{te['cameras']:2d}cam | leak ev={d['event_leak']:4d} "
                  f"cam={d['camera_leak']:2d} par={d['partner_leak']} "
                  f"| prev-spread {d['prevalence_spread_pp']:5.2f}pp")
        sz = [r["train"]["n"] for r in reps]
        sp = [r["prevalence_spread_pp"] for r in reps]
        print(f"  replicates: train size {min(sz)}-{max(sz)}, prevalence spread {min(sp):.2f}-{max(sp):.2f} pp")
        report["protocols"][name] = {"replicates": reps, "train_size_range": [min(sz), max(sz)],
                                     "prevalence_spread_range": [min(sp), max(sp)]}

    floor = min(r["train"]["n"] for p in report["protocols"].values() for r in p["replicates"])
    print(f"\n{'='*100}\nMATCHED-SIZE CONTROL\n{'='*100}")
    print(f"  smallest training arm anywhere: {floor}")
    print(f"  every run subsamples its training set to N = {floor}, using the replicate's own seed,")
    print("  so training-set size cannot explain a difference between protocols.")
    report["matched_train_n"] = floor

    json.dump(report, io.open("corpus/pyrosdis_partitions.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nwrote corpus/pyrosdis_partitions.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
