"""Build a full-document validation packet for the central construct only.

The frozen coding was performed on targeted EXCERPTS. The prefix-regression test shows those
excerpts span the document, but spanning is not recall: a quota-limited extractor can still
miss the one sentence that states an allocation rule. The primary finding is an absence claim,
and an absence claim built on a lossy sampling of the text is exactly the claim that needs
independent checking against the complete article.

This packet therefore contains, for each of the 64 learned-model papers, EVERY sentence in the
COMPLETE stored full text that could bear on how observations were assigned to subsets. No
quota, no budget, no truncation. One variable only.

The frozen model codes are deliberately NOT included. This is validation, not an invitation to
reproduce the existing answer.
"""
import json
import io
import os
import re
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# Deliberately broad. Recall matters far more than precision here: a false positive costs the
# assessor a glance, a false negative silently manufactures an "absence".
CUES = [
    r"\btrain(?:ing)?\b", r"\bvalidat(?:ion|e|ed)\b", r"\btest(?:ing|ed)?\b",
    r"\bsplit\b", r"\bpartition\w*\b", r"\bdivid\w+\b", r"\ballocat\w+\b",
    r"\bassign\w+\b", r"\bseparat\w+\b", r"\bhold[- ]?out\b", r"\bheld[- ]out\b",
    r"\brandom\w*\b", r"\bshuffl\w+\b", r"\bstratif\w+\b",
    r"\bk[- ]?fold\b", r"\bcross[- ]validat\w+\b", r"\bfold\b",
    r"\bdisjoint\b", r"\bnon[- ]overlapping\b", r"\bunseen\b",
    r"\bratio\b", r"\d{1,3}\s*[:%/]\s*\d{1,3}", r"\b\d{1,2}0\s*%",
    r"\bsubset\b", r"\bproportion\b", r"\bper[- ]?(?:video|scene|camera|site|event|fire)\b",
    r"\bofficial\b", r"\bdesignated\b", r"\bprovided\b.{0,20}\b(?:split|set)\b",
    r"\baugment\w+\b", r"\bsame (?:video|scene|camera|site|fire|event|sequence)\b",
]
RX = [re.compile(c, re.I) for c in CUES]


def sentences(text):
    text = re.sub(r"\s+", " ", text)
    out, start = [], 0
    for m in re.finditer(r"(?<=[.!?;])\s+(?=[A-ZÀ-ſ(\[0-9])", text):
        seg = text[start:m.start()].strip()
        if 15 < len(seg) < 500:
            out.append(seg)
        elif len(seg) >= 500:
            for i in range(0, len(seg), 400):
                out.append(seg[i:i + 400])
        start = m.end()
    tail = text[start:].strip()
    if 15 < len(tail) < 500:
        out.append(tail)
    return out


def main():
    scope = {r["paper_id"]: r for r in
             json.load(io.open("corpus/scope_final.json", encoding="utf-8"))}
    A = {r["paper_id"]: r for r in
         json.load(io.open("corpus/raw_coding/coded_A_67.RAW.json", encoding="utf-8"))}
    learned = [p for p in A if str(A[p].get("split_protocol")) != "not_applicable"]

    packet = []
    for pid in learned:
        key = hashlib.md5(pid.encode()).hexdigest()[:12]
        raw = io.open(f"corpus/ft/{key}.txt", encoding="utf-8", errors="replace").read()
        sents = sentences(raw)
        hits = [s for s in sents if any(r.search(s) for r in RX)]
        # de-duplicate while preserving document order
        seen, keep = set(), []
        for s in hits:
            k = s[:120].lower()
            if k not in seen:
                seen.add(k)
                keep.append(s)
        packet.append({
            "paper_id": pid,
            "title": scope[pid]["title"],
            "chars_full": len(raw),
            "n_sentences_total": len(sents),
            "n_partition_relevant": len(keep),
            "evidence": keep,
        })

    packet.sort(key=lambda r: hashlib.sha256(("val:" + r["paper_id"]).encode()).hexdigest())
    json.dump(packet, io.open("corpus/fulltext_validation_packet.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    tot = sum(r["n_partition_relevant"] for r in packet)
    ex = sorted(r["n_partition_relevant"] for r in packet)
    print(f"validation packet: {len(packet)} learned-model papers")
    print(f"partition-relevant sentences: {tot} total, "
          f"median {ex[len(ex)//2]}, min {ex[0]}, max {ex[-1]}")
    thin = [r for r in packet if r["n_partition_relevant"] < 5]
    print(f"papers with fewer than 5 candidate sentences: {len(thin)}")
    for r in thin:
        print(f"   {r['paper_id']}  {r['n_partition_relevant']} sentences, "
              f"{r['chars_full']} chars")
    print("\nFrozen model codes are NOT in this packet.")


if __name__ == "__main__":
    main()
