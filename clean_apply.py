"""
clean_apply.py <ytid> <videoDbId> [apply]
Build sections from a video's native YouTube chapters with standard cleanups, then
apply via apply_sections.py. Cleanups:
  - "<Untitled Chapter N>" -> "Intro" (if it starts at 0) else "Section"
  - strip a leading "M:SS " timestamp accidentally baked into a label
  - title-case fully-UPPERCASE labels (mixed-case left alone)
  - drop promo/credit chapters (subscribe/course/patreon/"check out part"/etc),
    merging their time span into the previous kept segment
Dry-run prints the cleaned spec; pass 'apply' to write.
"""
import json, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

vid, vid_db = sys.argv[1], sys.argv[2]
apply = len(sys.argv) > 3 and sys.argv[3] == "apply"

PROMO = re.compile(r"online course|subscribe|patreon|updated monthly|anytime anywhere|"
                   r"worlds best|check out part|thanks for joining|dance with anna|"
                   r"practice anytime|click here|link in", re.I)

d = json.load(open(f"_proto/{vid}.json", encoding="utf-8"))
dur = int(d.get("duration") or 0)
chs = d.get("chapters") or []

segs = []  # (start, end, label)
for i, c in enumerate(chs):
    st = int(c["start_time"])
    et = int(chs[i + 1]["start_time"]) if i + 1 < len(chs) else dur
    lbl = c["title"].strip()
    lbl = re.sub(r"^\d{1,2}:\d{2}\s+", "", lbl)            # stray leading timestamp
    if re.match(r"^<Untitled Chapter", lbl):
        lbl = "Intro" if st == 0 else "Section"
    if re.search(r"[A-Za-z]", lbl) and lbl.upper() == lbl:  # fully uppercase -> title case
        lbl = " ".join(w if any(ch.isdigit() for ch in w) else w.capitalize() for w in lbl.split())
    segs.append([st, et, lbl])

# drop promo segments, merging their time into the previous kept one (or next if first)
kept = []
for st, et, lbl in segs:
    if PROMO.search(lbl):
        if kept:
            kept[-1][1] = et            # extend previous
        else:
            continue                    # leading promo with nothing before -> just drop its span start
    else:
        kept.append([st, et, lbl])
# if we dropped a leading promo, make the first kept seg start at 0
if kept and kept[0][0] != 0:
    kept[0][0] = 0

spec = ";".join(f"{l}@{s}-{e}" for s, e, l in kept)
print(f"{vid} -> db{vid_db}: {len(kept)} sections")
for s, e, l in kept:
    print(f"  {s:>4}-{e:>4}  {l}")
if apply:
    r = subprocess.run(["python", "apply_sections.py", vid_db, spec, "apply"],
                       capture_output=True, text=True, encoding="utf-8")
    print("APPLIED" if "APPLIED" in r.stdout else "FAIL " + r.stderr[-200:])
