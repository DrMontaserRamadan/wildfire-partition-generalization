"""Every reported fraction, as a record with its analysis population attached.

The repeated failure mode in this project has been the denominator, not the numerator. It has
gone wrong four times in different disguises: publishers scored against a frame that had already
had their failures removed; 67/101 where the ten full-text-verified exclusions belonged in the
denominator; a hardcoded tierA=24 that outlived the re-code; and two scripts printing different
totals for the same quantity.

The response is that no percentage may be typed. A fraction is a record — numerator,
denominator, and the NAMED analysis population the denominator must equal — and the percentage
is derived. `verify_headlines.py` recomputes every one and fails if any disagrees, or if a
denominator does not match the population it claims.

Populations are computed from frozen artefacts, never hardcoded.
"""
import json
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REGISTRY = os.path.join(ROOT, "corpus", "reported_fractions.json")


def _load(rel):
    return json.load(io.open(os.path.join(ROOT, rel), encoding="utf-8"))


def populations():
    """Named analysis populations, as id sets, derived from frozen source.

    A fraction whose denominator does not equal the size of its declared population, or a
    documented subset of it, is a defect and fails the gate.
    """
    scope = _load("corpus/scope_final.json")
    excl = [x for x in _load("corpus/excluded_reviews_records.json")
            if x.get("_exclusion_reason")]

    pops = {}

    # --- scope-analysis populations -------------------------------------------------
    # Every paper whose full text we read, INCLUDING the ten excluded on scope in the
    # author-supplied batch. Those ten are full-text-verified out-of-scope papers; omitting
    # them is the 67/101 error.
    verified = [r["paper_id"] for r in scope if r["scope_tier"] in ("A", "B")]
    pops["POP_VERIFIED"] = set(verified) | {x["id"] for x in excl}

    # The initially eligible candidate corpus, before any scope exclusion.
    pops["POP_CANDIDATE"] = {r["paper_id"] for r in scope} | {x["id"] for x in excl}

    # Papers that survived scope and have usable full text — the coding corpus.
    try:
        pops["POP_ALL"] = {d["paper_id"] for d in _load("corpus/to_code.json")}
    except (OSError, ValueError):
        pops["POP_ALL"] = set()

    pops["POP_RETRIEVAL_FAILURES"] = set()
    try:
        import csv
        rows = list(csv.DictReader(io.open(os.path.join(ROOT, "corpus/retrieval_table.csv"),
                                           encoding="utf-8")))
        pops["POP_RETRIEVAL_FAILURES"] = {r["paper_id"] for r in rows
                                          if r["fulltext_obtained"] != "True"}
    except (OSError, ValueError, KeyError):
        pass

    # Once the corpus is coded, the coding populations become checkable too. Without this the
    # gate would silently SKIP every prevalence denominator as "unknown population" — a gate
    # that passes by not looking is the failure mode this whole mechanism exists to prevent.
    try:
        coded = {r["paper_id"]: r for r in
                 _load("corpus/raw_coding/coded_A_67.RAW.json")}
        pops.update(coding_populations(coded))
    except (OSError, ValueError):
        pass

    return pops


def coding_populations(coded):
    """Populations that only exist once the corpus is coded.

    `coded` maps paper_id -> record. Defined here, in the same file as the others, so the
    rule for each denominator lives in one place and can be audited.
    """
    pops = {}
    pops["POP_ALL"] = set(coded)
    # POP_LEARNED: the construct applies only to papers that train a learned model.
    # not_applicable is an exclusion from the denominator and its count is reported.
    pops["POP_LEARNED"] = {p for p, r in coded.items()
                           if r.get("split_protocol") != "not_applicable"}
    pops["POP_FLAME"] = {p for p, r in coded.items()
                         if "flame" in str(r.get("datasets_used", "")).lower()}
    pops["POP_DEPLOY"] = {p for p, r in coded.items()
                          if str(r.get("deployment_level", "")).upper().startswith(("L1", "L2",
                                                                                    "L3", "L4",
                                                                                    "L5"))}
    return pops


def emit(fractions):
    """Write the registry. `fractions` is a list of dicts with the required keys."""
    required = {"id", "label", "numerator", "denominator", "population", "source"}
    for f in fractions:
        missing = required - set(f)
        if missing:
            raise ValueError(f"fraction {f.get('id')} missing {sorted(missing)}")
        if f["denominator"] == 0:
            raise ValueError(f"fraction {f['id']} has a zero denominator")
        if f["numerator"] > f["denominator"]:
            raise ValueError(f"fraction {f['id']}: numerator exceeds denominator")
        f["pct"] = round(100.0 * f["numerator"] / f["denominator"], 4)
    json.dump(fractions, io.open(REGISTRY, "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    return fractions


def load_registry():
    try:
        return json.load(io.open(REGISTRY, encoding="utf-8"))
    except (OSError, ValueError):
        return []
