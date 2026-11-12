"""
PROVENANCE CONTROL — the decisive test for the reframed contamination claim.

BACKGROUND. A DeepQuestAI-trained model recalls ~1.00 of the 43% of FireNET that shares
provenance with its training data and ~0.65 of the remainder. The confound control showed this
is NOT memorisation: removing the 234 duplicated images from training left the gap unchanged
(p = 0.989 against a size-matched placebo).

TWO EXPLANATIONS REMAIN.
  (H1) SHARED PROVENANCE. The contaminated subset is easy because it is distributionally
       identical to the training corpus - same scraped commons, same style - not because
       specific files were seen.
  (H2) INTRINSIC DIFFICULTY. The clean subset is simply harder, and provenance is irrelevant.

THE TEST. Train on D-Fire, which we measured to have ZERO confirmed overlap with FireNET
(26 candidate pairs, all rejected at the NCC >= 0.95 gate), and evaluate on the SAME two
FireNET subsets.

  Gap VANISHES or shrinks sharply -> H1. The subsets differ by provenance relative to the
                                     training corpus, not by intrinsic difficulty. The
                                     reframed claim stands.
  Gap PERSISTS at similar size    -> H2. The clean subset is intrinsically harder. The
                                     contamination contribution reduces to a measurement with
                                     no demonstrated consequence, and we must say so.

This is a second falsification test of our own finding, run before publication.

D-Fire labelling: the parquet carries a `label` column. D-Fire annotates fire and smoke; we
map to binary fire-vs-not using the label field, and report the resulting class balance so the
training conditions are comparable to the DeepQuestAI arm.
"""
import os, io, json, random, sys
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import transforms
from PIL import Image
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decontamination_experiment import ListDS, TF_TRAIN, TF_EVAL, DEV, build_test, make_model

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
EPOCHS = 12
BS = 32
SEEDS = list(range(10))
ARCH = "resnet18"
CACHE = "datasets/dfire_labelled"


def materialise_dfire():
    """Extract D-Fire images into class folders once, using the parquet label column."""
    if os.path.isdir(CACHE) and sum(len(f) for _, _, f in os.walk(CACHE)) > 1000:
        return
    os.makedirs(f"{CACHE}/fire", exist_ok=True)
    os.makedirs(f"{CACHE}/nofire", exist_ok=True)
    n = 0
    for fn in sorted(os.listdir("datasets/dfire_pq")):
        if not fn.endswith(".parquet"):
            continue
        p = os.path.join("datasets/dfire_pq", fn)
        if os.path.getsize(p) < 1000:
            continue
        pf = pq.ParquetFile(p)
        for batch in pf.iter_batches(batch_size=64):
            d = batch.to_pydict()
            for rec, lab in zip(d["image"], d.get("label", [None] * len(d["image"]))):
                b = rec.get("bytes") if isinstance(rec, dict) else rec
                if not b:
                    continue
                try:
                    im = Image.open(io.BytesIO(b)); im.load()
                except Exception:
                    continue
                # D-Fire ships YOLO annotation text in `label`: "<class> cx cy w h" per line,
                # class 0 = smoke, class 1 = fire, empty string = no object.
                # Binary mapping: fire = any class-1 box; nofire = no boxes at all.
                # Smoke-only images are DISCARDED rather than labelled nofire, because a
                # smoke image is not a negative for a fire detector and calling it one would
                # be the same category error this paper audits.
                s = (lab or "").strip()
                if not s:
                    cls = "nofire"
                else:
                    classes = {ln.split()[0] for ln in s.splitlines() if ln.split()}
                    if "1" in classes:
                        cls = "fire"
                    else:
                        continue          # smoke-only: skip
                im.convert("RGB").save(f"{CACHE}/{cls}/d{n:06d}.jpg", quality=92)
                n += 1
    print(f"materialised {n} D-Fire images", flush=True)


def build_dfire_train(seed):
    rng = random.Random(seed)
    fire = [(os.path.join(CACHE, "fire", f), 1) for f in sorted(os.listdir(f"{CACHE}/fire"))]
    nof = [(os.path.join(CACHE, "nofire", f), 0) for f in sorted(os.listdir(f"{CACHE}/nofire"))]
    rng.shuffle(fire); rng.shuffle(nof)
    n = min(len(fire), len(nof), 900)      # match the DeepQuestAI arm's 900/900
    items = fire[:n] + nof[:n]
    rng.shuffle(items)
    return items


def run(seed, test_items, flags):
    torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
    tr = build_dfire_train(seed)
    m = make_model(ARCH)
    dl = DataLoader(ListDS(tr, TF_TRAIN), batch_size=BS, shuffle=True, drop_last=True)
    opt = torch.optim.AdamW(m.parameters(), lr=3e-4, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    lf = nn.CrossEntropyLoss()
    m.train()
    for _ in range(EPOCHS):
        for x, y in dl:
            x, y = x.to(DEV), y.to(DEV)
            opt.zero_grad(); lf(m(x), y).backward(); opt.step()
        sch.step()
    m.eval()
    pr = []
    with torch.no_grad():
        for x, _ in DataLoader(ListDS(test_items, TF_EVAL), batch_size=64):
            pr.append(m(x.to(DEV)).argmax(1).cpu().numpy())
    p = np.concatenate(pr)
    r = {"seed": seed, "n_train": len(tr),
         "recall_all": float((p == 1).mean()),
         "recall_contaminated": float((p[flags] == 1).mean()),
         "recall_clean": float((p[~flags] == 1).mean())}
    r["gap"] = r["recall_contaminated"] - r["recall_clean"]
    return r


if __name__ == "__main__":
    materialise_dfire()
    nf = len(os.listdir(f"{CACHE}/fire")); nn_ = len(os.listdir(f"{CACHE}/nofire"))
    print(f"D-Fire pool: fire={nf} nofire={nn_}", flush=True)
    if min(nf, nn_) < 100:
        sys.exit("insufficient class balance in D-Fire pool - inspect the label mapping")
    test_items, flags = build_test()
    print(f"FireNET test: n={len(test_items)} contaminated={flags.sum()} clean={(~flags).sum()}\n",
          flush=True)
    out = []
    for s in SEEDS:
        r = run(s, test_items, flags)
        print(f"  dfire-trained s{s} n={r['n_train']:4d} | all {r['recall_all']:.4f} "
              f"| contam {r['recall_contaminated']:.4f} | clean {r['recall_clean']:.4f} "
              f"| GAP {r['gap']:+.4f}", flush=True)
        out.append(r)
        json.dump(out, open("corpus/provenance_control_results.json", "w"), indent=1)

    g = [r["gap"] for r in out]
    print(f"\n=== PROVENANCE CONTROL (D-Fire trained, zero overlap with FireNET) ===")
    print(f"  contam {np.mean([r['recall_contaminated'] for r in out]):.4f}  "
          f"clean {np.mean([r['recall_clean'] for r in out]):.4f}  "
          f"GAP {np.mean(g):+.4f} +- {np.std(g):.4f}   n={len(g)}")
    try:
        from scipy import stats
        dq = [r["gap"] for r in json.load(open("corpus/confound_control_results.json"))
              if r["mode"] == "full"]
        t, p = stats.ttest_ind(dq, g, equal_var=False)
        print(f"  DeepQuestAI-trained gap {np.mean(dq):+.4f} vs D-Fire-trained gap "
              f"{np.mean(g):+.4f}")
        print(f"  Welch t={t:+.3f}  p={p:.4g}")
        print("\n  INTERPRETATION:")
        print("   D-Fire gap near zero and significantly smaller -> SHARED PROVENANCE (H1).")
        print("   D-Fire gap similar to DeepQuestAI -> INTRINSIC DIFFICULTY (H2); the")
        print("   contamination contribution has no demonstrated consequence and we say so.")
    except Exception as e:
        print("  (comparison unavailable:", e, ")")
