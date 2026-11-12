#!/usr/bin/env bash
# Provision a RunPod instance for the frozen partition-granularity experiment.
#
# Run once on a fresh pod. It installs the environment, pulls the corpus, rebuilds the partitions
# from the cached metadata, and verifies that the rebuilt splits are byte-identical to the ones
# frozen on 2026-09-11. If they are not, it refuses to continue: training on partitions that differ
# from the frozen ones would silently invalidate the experiment.
#
# Usage:
#   bash deploy/runpod_setup.sh
#   bash deploy/runpod_run.sh          # then launch the sweep
set -euo pipefail

# These are the hashes recorded in corpus/split_manifest.json when the design was frozen.
EXPECT_SPLIT_FILES="672c9fdf76ba4362"
EXPECT_MANIFEST="8463e20cbfbc93d3"

echo "=== 1. GPU ==="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

echo
echo "=== 2. Python environment ==="
# torchvision MUST match torch and MUST be the CUDA build. A CPU-only torchvision alongside a CUDA
# torch makes torchvision::nms raise NotImplementedError, which kills both torchvision detectors at
# their first evaluation — after a full training run has already been spent.
TORCH_VER=$(python -c "import torch; print(torch.__version__)")
echo "torch already present: ${TORCH_VER}"
python - <<'PY'
import torch, sys
cu = torch.version.cuda
print(f"  torch {torch.__version__}  cuda {cu}  available {torch.cuda.is_available()}")
if not torch.cuda.is_available():
    sys.exit("ABORT: torch cannot see a GPU")
PY

# Ubuntu 24.04 marks the system Python as externally managed (PEP 668), so pip refuses to install
# into it without being told. A virtualenv is the usual answer and is the wrong one here: torch
# 2.8.0+cu128 and its matching CUDA torchvision are ALREADY in the system Python, and an isolated
# venv would mean reinstalling multiple gigabytes of CUDA wheels to end up with what is already
# there - with a fresh chance of the CPU-only torchvision that cost a day the last time. The
# packages being added are pure additions and pull in no torch of their own.
PIP="python -m pip install --quiet --break-system-packages"
$PIP --upgrade pip
$PIP ultralytics torchmetrics pycocotools pyarrow fsspec aiohttp

# The install must not have swapped torch or torchvision underneath us.
python - <<'PY'
import sys, torch, torchvision
print(f"  after install: torch {torch.__version__}, torchvision {torchvision.__version__}")
if "+cu" not in torch.__version__ or "+cu" not in torchvision.__version__:
    sys.exit("ABORT: a CPU build replaced a CUDA build during install. Do not continue.")
PY

echo
echo "=== 3. Verify torchvision CUDA ops BEFORE anything expensive ==="
python - <<'PY'
import sys, torch, torchvision
print(f"  torchvision {torchvision.__version__}")
if "+cpu" in torchvision.__version__:
    sys.exit("ABORT: torchvision is a CPU-only build. Install the CUDA build matching torch, e.g.\n"
             "  pip install --index-url https://download.pytorch.org/whl/cu126 torchvision==<ver>+cu126")
from torchvision.ops import nms
b = torch.tensor([[0., 0., 10., 10.], [1., 1., 11., 11.]]).cuda()
s = torch.tensor([0.9, 0.8]).cuda()
print(f"  torchvision.ops.nms on CUDA -> {nms(b, s, 0.5).tolist()}  OK")
PY

echo
echo "=== 4. Extract the corpus (~3.3 GB from Hugging Face) ==="
if [ -f corpus/pyrosdis_extract.json ] && [ "$(ls datasets/pyrosdis/images 2>/dev/null | wc -l)" -eq 33636 ]; then
  echo "  already extracted, skipping"
else
  python scripts/pyrosdis_extract.py
fi

echo
echo "=== 5. Rebuild the partitions and verify against the frozen design ==="
# The frozen split_files_sha256 (672c9fdf76ba4362) was computed over split files WRITTEN ON
# WINDOWS, so every line ends CRLF. scripts/split_manifest.py hashes raw bytes, and the same script
# on Linux writes the same lines with LF. The byte hash therefore cannot match here no matter how
# correct the rebuild is - measured 2026-09-15: the Windows files normalise to
# 001da8e9e117698d, which is exactly what this machine produces. The partitions are identical; only
# the line terminators differ.
#
# So the byte hash is not the gate any more. Two platform-independent checks replace it, and
# together they are stricter than what they replace:
#   - the newline-normalised hash over all 57 split files, which pins the exact image lists;
#   - full equality of the rebuilt manifest's per-partition statistics against the frozen manifest,
#     which pins every image count, event and camera crossing and prevalence difference.
# A genuinely different corpus revision, a changed event definition or a non-deterministic grouping
# still fails both.
#
# scripts/split_manifest.py and corpus/split_manifest.json are both hashed in PROTOCOL_FREEZE rev 3,
# so the frozen manifest is restored afterwards rather than left overwritten by the rebuild.
EXPECT_SPLIT_FILES_NORM="001da8e9e117698df6f3e47e50c07df239dadef8140f0f7bb28a7003dcad6aaf"

cp -f corpus/split_manifest.json /tmp/split_manifest_frozen.json
python scripts/split_manifest.py > /tmp/split_rebuild.log 2>&1 || {
  echo "ABORT: the partition rebuild itself failed:" >&2; tail -20 /tmp/split_rebuild.log >&2; exit 1; }
tail -4 /tmp/split_rebuild.log

python - <<PY
import hashlib, io, json, os, sys

SPLITS = "datasets/pyrosdis/splits"
h = hashlib.sha256()
for fn in sorted(os.listdir(SPLITS)):
    h.update(io.open(f"{SPLITS}/{fn}", "rb").read().replace(b"\r\n", b"\n"))
norm = h.hexdigest()
print(f"  split files, newline-normalised {norm[:16]}   expected ${EXPECT_SPLIT_FILES_NORM:0:16}")
if norm != "${EXPECT_SPLIT_FILES_NORM}":
    sys.exit("\\nABORT: the rebuilt splits differ from the frozen ones. Do NOT train.\\n"
             "  This is content, not line endings - a different corpus revision, a changed event\\n"
             "  definition or a non-deterministic grouping would all show up here. Find the cause.")

frozen = json.load(io.open("/tmp/split_manifest_frozen.json", encoding="utf-8"))
rebuilt = json.load(io.open("corpus/split_manifest.json", encoding="utf-8"))
fp, rp = frozen["partitions"], rebuilt["partitions"]
if set(fp) != set(rp):
    sys.exit(f"\\nABORT: partition set changed.\\n  only frozen: {sorted(set(fp)-set(rp))}\\n"
             f"  only rebuilt: {sorted(set(rp)-set(fp))}")
diff = [k for k in sorted(fp) if fp[k] != rp[k]]
if diff:
    k = diff[0]
    sys.exit(f"\\nABORT: {len(diff)} partition(s) differ in their statistics, e.g. {k}:\\n"
             f"  frozen : {json.dumps(fp[k])[:300]}\\n  rebuilt: {json.dumps(rp[k])[:300]}")
print(f"  all {len(fp)} partitions match the frozen manifest exactly "
      "(image counts, crossings, prevalence)")
PY

# Restore the frozen manifest; the rebuild was a check, not a replacement.
cp -f /tmp/split_manifest_frozen.json corpus/split_manifest.json
echo "  frozen manifest restored, PROTOCOL_FREEZE stays intact"

echo
echo "=== 6. Verify the image bytes, not just the filenames ==="
# The check above proves the partitions are the frozen ones. It cannot prove the corpus is: the
# partitions are lists of filenames derived from corpus/pyrosdis_rows.json, which travels with the
# repository, so they match whatever images happen to sit on disk. scripts/pyrosdis_extract.py pulls
# from the hub's parquet-conversion endpoint with no revision pinned. A re-extract that returned
# different pixels under the same names would pass every check above and would never show up in a
# result. This is the only step that looks at the data itself.
#
# scripts/dataset_manifest.py --verify is not used here, for the same reason the raw split hash was
# dropped in step 5: it compares raw bytes, and corpus/dataset_manifest.json was built on Windows,
# where every non-empty .txt file ends its lines CRLF. On Linux the extractor writes LF, so it
# reports 28,194 files "changed" - measured 2026-09-15, and that number is exactly the count of
# non-empty text files (33,636 labels minus 5,499 empty ones, plus 57 split files). Not one image
# differed. The corpus is identical; the line terminators are not.
#
# The split is therefore by file type, and the strict check stays where it matters most:
#   - all 33,636 IMAGES are compared raw, per file, against the frozen manifest. Images are binary,
#     so this is already platform-independent, and pixels are the thing that cannot be re-derived.
#   - all 33,693 TEXT files are compared by a newline-normalised rollup over path and content.
# A changed corpus revision fails the first; an edited or reordered label fails the second.
EXPECT_TEXT_ROLLUP="0121ed79f11e98fe302150b2d7ee80edc679ae257e9233d20aa7d48c13c5d8e0"

python - <<PY
import hashlib, io, json, os, sys

DATA = "datasets/pyrosdis"
man = json.load(io.open("corpus/dataset_manifest.json", encoding="utf-8"))
want = man["files"]

missing, changed, n_img, n_txt = [], [], 0, 0
th = hashlib.sha256()
for rel in sorted(want):
    p = os.path.join(DATA, rel)
    if not os.path.exists(p):
        missing.append(rel)
        continue
    b = io.open(p, "rb").read()
    if rel.endswith(".txt"):
        n_txt += 1
        nb = b.replace(b"\r\n", b"\n")
        th.update(rel.encode() + b"\0" + hashlib.sha256(nb).digest())
    else:
        n_img += 1
        if hashlib.sha256(b).hexdigest() != want[rel][0]:
            changed.append(rel)

roll = th.hexdigest()
print(f"  images compared raw : {n_img:,}   differing {len(changed)}")
print(f"  text files rollup   : {n_txt:,}   {roll[:16]}   expected ${EXPECT_TEXT_ROLLUP:0:16}")
if missing:
    sys.exit(f"\\nABORT: {len(missing)} file(s) missing, e.g. {missing[:3]}")
if changed:
    sys.exit(f"\\nABORT: {len(changed)} IMAGE(s) differ from the frozen corpus, e.g. {changed[:3]}.\\n"
             "  Same filename, different pixels. Do NOT train - every other check would pass and\\n"
             "  the difference would never appear in a result.")
if roll != "${EXPECT_TEXT_ROLLUP}":
    sys.exit("\\nABORT: label or split content differs from the frozen corpus.\\n"
             "  This is not line endings - those are normalised here. Find the cause.")
print("  this corpus is the one the design was frozen on.")
PY

echo
echo "=== 7. Ready ==="
echo "  Launch with:  bash deploy/runpod_run.sh"
echo "  Results land in corpus/experiment_runs/ — pull those down; the weights are disposable."
