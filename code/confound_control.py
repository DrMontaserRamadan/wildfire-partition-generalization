"""
CONFOUND CONTROL for the decontamination experiment.

THE THREAT. In the main experiment a model trained on DeepQuestAI recalls ~0.99 of the
contaminated 43% of FireNET and ~0.65 of the clean 57%. The obvious alternative explanation
is that the clean subset is simply HARDER — different scenes, resolutions, or fire sizes —
and that contamination explains nothing.

THE TEST. Retrain on DeepQuestAI with the contaminating images REMOVED, and evaluate on the
SAME two FireNET subsets.

  If the gap COLLAPSES  -> the gap was caused by having seen those images. Contamination is
                           the explanation. The main result stands.
  If the gap PERSISTS   -> the clean subset is intrinsically harder. Contamination is not the
                           explanation and the main claim must be withdrawn or heavily
                           qualified.

This is a falsification test for our own headline finding, and it is run before publication
rather than after a reviewer asks for it.

Design notes:
  - The removed set is the 234 DeepQuestAI images identified as twins in overlap_pairs.json.
    They are removed from the TRAINING pool only. The FireNET test set is untouched, so the
    two arms are evaluated on exactly the same images.
  - To keep training-set SIZE from being a confound, a matched arm is also run in which an
    equal number of RANDOM non-twin images is removed instead. Three arms:
        FULL     : train on everything (reproduces the main experiment)
        NO_TWINS : remove the 234 twins
        RANDOM   : remove 234 random non-twin images (size-matched placebo)
    If NO_TWINS collapses the gap and RANDOM does not, the effect is specific to the twins.
"""
import os, json, random, sys
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import transforms
import torchvision.models as tvm
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decontamination_experiment import (ListDS, TF_TRAIN, TF_EVAL, DQ, FN, DEV,
                                        build_test, make_model, contaminated_firenet)

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPOCHS = 12
BS = 32
SEEDS = list(range(10))   # 10 seeds/arm: the 3-seed pilot showed the
                          # gap ranges 0.18-0.37 within one arm, so 3 cannot
                          # separate the arms. Underpowered designs are how
                          # this literature got into trouble in the first place.
ARCH = "resnet18"


def dq_twins():
    """DeepQuestAI relative paths that are twins of a FireNET image."""
    P = json.load(open(os.path.join(ROOT, "corpus/overlap_pairs.json"), encoding="utf-8"))
    key = [k for k in P["cross"] if "FireNET" in k and "DeepQuestAI_FireSmoke" in k][0]
    return {p["a"] for p in P["cross"][key]}   # 'a' side is DeepQuestAI


def build_train(seed, mode, twins):
    rng = random.Random(seed)
    items = []
    for cls, y in (("Fire", 1), ("Neutral", 0), ("Smoke", 0)):
        d = os.path.join(DQ, "Train", cls)
        for f in sorted(os.listdir(d)):
            rel = f"Train/{cls}/{f}"
            items.append((os.path.join(d, f), y, rel))
    fire = [x for x in items if x[1] == 1]
    neg = [x for x in items if x[1] == 0]
    rng.shuffle(neg)
    neg = neg[:len(fire)]
    pool = fire + neg

    if mode == "no_twins":
        pool = [x for x in pool if x[2] not in twins]
        removed = None
    elif mode == "random":
        n_rm = sum(1 for x in pool if x[2] in twins)
        cand = [i for i, x in enumerate(pool) if x[2] not in twins and x[1] == 1]
        rng.shuffle(cand)
        drop = set(cand[:n_rm])
        pool = [x for i, x in enumerate(pool) if i not in drop]
        removed = n_rm
    else:
        removed = 0
    rng.shuffle(pool)
    return [(p, y) for p, y, _ in pool], removed


def run(mode, seed, twins, test_items, flags):
    torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
    tr, removed = build_train(seed, mode, twins)
    m = make_model(ARCH)
    dl = DataLoader(ListDS(tr, TF_TRAIN), batch_size=BS, shuffle=True, drop_last=True)
    opt = torch.optim.AdamW(m.parameters(), lr=3e-4, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    lf = nn.CrossEntropyLoss()
    m.train()
    for ep in range(EPOCHS):
        for x, y in dl:
            x, y = x.to(DEV), y.to(DEV)
            opt.zero_grad(); lf(m(x), y).backward(); opt.step()
        sched.step()
    m.eval()
    preds = []
    with torch.no_grad():
        for x, _ in DataLoader(ListDS(test_items, TF_EVAL), batch_size=64):
            preds.append(m(x.to(DEV)).argmax(1).cpu().numpy())
    p = np.concatenate(preds)
    r = {"mode": mode, "seed": seed, "n_train": len(tr),
         "recall_all": float((p == 1).mean()),
         "recall_contaminated": float((p[flags] == 1).mean()),
         "recall_clean": float((p[~flags] == 1).mean())}
    r["gap"] = r["recall_contaminated"] - r["recall_clean"]
    return r


if __name__ == "__main__":
    twins = dq_twins()
    test_items, flags = build_test()
    print(f"DeepQuestAI images that are FireNET twins: {len(twins)}")
    print(f"FireNET test: n={len(test_items)} contaminated={flags.sum()} clean={(~flags).sum()}\n",
          flush=True)
    out = []
    for mode in ("full", "no_twins", "random"):
        for seed in SEEDS:
            r = run(mode, seed, twins, test_items, flags)
            print(f"  {mode:9s} s{seed} n_train={r['n_train']:5d} | all {r['recall_all']:.4f} "
                  f"| contam {r['recall_contaminated']:.4f} | clean {r['recall_clean']:.4f} "
                  f"| GAP {r['gap']:+.4f}", flush=True)
            out.append(r)
            json.dump(out, open(os.path.join(ROOT, "corpus/confound_control_results.json"),
                                "w"), indent=1)
    print("\n=== CONFOUND CONTROL SUMMARY ===")
    for mode in ("full", "no_twins", "random"):
        rs = [r for r in out if r["mode"] == mode]
        g = np.mean([r["gap"] for r in rs]); sg = np.std([r["gap"] for r in rs])
        c = np.mean([r["recall_contaminated"] for r in rs])
        q = np.mean([r["recall_clean"] for r in rs])
        print(f"  {mode:9s} contam {c:.4f}  clean {q:.4f}  GAP {g:+.4f} +- {sg:.4f}")
    gf = np.mean([r["gap"] for r in out if r["mode"] == "full"])
    gn = np.mean([r["gap"] for r in out if r["mode"] == "no_twins"])
    gr = np.mean([r["gap"] for r in out if r["mode"] == "random"])
    print(f"\n  gap reduction from removing TWINS   : {gf-gn:+.4f} "
          f"({100*(gf-gn)/gf:.1f}% of the original gap)")
    print(f"  gap reduction from removing RANDOM  : {gf-gr:+.4f} "
          f"({100*(gf-gr)/gf:.1f}% of the original gap)")
    # Welch t-tests on the gap between arms. Unequal variance is assumed because the pilot
    # showed the arms need not have comparable spread.
    try:
        from scipy import stats
        gf_v = [r["gap"] for r in out if r["mode"] == "full"]
        gn_v = [r["gap"] for r in out if r["mode"] == "no_twins"]
        gr_v = [r["gap"] for r in out if r["mode"] == "random"]
        t1, p1 = stats.ttest_ind(gf_v, gn_v, equal_var=False)
        t2, p2 = stats.ttest_ind(gf_v, gr_v, equal_var=False)
        t3, p3 = stats.ttest_ind(gn_v, gr_v, equal_var=False)
        print(f"\n  n per arm = {len(gf_v)}")
        print(f"  Welch  full     vs no_twins : t={t1:+.3f}  p={p1:.4g}")
        print(f"  Welch  full     vs random   : t={t2:+.3f}  p={p2:.4g}")
        print(f"  Welch  no_twins vs random   : t={t3:+.3f}  p={p3:.4g}   <- the decisive one")
    except Exception as e:
        print("  (significance test unavailable:", e, ")")

    print("\n  INTERPRETATION:")
    print("   twins-removal collapses the gap and random-removal does not -> contamination is")
    print("   the explanation. Both collapse equally -> training-set size is the explanation.")
    print("   Neither collapses -> the clean subset is intrinsically harder and the main")
    print("   claim must be withdrawn or heavily qualified.")
