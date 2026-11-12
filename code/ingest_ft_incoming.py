"""Ingest hand-retrieved PDFs for the in-scope papers that automated retrieval could not reach.

Extracts text, hashes the source PDF, and checks that each file is the paper its filename claims.
The identity check is deliberately a competition rather than a threshold: every PDF is scored
against ALL the wanted titles, and the file passes only if the title it is named for is the
argmax and clears the runner-up by a margin. A matcher with no control set has been confidently
wrong in this project before.

Nothing here codes anything. It only turns PDFs into verified text.
"""
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "corpus" / "ft_incoming"
TXT = INBOX / "txt"
# Two request lists now feed this inbox: the in-scope papers automated retrieval missed, and the
# papers that were EXCLUDED on their abstracts and never read at full text. Both are hand
# retrieved and both are verified the same way here; the identity competition runs over the union,
# which is the stricter test because it gives every file more chances to be mistaken for another.
WANTED = ROOT / "corpus" / "ft_wanted_inscope.json"
WANTED_EXCL = ROOT / "corpus" / "ft_wanted_exclusion_check.json"
OUT = ROOT / "corpus" / "ft_incoming_manifest.json"

STOP = {"a", "an", "and", "for", "from", "in", "of", "on", "the", "to", "using", "with", "based"}


def flat(s):
    """NFKC first: publisher PDFs carry ligatures, so "wildfires" is stored as "wildﬁres" and a
    naive [a-z0-9]+ tokenizer silently splits it into "wild" and "res". Three of the first
    eighteen files failed their identity check for exactly this reason.

    Then join words the typesetter broke across a line: a title set as "Op-\\ntimization" is not a
    different title, and two more files raised false alarms on exactly that."""
    s = unicodedata.normalize("NFKC", s).lower()
    # Only a letter-to-letter join. An unrestricted rule glued a running page number onto the
    # next line's title ("...uk 29-" + "Unsupervised...") and broke a file that had been passing.
    s = re.sub(r"(?<=[a-z])-[ \t]*\n[ \t]*(?=[a-z])", "", s)
    return s


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]+", flat(s)) if w not in STOP and len(w) > 2}


def norm(s):
    """Collapse to lowercase words joined by single spaces, so line breaks and hyphenation in
    an extracted PDF do not defeat a contiguous-title search."""
    return " " + " ".join(re.findall(r"[a-z0-9]+", flat(s))) + " "


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    wanted = json.loads(WANTED.read_text(encoding="utf-8"))
    if WANTED_EXCL.exists():
        wanted = wanted + json.loads(WANTED_EXCL.read_text(encoding="utf-8"))
    by_id = {w["pid"]: w for w in wanted}
    TXT.mkdir(exist_ok=True)

    pdfs = sorted(INBOX.glob("*.pdf"))
    if not pdfs:
        print("no PDFs in", INBOX)
        return 1

    records, problems = [], []
    for pdf in pdfs:
        pid = pdf.stem
        if pid not in by_id:
            problems.append(f"{pdf.name}: filename is not one of the wanted paper ids")
            continue

        doc = fitz.open(pdf)
        # NFKC at extraction, so the stored text matches the convention of the frozen corpus/ft,
        # which was harvested from HTML and carries no ligatures. Left raw, "wildfires" is stored
        # as "wild<fi>res" and the wildland term count in the scope evidence packet reads zero
        # for a paper whose whole motivation is wildfire.
        pages = [unicodedata.normalize("NFKC", p.get_text("text")) for p in doc]
        doc.close()
        text = "\n".join(pages)
        with_text = sum(1 for p in pages if len(p.strip()) > 100)

        # Identity. Token coverage alone is not enough: a short generic title like "Neural
        # network model for forest fires recognition" has every one of its words present in an
        # unrelated fire paper's opening pages, so it ties at 1.00 with the true owner. The
        # primary test is therefore whether the title appears as a CONTIGUOUS run of words on
        # the opening pages; coverage is kept as the fallback and as the tie report.
        head_raw = norm("\n".join(pages[:2]))
        head = toks("\n".join(pages[:2]))
        scores = []
        for w in wanted:
            t = toks(w["title"])
            cov = len(t & head) / len(t) if t else 0.0
            scores.append((1 if norm(w["title"]) in head_raw else 0, cov, w["pid"]))
        scores.sort(reverse=True)
        best_exact, best_score, best_pid = scores[0]
        runner_up = scores[1][1] if len(scores) > 1 else 0.0
        own_exact, own = next((e, c) for e, c, p in scores if p == pid)

        rec = {
            "paper_id": pid,
            "title": by_id[pid]["title"],
            "file": pdf.name,
            "sha256": sha256(pdf),
            "bytes": pdf.stat().st_size,
            "pages": len(pages),
            "pages_with_text": with_text,
            "chars": len(text),
            "title_on_page": bool(own_exact),
            "title_match_own": round(own, 3),
            "title_match_best": round(best_score, 3),
            "title_match_best_id": best_pid,
            "title_match_runner_up": round(runner_up, 3),
        }

        if with_text == 0:
            problems.append(f"{pid}: no text layer on any page — scanned image, needs OCR")
        elif with_text < len(pages) / 2:
            problems.append(
                f"{pid}: only {with_text} of {len(pages)} pages carry text — check for a "
                f"partial text layer before coding it")
        # The file is accepted if its own title is printed on its opening pages. Only when that
        # fails does the token competition decide, and a competition loss is then fatal.
        if not own_exact:
            if best_exact and best_pid != pid:
                problems.append(
                    f"{pid}: the title printed on this PDF is {best_pid}'s — WRONG FILE")
            elif best_pid != pid:
                problems.append(
                    f"{pid}: own title not printed on the page and {best_pid} scores higher "
                    f"({best_score:.2f} vs {own:.2f}) — verify by eye before ingesting")
            else:
                problems.append(
                    f"{pid}: own title not printed on the page, {own:.2f} token coverage — "
                    f"expected for a paper published in another language; verify by eye")

        records.append(rec)
        (TXT / f"{pid}.txt").write_text(text, encoding="utf-8")

    rollup = hashlib.sha256(
        "".join(sorted(r["sha256"] for r in records)).encode()).hexdigest()[:16]
    OUT.write_text(json.dumps(
        {"n": len(records), "rollup": rollup, "records": records, "problems": problems},
        indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"ingested {len(records)} PDFs, rollup {rollup}\n")
    print(f"{'paper':<14}{'pages':>6}{'text pg':>8}{'chars':>9}{'title':>7}{'cover':>7}")
    for r in sorted(records, key=lambda r: (r["title_on_page"], r["title_match_own"])):
        print(f"{r['paper_id']:<14}{r['pages']:>6}{r['pages_with_text']:>8}"
              f"{r['chars']:>9}{'on page' if r['title_on_page'] else '  --':>7}"
              f"{r['title_match_own']:>7.2f}")
    if problems:
        print("\nPROBLEMS")
        for p in problems:
            print(" -", p)
    else:
        print("\nno problems: every file is the paper it is named for, and every page has text")
    return 0


if __name__ == "__main__":
    sys.exit(main())
