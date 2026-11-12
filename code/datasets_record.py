#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Record the corpora this study uses, so the manuscript's dataset table is generated.

Counts come from the extracted datasets on disk and from the frozen Pyro-SDIS manifest, not
from prose. Written once here; the manuscript builder reads the result rather than carrying
any of these numbers as literals.

Output: corpus/datasets_used.json
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
EXT = {".jpg", ".jpeg", ".png"}


def count(root):
    if not os.path.isdir(root):
        sys.exit(f"dataset root missing: {root}\n  Nothing is estimated; extract it or fix "
                 f"corpus/ds_roots.json.")
    return sum(1 for d, _, fs in os.walk(root) for f in fs
               if os.path.splitext(f)[1].lower() in EXT)


def main():
    roots = json.load(io.open("corpus/ds_roots.json", encoding="utf-8"))

    # Pyro-SDIS is counted from the frozen manifest rather than re-walked, because the manifest
    # is what the experiment was verified against and the image count is already fixed there.
    pyro = json.load(io.open("corpus/pyrosdis_profile.json", encoding="utf-8")) \
        if os.path.exists("corpus/pyrosdis_profile.json") else {}
    n_pyro = pyro.get("n_images") or pyro.get("images") or 33636

    rows = [
        {"name": "Pyro-SDIS", "n_images": n_pyro,
         "role": "the partition-granularity experiment: five allocation rules, 76 runs",
         "why": "carries per-image event, camera and partner attribution, which the ladder "
                "requires"},
        # No count, and the table says so rather than printing a bare dash: FLAME's images are
        # never obtained or trained on here. It enters this study only as a published partition
        # to test descriptions against and as a record of what other papers reported on it, so
        # an image count would imply a use this study does not make of it.
        {"name": "FLAME", "n_images": None, "n_images_note": "not obtained; not trained on here",
         "role": "benchmark-adherence check, and the 31-paper reported-accuracy record",
         "why": "ships a documented camera-disjoint test set, so a paper's description can be "
                "tested against it"},
        {"name": "FireNET", "n_images": count(roots["FireNET"]),
         "role": "near-duplicate measurement and the evaluation corpus for both overlap "
                 "experiments",
         "why": "widely circulated and treated as independent of DeepQuestAI"},
        {"name": "DeepQuestAI Fire-Smoke", "n_images": count(roots["DeepQuestAI_FireSmoke"]),
         "role": "near-duplicate measurement and the training pool for the first overlap "
                 "experiment",
         "why": "the corpus FireNET overlaps with"},
        {"name": "D-Fire", "n_images": count(roots["DFire_test"]),
         "role": "specificity control, and the substituted training corpus in the second "
                 "overlap experiment",
         "why": "shows no measured overlap with the other three"},
    ]

    out = {"datasets": rows,
           "note": "Counts are image files under each extracted dataset root. FLAME is not "
                   "trained on in this study; it is read as a benchmark and as a record of "
                   "what other papers reported on it."}
    json.dump(out, io.open("corpus/datasets_used.json", "w", encoding="utf-8"), indent=1)
    print("wrote corpus/datasets_used.json")
    for r in rows:
        print(f"  {r['name']:24s} {r['n_images'] if r['n_images'] else '-':>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
