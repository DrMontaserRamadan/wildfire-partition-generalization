"""
CONSEQUENCE EXPERIMENT — does benchmark contamination change the conclusions?

Scenario under test (the one researchers actually run):
    A model is trained on DeepQuestAI Fire-Smoke and then evaluated on FireNET, and the
    result is reported as CROSS-DATASET generalisation to an independent benchmark.

We measured that 218 of FireNET's 502 images (43.4%) have a confirmed near-duplicate in
DeepQuestAI. So that "independent" test set is 43% training data.

DESIGN
  Train:  DeepQuestAI Fire-Smoke, Train/ split only.
          Binary task: Fire (900) vs NotFire (Neutral 900 + Smoke 900 -> subsampled to 900).
          Any DeepQuestAI training image that is a confirmed twin of a FireNET image is KEPT,
          because that is exactly what a real researcher would do — they never checked.
  Test:   FireNET, all 502 images, all positive (class "fire", 701 boxes, verified).
          Metric is therefore RECALL (fraction of fire images the model calls fire).
  Split the test set by contamination status:
          CONTAMINATED  = the 218 FireNET images with a DeepQuestAI twin
          CLEAN         = the remaining 284
  Report recall on each, and the gap.

  Three architectures are trained so we can also ask the stronger question:
  DOES THE RANKING OF MODELS CHANGE between the contaminated and clean subsets?
  A ranking change is a much stronger claim than a score change: it means contamination
  alters which method a reader would conclude is best.

  Multiple seeds per architecture so the gap can be reported with a spread rather than as a
  single number.

Everything is derived from corpus/overlap_pairs.json, which is produced by
scripts/overlap_audit.py. Nothing here is hand-picked.
"""
import os, json, sys, random, hashlib
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
import torchvision.models as tvm
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DQ = os.path.join(ROOT, "datasets/deepquestai/FIRE-SMOKE-DATASET")
FN = os.path.join(ROOT, "datasets/firenet/fire-dataset")
DEV = "cuda" if torch.cuda.is_available() else "cpu"
SEEDS = [0, 1, 2]
EPOCHS = 6
BS = 32


def contaminated_firenet():
    """FireNET relative paths that have a confirmed DeepQuestAI twin."""
    P = json.load(open(os.path.join(ROOT, "corpus/overlap_pairs.json"), encoding="utf-8"))
    key = None
    for k in P["cross"]:
        if "FireNET" in k and "DeepQuestAI_FireSmoke" in k:
            key = k
            break
    if key is None:
        sys.exit("cross pair list not found - run overlap_audit.py first")
    # in compare(A,B) A=DeepQuestAI_FireSmoke, B=FireNET (alphabetical), so 'b' is FireNET
    return {p["b"] for p in P["cross"][key]}


class ListDS(Dataset):
    def __init__(self, items, tf):
        self.items, self.tf = items, tf

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        p, y = self.items[i]
        try:
            im = Image.open(p).convert("RGB")
        except Exception:
            im = Image.new("RGB", (224, 224))
        return self.tf(im), y


TF_TRAIN = transforms.Compose([
    transforms.Resize((256, 256)), transforms.RandomCrop(224),
    transforms.RandomHorizontalFlip(), transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
TF_EVAL = transforms.Compose([
    transforms.Resize((224, 224)), transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])


def build_train(seed):
    rng = random.Random(seed)
    fire = [(os.path.join(DQ, "Train/Fire", f), 1)
            for f in sorted(os.listdir(os.path.join(DQ, "Train/Fire")))]
    neu = [(os.path.join(DQ, "Train/Neutral", f), 0)
           for f in sorted(os.listdir(os.path.join(DQ, "Train/Neutral")))]
    smoke = [(os.path.join(DQ, "Train/Smoke", f), 0)
             for f in sorted(os.listdir(os.path.join(DQ, "Train/Smoke")))]
    neg = neu + smoke
    rng.shuffle(neg)
    neg = neg[:len(fire)]          # balance
    items = fire + neg
    rng.shuffle(items)
    return items


def build_test():
    contam = contaminated_firenet()
    items, flags = [], []
    for split in ("train/images", "validation/images"):
        d = os.path.join(FN, split)
        for f in sorted(os.listdir(d)):
            if os.path.splitext(f)[1].lower() not in (".jpg", ".jpeg", ".png", ".bmp"):
                continue
            rel = f"{split}/{f}"
            items.append((os.path.join(d, f), 1))   # FireNET is all-positive
            flags.append(rel in contam)
    return items, np.array(flags)


def make_model(name):
    if name == "resnet18":
        m = tvm.resnet18(weights=tvm.ResNet18_Weights.IMAGENET1K_V1)
        m.fc = nn.Linear(m.fc.in_features, 2)
    elif name == "mobilenet_v3_small":
        m = tvm.mobilenet_v3_small(weights=tvm.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
        m.classifier[3] = nn.Linear(m.classifier[3].in_features, 2)
    elif name == "efficientnet_b0":
        m = tvm.efficientnet_b0(weights=tvm.EfficientNet_B0_Weights.IMAGENET1K_V1)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, 2)
    else:
        raise ValueError(name)
    return m.to(DEV)


def run(arch, seed, train_items, test_items, flags):
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    m = make_model(arch)
    tl = DataLoader(ListDS(train_items, TF_TRAIN), batch_size=BS, shuffle=True,
                    num_workers=0, drop_last=True)
    opt = torch.optim.AdamW(m.parameters(), lr=3e-4, weight_decay=1e-4)
    lossf = nn.CrossEntropyLoss()
    m.train()
    for ep in range(EPOCHS):
        tot = n = 0
        for x, y in tl:
            x, y = x.to(DEV), y.to(DEV)
            opt.zero_grad()
            l = lossf(m(x), y)
            l.backward()
            opt.step()
            tot += l.item() * len(y)
            n += len(y)
        print(f"    {arch} s{seed} ep{ep+1}/{EPOCHS} loss {tot/max(1,n):.4f}", flush=True)
    m.eval()
    preds = []
    dl = DataLoader(ListDS(test_items, TF_EVAL), batch_size=64, shuffle=False, num_workers=0)
    with torch.no_grad():
        for x, _ in dl:
            preds.append(m(x.to(DEV)).argmax(1).cpu().numpy())
    preds = np.concatenate(preds)
    rec_all = float((preds == 1).mean())
    rec_con = float((preds[flags] == 1).mean())
    rec_cln = float((preds[~flags] == 1).mean())
    return {"arch": arch, "seed": seed, "recall_all": rec_all,
            "recall_contaminated": rec_con, "recall_clean": rec_cln,
            "gap": rec_con - rec_cln,
            "n_contaminated": int(flags.sum()), "n_clean": int((~flags).sum())}


if __name__ == "__main__":
    test_items, flags = build_test()
    print(f"TEST: FireNET n={len(test_items)}  contaminated={flags.sum()} "
          f"({100*flags.mean():.1f}%)  clean={(~flags).sum()}", flush=True)
    results = []
    for arch in ["resnet18", "mobilenet_v3_small", "efficientnet_b0"]:
        for seed in SEEDS:
            tr = build_train(seed)
            print(f"  TRAIN {arch} seed={seed} n={len(tr)}", flush=True)
            r = run(arch, seed, tr, test_items, flags)
            print(f"  -> all {r['recall_all']:.4f} | contam {r['recall_contaminated']:.4f} "
                  f"| clean {r['recall_clean']:.4f} | GAP {r['gap']:+.4f}", flush=True)
            results.append(r)
            json.dump(results, open(os.path.join(ROOT, "corpus/decontamination_results.json"),
                                    "w"), indent=1)
    print("\n=== SUMMARY ===")
    for arch in ["resnet18", "mobilenet_v3_small", "efficientnet_b0"]:
        rs = [r for r in results if r["arch"] == arch]
        if not rs:
            continue
        f = lambda k: (np.mean([r[k] for r in rs]), np.std([r[k] for r in rs]))
        a, sa = f("recall_all"); c, sc = f("recall_contaminated"); q, sq = f("recall_clean")
        g, sg = f("gap")
        print(f"{arch:22s} all {a:.4f}+-{sa:.4f}  contam {c:.4f}+-{sc:.4f}  "
              f"clean {q:.4f}+-{sq:.4f}  GAP {g:+.4f}+-{sg:.4f}")
    print("\nRANKING CHECK (does contamination change which model looks best?)")
    for key in ["recall_all", "recall_contaminated", "recall_clean"]:
        order = sorted(["resnet18", "mobilenet_v3_small", "efficientnet_b0"],
                       key=lambda a: -np.mean([r[key] for r in results if r["arch"] == a]))
        print(f"  by {key:22s}: {' > '.join(order)}")
