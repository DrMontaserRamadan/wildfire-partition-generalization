"""Build coding excerpts targeted at the rubric's constructs.

Replaces an extractor that both coders independently reported as broken. The old version
opened a 4,500-character window at every cue hit; cues like "dataset" fire dozens of times, so
the merged windows swallowed the document and the 46,000-character cap then returned a PREFIX.
On the seed paper (108k chars) that dropped the entire Results section, and four other
excerpts came back with silent internal elisions.

This version works at sentence level with a per-construct quota, so no construct can be
starved by a verbose neighbour, and it reports what it could NOT find. An excerpt that omits
the split statement is indistinguishable, to a coder, from a paper that never made one —
which is precisely the distinction the central construct depends on.

Reads the scope layer and codes only papers verified in scope with usable full text.
"""
import json
import io
import os
import re
import hashlib
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# Rubric construct -> patterns. Ordered by how central the construct is to the paper's claims;
# the quota below spends the budget in this order.
CONSTRUCTS = [
    ("split_protocol", 14, [
        r"\b(train(?:ing)?|valid(?:ation)?|test(?:ing)?)\s+(?:set|subset|split|data|images|samples)\b",
        r"\b(?:divided|split|partition\w*|separated|allocat\w*)\s+(?:in)?to\b",
        r"\b\d{1,3}\s*[:%/]\s*\d{1,3}(?:\s*[:%/]\s*\d{1,3})?\b",
        r"\b(?:randomly|shuffl\w+|stratif\w+)\b",
        r"\bk[- ]?fold|cross[- ]validation\b",
        r"\b(?:hold[- ]?out|held[- ]out|official (?:test|split)|benchmark(?:'s)? (?:own )?test)\b",
        r"\b(?:disjoint|non[- ]overlapping|unseen (?:site|camera|event|fire|region))\b",
    ]),
    ("augmentation_timing", 10, [
        r"\b(?:augment\w+|rotat\w+|flip\w+|mirror\w+|oversampl\w+|SMOTE|mosaic)\b",
        r"\b(?:expand\w+|increas\w+|enlarg\w+)\s+(?:the\s+)?(?:dataset|data|number of images)\b",
        r"\bafter\s+(?:the\s+)?augment\w+\b",
        r"\btotal (?:number )?of\s+[\d,]+\s+images\b",
    ]),
    ("dataset_identity", 10, [
        r"\b(?:FLAME|D-?Fire|FireNet|BoWFire|Corsican|FiSmo|DeepFire|FASDD|FIgLib|M4SFWD|"
        r"USTC_SmokeRS|Foggia|DeepQuestAI|PyroNear|Roboflow|Kaggle|Mendeley)\b",
        r"\b(?:self[- ]collected|private dataset|our own dataset|we (?:collected|constructed|built))\b",
        r"\b(?:publicly available|open[- ]source dataset|data availability)\b",
        r"\b[\d,]{3,}\s+(?:images|frames|samples|scenes|patches)\b",
    ]),
    ("leakage_and_duplicates", 8, [
        r"\b(?:leak\w+|duplicat\w+|near[- ]duplicate|overlap\w*|contaminat\w+|same (?:video|scene|site|region))\b",
        r"\b(?:consecutive|adjacent|successive)\s+frames?\b",
        r"\bextracted?\s+frames?\s+from\b",
    ]),
    ("validity_of_number", 10, [
        r"\b(?:accuracy|precision|recall|F1|mAP|IoU|AUC|false[- ]positive rate|FPR|MCC)\b\s*(?:of|:|=|reach\w*)?\s*\d",
        r"\b(?:standard deviation|confidence interval|±|mean of\s+\d+\s+runs|seeds?|repetitions?)\b",
        r"\b(?:statistical\w*|significan\w+|t-test|Wilcoxon|p\s*[<=]\s*0)\b",
        r"\bablation\b",
        r"\bcompared? (?:with|to|against)\b.{0,60}\b(?:state[- ]of[- ]the[- ]art|existing|baseline|other)\b",
    ]),
    ("deployment", 10, [
        r"\b(?:field (?:test|trial|deployment|experiment)|real[- ]world deployment|deployed in)\b",
        r"\b(?:prescribed|controlled) burn\b",
        r"\b(?:real|actual|unplanned) (?:wildfire|forest fire)\b",
        r"\b(?:for|over|during)\s+\d+\s*(?:days?|weeks?|months?|fire seasons?)\b",
        r"\b\d+\s*(?:nodes?|cameras?|sensors?|towers?|UAVs?|drones?)\b",
        r"\b(?:km2|km²|hectares?|square kilomet\w+)\b",
    ]),
    ("operational_metrics", 10, [
        r"\bfalse alarms?\b",
        r"\b(?:detection|response|reaction) (?:time|latency|delay)\b",
        r"\b(?:smallest|minimum|min\.?) (?:detectable )?(?:fire|flame|smoke) (?:size|area)\b",
        r"\b(?:detection|sensing|coverage) (?:range|radius|distance)\b",
        r"\b(?:power consumption|current draw|mA\b|mW\b|battery life|energy consumption)\b",
        r"\b(?:FPS|frames per second|inference time|ms\b)\b.{0,80}\b(?:Jetson|Raspberry|Coral|ESP32|STM32|Xavier|Nano|edge device|embedded)\b",
        r"\b(?:Jetson|Raspberry Pi|Coral|ESP32|STM32|Xavier|Orin|Movidius|Kria)\b",
    ]),
    ("reproducibility", 6, [
        r"\b(?:github\.com|gitlab|zenodo|figshare|huggingface|ieee-dataport|doi\.org/10\.5281)\b",
        r"\b(?:code|source code|implementation|weights|model)\s+(?:is|are|will be)?\s*(?:publicly\s+)?available\b",
        r"\b(?:upon|on)\s+reasonable\s+request\b",
        r"\b(?:learning rate|batch size|epochs?|optimiz\w+|random seed|seed\s*=)\b",
    ]),
    ("external_validity", 8, [
        r"\bcross[- ]dataset\b",
        r"\b(?:generaliz\w+|unseen|held[- ]out) (?:dataset|domain|site|region|season)\b",
        r"\b(?:night|nighttime|low[- ]light|darkness|dusk|dawn)\b",
        r"\b(?:fog|haze|cloud|rain|snow|smog|dust|adverse weather)\b",
        r"\b(?:sunset|sun glare|glare|red[- ]coloured|fire[- ]like|smoke[- ]like|industrial smoke|agricultural burn)\b",
        r"\bearly[- ]stage smoke|incipient\b",
    ]),
]

CTX = 1          # neighbouring sentences kept either side of a hit
MIN_SENT = 25
MAX_SENT = 600
LANDING_PAGE_CHARS = 8000   # below this, a "full text" is almost certainly a landing page


def split_sentences(text):
    """Sentence spans as (start, end), tolerant of the noise in scraped article text."""
    spans = []
    start = 0
    for m in re.finditer(r"(?<=[.!?])\s+(?=[A-ZÀ-ſ(\[])|\n{2,}", text):
        end = m.start()
        if MIN_SENT <= end - start <= MAX_SENT:
            spans.append((start, end))
        elif end - start > MAX_SENT:
            # long unpunctuated run (tables, reference blocks): chop into readable pieces
            for i in range(start, end, MAX_SENT):
                spans.append((i, min(i + MAX_SENT, end)))
        start = m.end()
    if len(text) - start >= MIN_SENT:
        spans.append((start, min(len(text), start + MAX_SENT)))
    return spans


def build_excerpt(text):
    spans = split_sentences(text)
    sents = [text[a:b] for a, b in spans]
    lows = [s.lower() for s in sents]

    chosen = {}          # sentence index -> set of constructs that selected it
    found = Counter()
    for name, quota, pats in CONSTRUCTS:
        rx = [re.compile(p, re.I) for p in pats]
        scored = []
        for i, low in enumerate(lows):
            hits = sum(1 for r in rx if r.search(low))
            if hits:
                scored.append((hits, -abs(len(sents[i]) - 180), i))
        scored.sort(reverse=True)
        found[name] = len(scored)
        for _, _, i in scored[:quota]:
            for j in range(max(0, i - CTX), min(len(sents), i + CTX + 1)):
                chosen.setdefault(j, set())
            chosen[i].add(name)

    if not chosen:
        return None, found, []

    keep = sorted(chosen)
    parts, prev = [], None
    for i in keep:
        if prev is not None and i > prev + 1:
            parts.append(f"\n\n[... {i - prev - 1} sentences omitted ...]\n\n")
        tags = chosen[i]
        parts.append((f"«{'/'.join(sorted(tags))}» " if tags else "") + sents[i].strip() + " ")
        prev = i
    missing = [name for name, _, _ in CONSTRUCTS if not found[name]]
    return "".join(parts), found, missing


def main():
    scope = json.load(io.open("corpus/scope_final.json", encoding="utf-8"))
    in_scope = [r for r in scope if r["in_scope"] and r["scope_tier"] in ("A", "B")]

    out, skipped = [], []
    for r in in_scope:
        key = hashlib.md5(r["paper_id"].encode()).hexdigest()[:12]
        path = f"corpus/ft/{key}.txt"
        if not os.path.exists(path):
            skipped.append((r["paper_id"], "no full text on disk"))
            continue
        text = io.open(path, encoding="utf-8", errors="replace").read()
        if len(text) < LANDING_PAGE_CHARS:
            skipped.append((r["paper_id"], f"only {len(text)} chars - landing page, not an article"))
            continue
        excerpt, found, missing = build_excerpt(text)
        if excerpt is None:
            skipped.append((r["paper_id"], "no construct evidence found at all"))
            continue
        out.append({
            "paper_id": r["paper_id"], "title": r["title"], "year": r["year"],
            "venue": r.get("venue", ""), "publisher": r["publisher"],
            "modality": r["modality"], "ftkey": key,
            "chars_full": len(text), "chars_excerpt": len(excerpt),
            "coverage_fraction": round(len(excerpt) / len(text), 3),
            "constructs_found": dict(found),
            "constructs_with_no_evidence": missing,
            "excerpt": excerpt,
        })

    json.dump(out, io.open("corpus/to_code.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    print(f"READY TO CODE: {len(out)} in-scope papers with usable full text")
    if skipped:
        print(f"\nskipped ({len(skipped)}):")
        for pid, why in skipped:
            print(f"  {pid}  {why}")
    ex = [o["chars_excerpt"] for o in out]
    full = [o["chars_full"] for o in out]
    ex.sort()
    print(f"\nexcerpt chars  median {ex[len(ex)//2]}  min {ex[0]}  max {ex[-1]}")
    print(f"source chars   median {sorted(full)[len(full)//2]}  max {max(full)}")
    print("NO prefix truncation: excerpts are assembled from passages across the whole document.")

    print("\nconstructs with NO evidence anywhere in the paper (a finding, not a bug):")
    miss = Counter(m for o in out for m in o["constructs_with_no_evidence"])
    for name, _, _ in CONSTRUCTS:
        print(f"  {name:24s} {miss.get(name, 0):3d} of {len(out)} papers")
    print("\nby modality:", dict(Counter(o["modality"] for o in out)))


if __name__ == "__main__":
    main()
