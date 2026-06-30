"""
thin_chips.py <ytid> <videoDbId> [apply]
Heuristic 2-4 part "thin" sections for a short single-move tutorial clip, from its
cached transcript (_proto/sec_<ytid>.txt). Splits into: Intro / Tutorial /
[Practice with music] / [Outro], using simple spoken-cue detection. Prints SKIP if
the transcript is too thin to structure. Dry-run unless 'apply'.
"""
import json, os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

vid, vid_db = sys.argv[1], sys.argv[2]
apply = len(sys.argv) > 3 and sys.argv[3] == "apply"

d = json.load(open(f"_proto/{vid}.json", encoding="utf-8"))
dur = int(d.get("duration") or 0)

# parse transcript lines "MM:SS  text"
lines = []
sec = open(f"_proto/sec_{vid}.txt", encoding="utf-8").read().splitlines() if os.path.exists(f"_proto/sec_{vid}.txt") else []
intmap = False
for l in sec:
    if l.strip() == "transcript:":
        intmap = True; continue
    if not intmap:
        continue
    m = re.match(r"(\d\d):(\d\d)\s+(.+)", l)
    if m:
        lines.append((int(m.group(1)) * 60 + int(m.group(2)), m.group(3).strip().lower()))

if dur < 90 or len(lines) < 5:
    print(f"{vid}: SKIP (thin: dur={dur} lines={len(lines)})")
    raise SystemExit(0)

INSTR = re.compile(r"\b(first|start|begin|step|we'?re going to|we are going to|let'?s|going to do|the move|today we|alright|all right|okay so|so the|to do this)\b")
MUSIC = re.compile(r"\bmusic\b")
OUTRO = re.compile(r"\b(subscribe|thanks for watching|thank you for watching|hope you|see you|comment below|next video|next time|follow me|hit that|that'?s it|that was)\b")

# intro end: first instructional cue after 4s, clamped
intro_end = None
for t, tx in lines:
    if t >= 4 and INSTR.search(tx):
        intro_end = t; break
cap = min(int(dur * 0.25), 40)
if intro_end is None or intro_end > cap:
    intro_end = max(8, min(cap, int(dur * 0.10)))

# music start: last "music" mention in the back half
music_start = None
for t, tx in lines:
    if dur * 0.5 <= t <= dur * 0.95 and MUSIC.search(tx):
        music_start = t
# outro start: first outro cue in last 30%
outro_start = None
for t, tx in lines:
    if t >= dur * 0.7 and OUTRO.search(tx):
        outro_start = t; break

pts = [(0, "Intro"), (intro_end, "Tutorial")]
if music_start and music_start > intro_end + 20:
    pts.append((music_start, "Practice with music"))
if outro_start and outro_start > pts[-1][0] + 15 and outro_start < dur - 3:
    pts.append((outro_start, "Outro"))

# build segments, require Tutorial >= 25s
segs = []
for i, (st, lbl) in enumerate(pts):
    et = pts[i + 1][0] if i + 1 < len(pts) else dur
    segs.append((lbl, st, et))
tut = next((e - s for l, s, e in segs if l == "Tutorial"), 0)
if len(segs) < 2 or tut < 25:
    print(f"{vid}: SKIP (structure too thin: {[(l,s,e) for l,s,e in segs]})")
    raise SystemExit(0)

spec = ";".join(f"{l}@{s}-{e}" for l, s, e in segs)
print(f"{vid} -> db{vid_db}: " + " | ".join(f"{l} {s}-{e}" for l, s, e in segs))
if apply:
    r = subprocess.run(["python", "apply_sections.py", vid_db, spec, "apply"],
                       capture_output=True, text=True, encoding="utf-8")
    print("  APPLIED" if "APPLIED" in r.stdout else "  FAIL " + r.stderr[-160:])
