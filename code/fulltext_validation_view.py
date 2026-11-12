"""Decision-focused view: sentences that plausibly STATE a partition, not merely mention a cue."""
import json, io, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# must contain a partition ACTION or an explicit subset-size statement
ACTION = re.compile(
    r"\b(?:split|splitting|divid\w+|partition\w*|separat\w+|allocat\w+|assign\w+|"
    r"select\w+ for|used for (?:train|test|valid)|set aside|hold[- ]?out|held[- ]?out|"
    r"cross[- ]validat\w+|k[- ]?fold|fold[s]?\b|randomly|shuffl\w+|stratif\w+)\b", re.I)
SUBSET = re.compile(r"\b(?:train(?:ing)?|valid(?:ation)?|test(?:ing)?)\b", re.I)
SIZE = re.compile(r"\d{1,3}\s*[:%/]\s*\d{1,3}|\b\d{1,3}\s?%|\b[\d,]{3,}\s+(?:images|frames|samples)")
# reject well-known false friends
NOISE = re.compile(r"shufflenet|random forest|aspect ratio|signal[- ]to[- ]noise|"
                   r"intersection over union|\bIoU\b|ratio of the intersection|"
                   r"channel split|channel shuffl|positive sample allocation|"
                   r"divides? an image into grid|divide each image into block", re.I)

lo, hi = int(sys.argv[1]), int(sys.argv[2])
P = json.load(io.open("corpus/fulltext_validation_packet.json", encoding="utf-8"))
out = []
for i, r in enumerate(P):
    if not (lo <= i < hi):
        continue
    keep = []
    for s in r["evidence"]:
        if NOISE.search(s):
            continue
        if ACTION.search(s) and SUBSET.search(s):
            keep.append(s)
        elif SIZE.search(s) and SUBSET.search(s):
            keep.append(s)
    out.append(f"[V{i:02d}] {r['paper_id']}  ({len(keep)} partition-statement candidates)")
    out.append(f"   T: {r['title'][:88]}")
    for s in keep[:14]:
        out.append(f"   . {s[:290]}")
    if not keep:
        out.append("   . (NO PARTITION STATEMENT FOUND IN COMPLETE FULL TEXT)")
    out.append("")
io.open("scratch_val.txt", "w", encoding="utf-8").write("\n".join(out))
print(f"rendered papers {lo}-{hi-1}")
