"""
chapters_spec.py <ytid>
Prints a section spec ("Label@start-end;...") built from a video's native YouTube
chapters (from cached _proto/<ytid>.json), using each chapter's start and the next
chapter's start (or duration) as the segment end. No DB writes.
"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")

vid = sys.argv[1]
d = json.load(open(f"_proto/{vid}.json", encoding="utf-8"))
dur = int(d.get("duration") or 0)
chs = d.get("chapters") or []
parts = []
for i, c in enumerate(chs):
    st = int(c["start_time"])
    et = int(chs[i + 1]["start_time"]) if i + 1 < len(chs) else dur
    label = c["title"].strip().replace(";", ",").replace("@", "at")
    parts.append(f"{label}@{st}-{et}")
print(";".join(parts))
