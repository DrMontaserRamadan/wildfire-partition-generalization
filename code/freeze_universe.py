"""
Freeze the eligible-paper universe and build the retrieval table.

Run BEFORE any further retrieval so that later acquisitions can only fill cells in a fixed
table -- they can never change which papers were eligible. The frozen file carries a SHA-256
so any later edit is detectable.

Output:
  corpus/UNIVERSE_FROZEN.json   the immutable eligible list + checksum
  corpus/retrieval_table.csv    paper | year | venue | publisher | doi | eligible |
                                fulltext_obtained | retrieval_route | failure_reason
"""
import json, os, csv, hashlib, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

PUB_PREFIX = [
    ("10.3390", "MDPI"), ("10.1109", "IEEE"), ("10.1016", "Elsevier"),
    ("10.1007", "Springer"), ("10.1080", "Taylor & Francis"), ("10.1002", "Wiley"),
    ("10.1049", "IET (Wiley)"), ("10.1038", "Nature Portfolio"), ("10.1371", "PLOS"),
    ("10.3389", "Frontiers"), ("10.1071", "CSIRO"), ("10.1186", "BMC/SpringerOpen"),
    ("10.1155", "Hindawi (Wiley)"), ("10.5194", "Copernicus"), ("10.1088", "IOP"),
    ("10.1117", "SPIE"), ("10.1145", "ACM"), ("10.3844", "Science Publications"),
    ("10.1061", "ASCE"), ("10.1021", "ACS"),
]


def publisher(doi):
    for p, n in PUB_PREFIX:
        if (doi or "").startswith(p):
            return n
    return "other/small publisher" if doi else "no DOI"


def route_for(rec, ftkey):
    """How the full text was obtained, from the acquisition evidence on disk."""
    p = f"corpus/ft/{ftkey}.txt"
    if not (os.path.exists(p) and os.path.getsize(p) > 5000):
        return None
    if os.path.exists(f"corpus/ft/{ftkey}.pdf"):
        return "PDF via Unpaywall/repository"
    pub = publisher(rec.get("doi", ""))
    if pub == "MDPI":
        return "browser same-origin fetch (mdpi.com)"
    if pub == "Springer":
        return "browser same-origin fetch (link.springer.com)"
    if "101248" in (rec.get("doi") or ""):
        return "author-supplied PDF"
    return "automated HTTP (unpaywall/epmc/s2/oa_url)"


def key_is_author_supplied(ftkey):
    return os.path.exists(f"intake/{ftkey}.pdf")


def retrieved_before_author_batch(paper_id):
    """True if corpus/acquisition_record.json already had the full text pre-batch.

    An author-supplied PDF that arrives for a paper we had already retrieved does not
    become the provenance of the text we analysed. Labelling it author-supplied
    overstates what the manual batch unlocked.
    """
    return paper_id in _PRE_BATCH_RETRIEVED


def _load_pre_batch():
    try:
        recs = json.load(open("corpus/acquisition_record.json", encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return {r["id"] for r in recs if r.get("fulltext")}


_PRE_BATCH_RETRIEVED = _load_pre_batch()


def exclusion_blocks(excluded):
    """Group the excluded records by the reason they were actually excluded.

    The records carry a written `_exclusion_reason` when they were dropped on scope after
    full-text inspection. Records without one were dropped earlier as reviews/surveys.
    Reporting both groups under a single 'review/survey' label misstates why ten papers
    left the sample.
    """
    scope = [x for x in excluded if x.get("_exclusion_reason")]
    reviews = [x for x in excluded if not x.get("_exclusion_reason")]
    blocks = []
    if reviews:
        blocks.append({
            "reason": "document type is a review/survey, not a primary study",
            "stage": "title/abstract screen, before retrieval",
            "n": len(reviews),
            "ids": [x["id"] for x in reviews],
        })
    if scope:
        blocks.append({
            "reason": "out of scope on full-text inspection (see per-record _exclusion_reason)",
            "stage": "full-text screen, author-supplied batch",
            "n": len(scope),
            "ids": [x["id"] for x in scope],
            "per_record_reasons": {x["id"]: x["_exclusion_reason"] for x in scope},
        })
    return blocks


def main():
    sample = json.load(open("corpus/sample.json", encoding="utf-8"))
    excluded_reviews = json.load(open("corpus/excluded_reviews_records.json", encoding="utf-8"))

    import hashlib as _h
    rows = []
    for r in sample:
        ftkey = _h.md5(r["id"].encode()).hexdigest()[:12]
        p = f"corpus/ft/{ftkey}.txt"
        got = os.path.exists(p) and os.path.getsize(p) > 5000
        route = route_for(r, ftkey) if got else ""
        if got:
            reason = ""
            if key_is_author_supplied(ftkey):
                if retrieved_before_author_batch(r["id"]):
                    route = (route + "; a duplicate author-supplied PDF also exists"
                             " (text analysed predates the manual batch)")
                else:
                    route = "author-supplied PDF (publisher blocks automated retrieval)"
        elif not r.get("oa"):
            reason = "paywalled - no open-access copy located"
        else:
            reason = ("open access but publisher blocks retrieval "
                      "(client-side rendering or bot protection)")
        rows.append({
            "paper_id": r["id"],
            "title": r["title"],
            "year": r["year"],
            "venue": r["venue"],
            "publisher": publisher(r.get("doi", "")),
            "doi": r.get("doi", ""),
            "modality": r.get("mod", ""),
            "cites": r.get("cites", 0),
            "open_access": bool(r.get("oa")),
            "eligible": True,
            "fulltext_obtained": bool(got),
            "fulltext_chars": os.path.getsize(p) if got else 0,
            "retrieval_route": route,
            "failure_reason": reason,
            "ftkey": ftkey,
        })

    payload = {
        "frozen_at": datetime.datetime.now().replace(microsecond=0).isoformat(),
        "n_eligible": len(rows),
        "excluded_before_freeze": exclusion_blocks(excluded_reviews),
        "eligibility_criteria": [
            "primary research article reporting a wildfire/forest-fire detection method",
            "publication year >= 2020",
            "indexed venue (predatory/preprint-only venues removed)",
            "abstract of at least 250 characters available",
            "detection/recognition is the subject of the TITLE",
            "not a review, survey, taxonomy or bibliometric study",
        ],
        "papers": rows,
    }
    blob = json.dumps(payload["papers"], sort_keys=True).encode()
    payload["universe_sha256"] = hashlib.sha256(blob).hexdigest()

    json.dump(payload, open("corpus/UNIVERSE_FROZEN.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    cols = ["paper_id", "title", "year", "venue", "publisher", "doi", "modality", "cites",
            "open_access", "eligible", "fulltext_obtained", "fulltext_chars",
            "retrieval_route", "failure_reason"]
    with open("corpus/retrieval_table.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    from collections import Counter
    got = [r for r in rows if r["fulltext_obtained"]]
    print(f"UNIVERSE FROZEN  n_eligible={len(rows)}  sha256={payload['universe_sha256'][:16]}...")
    print(f"retrieved={len(got)}  rate={100*len(got)/len(rows):.1f}%")
    print("\npublisher            eligible  retrieved   rate")
    pe = Counter(r["publisher"] for r in rows)
    pg = Counter(r["publisher"] for r in got)
    for k, v in pe.most_common():
        g = pg.get(k, 0)
        print(f"  {k:26s} {v:5d} {g:9d} {100*g/v:7.1f}%")
    print("\nfailure reasons:")
    for k, v in Counter(r["failure_reason"] for r in rows if not r["fulltext_obtained"]).items():
        print(f"  {v:4d}  {k}")
    print("\nwrote corpus/UNIVERSE_FROZEN.json and corpus/retrieval_table.csv")


if __name__ == "__main__":
    main()
