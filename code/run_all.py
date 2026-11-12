"""Run the frozen experiment: 4 models x 19 partitions = 76 runs.

The replicate count is five, which is what section 7 of the protocol assumes. It was cut to three
on 2026-09-11 as the pre-specified response to a measured overrun: the pilots came in at 11.99
GPU-hours per partition against a pre-pilot estimate of about four, which put the full design near
215 hours of a home RTX 2070. That cut was restored on 2026-09-15, before any result existed, when
the sweep moved to rented hardware and the same design came to roughly 61 hours.

The reason is not only the bill. Section 7 defines the split-noise floor as the largest gap between
any two P1 replicates, and no rank movement below that floor may be reported as a finding.
Estimated from three replicates rather than five the floor comes out smaller, which makes rank
movement easier to call a finding - anti-conservative exactly where E3 and E4 are most exposed.

Resumable: a run whose result JSON already exists is skipped, so an interruption costs at most the
run in flight. Each run is a separate process, which keeps a crash or an out-of-memory event from
taking the whole sweep with it.
"""
import io
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SEEDS = [20260911, 20260912, 20260913, 20260914, 20260915]   # 5 replicates, as section 7 assumes
PARTNERS = [20260911, 20260912, 20260913]                    # P4 is three partners, not replicates
MODELS = ["yolov8n", "yolov8s", "fasterrcnn", "retinanet"]

PARTITIONS = []
for proto in ("P1_random_image", "P2_event_disjoint", "P3_camera_disjoint"):
    PARTITIONS += [f"{proto}__seed{s}" for s in SEEDS]
PARTITIONS += [f"P4_partner_lopo__seed{s}" for s in PARTNERS]
PARTITIONS.append("P5_temporal__seed20260911")               # deterministic, one split

RESULTS = "corpus/experiment_runs"
LOG = "corpus/run_all_log.jsonl"
HARDWARE = "corpus/sweep_hardware.json"


def finished():
    """Result files that count towards the 52. Pilots are timing measurements, not results."""
    return sorted(f for f in os.listdir(RESULTS) if f.endswith(".json") and "__PILOT" not in f)


def gate_one_gpu():
    """Refuse to extend a partly-finished sweep on a different card.

    The design holds corpus, model and training budget fixed so that the partition is the only
    thing that varies. Two GPUs select different cuDNN kernels and different floating-point
    reduction orders, so a P1 run on one card and a P3 run on another are not exchangeable: a gap
    between them would confound hardware with protocol. Until now that rule lived in a README; here
    it is checked.

    Changing cards with nothing finished is allowed, and deliberately so - that is exactly what
    happened on 2026-09-11, when the local sweep was stopped at 0 of 52 and moved to a rented pod.
    Nothing can be confounded with nothing. The gate closes the moment the first result exists.

    This file is written here rather than inside each result record because scripts/run_experiment.py
    is hashed in corpus/PROTOCOL_FREEZE.json and must not be edited to add provenance.
    """
    import torch
    here = torch.cuda.get_device_name(0)
    done = finished()

    prior = json.load(io.open(HARDWARE, encoding="utf-8")) if os.path.exists(HARDWARE) else None
    if prior and done and prior["gpu"] != here:
        sys.exit(f"ABORT: this card is {here}, but the {len(done)} finished runs were measured on "
                 f"{prior['gpu']}\n  (sweep opened {prior['opened']}, first result {done[0]}).\n"
                 "  Continuing would confound hardware with partition. Either go back to the "
                 "original card,\n  or discard the finished runs and restart the sweep here. "
                 "That is a decision, not a patch.")

    if not prior or not done:
        rec = {"gpu": here, "opened": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "finished_when_opened": len(done),
               "n_runs": len(PARTITIONS) * len(MODELS),
               "note": "the card every run in this sweep is measured on; see deploy/README.md"}
        json.dump(rec, io.open(HARDWARE, "w", encoding="utf-8"), indent=1)
        print(f"single-GPU gate: opened on {here} with {len(done)} finished runs", flush=True)
    else:
        print(f"single-GPU gate: {here}, matches the {len(done)} finished runs", flush=True)
    return here


def main():
    os.makedirs(RESULTS, exist_ok=True)
    gpu = gate_one_gpu()
    todo = [(p, m) for p in PARTITIONS for m in MODELS
            if not os.path.exists(f"{RESULTS}/{m}__{p}.json")]
    done = len(PARTITIONS) * len(MODELS) - len(todo)
    print(f"{len(PARTITIONS)} partitions x {len(MODELS)} models = "
          f"{len(PARTITIONS)*len(MODELS)} runs; {done} already complete, {len(todo)} to run",
          flush=True)

    t_start = time.time()
    for i, (part, model) in enumerate(todo, 1):
        tag = f"{model}__{part}"
        print(f"\n[{i}/{len(todo)}] {tag}  (elapsed {(time.time()-t_start)/3600:.2f} h)",
              flush=True)
        t0 = time.time()
        r = subprocess.run([sys.executable, "scripts/run_experiment.py",
                            "--model", model, "--partition", part],
                           capture_output=True, text=True)
        dt = time.time() - t0
        ok = r.returncode == 0 and os.path.exists(f"{RESULTS}/{tag}.json")
        rec = {"tag": tag, "ok": ok, "returncode": r.returncode, "seconds": round(dt, 1),
               "gpu": gpu}
        if not ok:
            rec["stderr_tail"] = r.stderr[-2000:]
            print(f"  FAILED rc={r.returncode} after {dt/60:.1f} min", flush=True)
            print(r.stderr[-1500:], flush=True)
        else:
            m = json.load(io.open(f"{RESULTS}/{tag}.json", encoding="utf-8"))["metrics"]
            rec["map_50"] = m["map_50"]
            print(f"  OK mAP@50 {m['map_50']:.4f} in {dt/60:.1f} min", flush=True)
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    print(f"\nSWEEP COMPLETE in {(time.time()-t_start)/3600:.2f} h", flush=True)
    fin = [f for f in os.listdir(RESULTS) if "__PILOT" not in f]
    print(f"  {len(fin)} result files present", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
