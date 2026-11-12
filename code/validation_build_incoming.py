"""Central-construct packet for the newly retrieved in-scope papers.

Same extractor, same cue list and same sentence splitter as scripts/fulltext_validation_build.py,
run over the complete stored full text of every paper the full-text scope screen placed in scope.
No quota, no truncation: the endpoint is an absence claim, and an absence built on a sampled
reading of the text is exactly the claim that needs the complete text.

Also reports, per paper, whether a learned model is trained at all. The endpoint's denominator is
the learned-model population, and a sensor system or an observational study belongs in scope
without belonging in that denominator.
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

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

# a learned model is trained if the text states training of a model, not merely a "training set"
LEARNED = [r"\btrain(?:ed|ing)\b.{0,40}\b(model|network|classifier|cnn|yolo|detector|architecture)",
           r"\b(model|network|classifier|cnn|yolo|detector)\b.{0,40}\btrain(?:ed|ing)\b",
           r"\bepochs?\b", r"\blearning rate\b", r"\bfine[- ]tun\w+\b", r"\bpre[- ]trained\b",
           r"\bloss function\b", r"\bbackpropagat\w+\b", r"\bfitted? (?:a |the )?model\b"]
RXL = [re.compile(c, re.I) for c in LEARNED]


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
    dec = json.load(io.open("corpus/scope_incoming_decisions.json", encoding="utf-8"))
    in_scope = [d["paper_id"] for d in dec["decisions"] if d["in_scope"]]

    packet = []
    for pid in sorted(in_scope):
        raw = io.open(f"corpus/ft_incoming/txt/{pid}.txt", encoding="utf-8",
                      errors="replace").read()
        sents = sentences(raw)
        hits = [s for s in sents if any(r.search(s) for r in RX)]
        learned_hits = [s for s in sents if any(r.search(s) for r in RXL)]
        packet.append({
            "paper_id": pid,
            "chars": len(raw),
            "n_sentences": len(sents),
            "n_partition_sentences": len(hits),
            "learned_model_cues": len(learned_hits),
            "learned_model_evidence": learned_hits[:3],
            "sentences": hits,
        })

    json.dump(packet, io.open("corpus/validation_packet_incoming.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print(f"packet: {len(packet)} in-scope papers")
    print(f"{'paper':<14}{'sents':>7}{'partition':>11}{'learned cues':>14}")
    for r in packet:
        print(f"{r['paper_id']:<14}{r['n_sentences']:>7}{r['n_partition_sentences']:>11}"
              f"{r['learned_model_cues']:>14}")


if __name__ == "__main__":
    main()
