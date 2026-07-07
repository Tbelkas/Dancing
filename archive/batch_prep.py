"""batch_prep.py — run prep_sections over the long no-chip queue + re-sourced ids;
record dur/chapters/caplines into _proto/chip_triage.tsv (videoDbId, ytid, danceid, dur,
chapters, caplines, name). Resumable. Network-heavy."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")

queue = []
for l in open("_proto/chip_long_queue.tsv", encoding="utf-8"):
    p = l.rstrip("\n").split("\t")
    if len(p) >= 5:
        queue.append(p)  # vid ytid danceid dur name
# re-sourced videos (videoRowId, ytid, danceid, name) — durations unknown, prep will fetch
RESOURCED = [("433","KFo9wrVVqA4","446","Knee Slide"),
             ("464","ezYQ_emrvJc","477","The Slide"),
             ("402","zn81KebgGNg","411","Spiral")]

done = {}
out_path = "_proto/chip_triage.tsv"
if os.path.exists(out_path):
    for l in open(out_path, encoding="utf-8"):
        p = l.rstrip("\n").split("\t")
        if len(p) >= 2: done[p[1]] = True

f = open(out_path, "a", encoding="utf-8")
items = [(p[0], p[1], p[2], p[4]) for p in queue] + RESOURCED
for i, (vrow, yt, did, name) in enumerate(items):
    if yt in done:
        continue
    try:
        p = subprocess.run([sys.executable, "prep_sections.py", yt],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        line = (p.stdout or "").strip().splitlines()
        summ = line[-1] if line else "FAIL"
        dur = ch = cap = "?"
        for tok in summ.split():
            if tok.startswith("dur="): dur = tok[4:]
            if tok.startswith("chapters="): ch = tok[9:]
            if tok.startswith("caplines="): cap = tok[9:]
    except Exception as e:
        dur = ch = cap = "ERR"
    f.write(f"{vrow}\t{yt}\t{did}\t{dur}\t{ch}\t{cap}\t{name}\n"); f.flush()
    print(f"{i+1}/{len(items)} {yt} dur={dur} ch={ch} cap={cap} {name}", flush=True)
f.close()
print("done")
