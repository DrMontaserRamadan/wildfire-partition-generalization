#!/usr/bin/env bash
# Time the frozen experiment on a rented GPU, and only then - on a separate, explicit instruction -
# launch it.
#
#   bash deploy/runpod_run.sh              # pilot only. Measures this card and STOPS.
#   bash deploy/runpod_run.sh --sweep      # launch the 76-run sweep. Requires the pilot to exist.
#
# The default does not train the experiment. That is deliberate: the hour figures in the protocol
# were measured on an RTX 2070 and describe that card and no other, so the first thing a rented pod
# does is replace them with a measurement. The projected duration and cost are then reported and the
# decision to spend them is taken by a person, not by this script.
#
# Run deploy/runpod_setup.sh first. It verifies the environment, that the rebuilt partitions match
# the frozen hashes, and that the corpus is byte-identical to the one the design was frozen on.
set -euo pipefail

cd "$(dirname "$0")/.."

MODE="${1:-pilot}"

if [ ! -f corpus/split_manifest.json ]; then
  echo "ABORT: no split manifest. Run deploy/runpod_setup.sh first." >&2
  exit 1
fi

TOTAL=$(python -c "import sys; sys.path.insert(0,'scripts'); import run_all; \
print(len(run_all.PARTITIONS)*len(run_all.MODELS))")
DONE=$(ls corpus/experiment_runs/*.json 2>/dev/null | grep -vc PILOT || true)
GPU=$(python -c "import torch; print(torch.cuda.get_device_name(0))")
echo "card: ${GPU}"
echo "results already present: ${DONE} of ${TOTAL}"

# ---------------------------------------------------------------------------------------------
if [ "$MODE" != "--sweep" ]; then
  echo
  echo "=== timing pilot: one epoch of each of the four models on THIS card ==="
  # All four, not just the budget driver. A single RetinaNet pilot would calibrate RetinaNet and
  # then assume the same speed-up describes the YOLO arms, which run different kernels entirely.
  # Four one-epoch pilots cost about twenty minutes and remove that assumption.
  #
  # The RTX 2070 pilots are the measurements the budget was sized from, and run_experiment.py
  # writes pilots to a fixed filename, so they are moved aside rather than overwritten. That file
  # is hashed in the freeze and must not be edited to name pilots per-card.
  for m in yolov8n yolov8s fasterrcnn retinanet; do
    P="corpus/experiment_runs/${m}__P1_random_image__seed20260911__PILOT.json"
    if [ -f "$P" ] && [ ! -f "${P%.json}__rtx2070.json" ]; then
      mv "$P" "${P%.json}__rtx2070.json"
      echo "  preserved the RTX 2070 ${m} pilot"
    fi
    echo "  --- ${m}"
    python scripts/run_experiment.py --model "$m" \
        --partition P1_random_image__seed20260911 --pilot 2>&1 | tail -2
  done

  echo
  python - <<'PY'
import io, json, os, sys
sys.path.insert(0, "scripts")
import run_all

# Per-model speed-up against the RTX 2070 pilots, then the sweep repriced on this card. Nothing
# here is hardcoded: the run list comes from run_all and the 2070 baseline from the preserved
# pilot files, so neither can go stale if the design changes.
here, base = {}, {}
for m in run_all.MODELS:
    p = f"corpus/experiment_runs/{m}__P1_random_image__seed20260911__PILOT.json"
    b = f"{p[:-5]}__rtx2070.json"
    if not os.path.exists(p):
        sys.exit(f"ABORT: {p} was not written. The pilot did not complete.")
    if not os.path.exists(b):
        sys.exit(f"ABORT: {b} is missing, so there is no 2070 baseline to compare against.")
    here[m] = json.load(io.open(p, encoding="utf-8"))
    base[m] = json.load(io.open(b, encoding="utf-8"))

print(f"  {'model':<11} {'2070 s/epoch':>13} {'here s/epoch':>13} {'speed-up':>9}")
sp = {}
for m in run_all.MODELS:
    a, c = base[m]["train_seconds"], here[m]["train_seconds"]
    sp[m] = a / c if c else float("nan")
    print(f"  {m:<11} {a:>13.1f} {c:>13.1f} {sp[m]:>8.2f}x")

man = json.load(io.open("corpus/split_manifest.json", encoding="utf-8"))["partitions"]
EP = 25
total = 0.0
for part in run_all.PARTITIONS:
    n_tr = min(21995 if not part.startswith("P4") else 13836, man[part]["train"]["images"])
    n_io = man[part]["test"]["images"] + man[part]["val"]["images"]
    for m in run_all.MODELS:
        b = base[m]
        tr = EP * n_tr * (b["train_seconds"] / b["n_train_used"]) / sp[m]
        ev = n_io * (b["eval_seconds"] / b["n_test"]) / sp[m]
        total += (tr + ev) / 3600

print(f"\n  whole sweep on this card : {total:.1f} GPU-hours ({total/24:.1f} days) "
      f"for {len(run_all.PARTITIONS)*len(run_all.MODELS)} runs")
for rate in (0.49, 0.74, 1.09):
    print(f"    at ${rate:.2f}/h : ${total*rate:,.0f}")
json.dump({"gpu_speedup_vs_rtx2070": sp, "projected_sweep_hours": total,
           "n_runs": len(run_all.PARTITIONS) * len(run_all.MODELS)},
          io.open("corpus/pilot_projection.json", "w", encoding="utf-8"), indent=1)
print("\n  wrote corpus/pilot_projection.json")
PY

  cat <<'EOF'

STOPPING HERE. The pilot has measured this card; the sweep has not started.

Report the numbers above, get approval, and only then run:
  bash deploy/runpod_run.sh --sweep
EOF
  exit 0
fi

# ---------------------------------------------------------------------------------------------
echo
echo "=== launching the sweep ==="
if ! ls corpus/experiment_runs/*__PILOT.json >/dev/null 2>&1; then
  echo "ABORT: no pilot on this card. Run 'bash deploy/runpod_run.sh' first and report it." >&2
  exit 1
fi

nohup python scripts/run_all.py > corpus/run_all_stdout.log 2>&1 &
echo "  pid $!"
sleep 20
head -8 corpus/run_all_stdout.log

cat <<'EOF'

Monitor with:
  tail -f corpus/run_all_stdout.log
  ls corpus/experiment_runs/*.json | grep -v PILOT | wc -l      # out of 76
  grep '"ok": false' corpus/run_all_log.jsonl                   # failures

Pull results down regularly - a terminated pod takes them with it:
  rsync -av <pod>:<path>/corpus/experiment_runs/ ./corpus/experiment_runs/
  rsync -av <pod>:<path>/corpus/predictions/     ./corpus/predictions/
  rsync -av <pod>:<path>/corpus/checkpoints/     ./corpus/checkpoints/

The per-run JSONs are the primary record. The predictions let every secondary metric be recomputed
without a GPU; the checkpoints let inference be reproduced. Roughly 5.8 GB in total.
EOF
