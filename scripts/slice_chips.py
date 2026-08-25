"""
slice_chips.py [apply] [ytid ...]
Chip montage-slice Videos rows (StartTime set) using the SOURCE video's native
chapters and transcript, clamped to each slice's [StartTime, EndTime) window.
Segment times are ABSOLUTE source-video seconds (the player seeks absolutely).

Per slice:
 1. Source chapters overlapping the window (>=15s or >=50% of the chapter)
    -> one chip per chapter, label cleaned, times clamped. Needs >=2 to count
    as "real structure"; a single overlapping chapter falls through to 2.
 2. Else transcript-cue thin split inside the window: Breakdown / Practice
    with music (last "music" cue in back half) — 2-3 chips.
 3. Else one chip spanning the window labeled with the dance name (marks the
    move on the seek bar; low value but the user wants everything chipped).

Reads _proto/chip_all_inventory.tsv (lane C rows) + _proto/<ytid>.json +
_proto/sec_<ytid>.txt. Applies via scripts/apply_sections.py with keeptype
(slices stay steps/performance — never flipped to tutorial).
Dry-run unless 'apply'. Optional ytid args restrict to those sources.
"""
import json, os, re, subprocess, sys
# pythonw.exe (used to run the dashboard detached) has no stdout, and an
# unguarded reconfigure() throws on import - which surfaced as an HTTP handler
# dying with an empty response rather than an error.
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = os.path.join(ROOT, "_proto", "chip_all_inventory.tsv")

apply = "apply" in sys.argv[1:]
only = {a for a in sys.argv[1:] if a != "apply"}

INSTR = re.compile(r"\b(first|start|begin|step|we'?re going to|we are going to|let'?s|going to do|the move|okay so|so the|like this|watch)\b", re.I)
MUSIC = re.compile(r"\bmusic\b", re.I)


def clean_label(t):
    t = re.sub(r"^\s*(<untitled[^>]*>|untitled.*)$", "Intro", t, flags=re.I)
    t = re.sub(r"^\s*(\d+[\.\):]|move\s+\d+:?)\s*", "", t, flags=re.I).strip()
    if t.isupper():
        t = t.title()
    return t or "Intro"


def load_source(ytid):
    meta = os.path.join(ROOT, "_proto", f"{ytid}.json")
    sec = os.path.join(ROOT, "_proto", f"sec_{ytid}.txt")
    dur, chapters = 0, []
    if os.path.exists(meta):
        d = json.load(open(meta, encoding="utf-8"))
        dur = int(d.get("duration") or 0)
        chapters = [(int(c["start_time"]), int(c.get("end_time") or 0), c["title"])
                    for c in (d.get("chapters") or [])]
        for i, (st, et, t) in enumerate(chapters):
            if not et:
                et = chapters[i + 1][0] if i + 1 < len(chapters) else dur
                chapters[i] = (st, et, t)
    lines = []
    if os.path.exists(sec):
        in_tr = False
        for l in open(sec, encoding="utf-8").read().splitlines():
            if l.strip() == "transcript:":
                in_tr = True; continue
            m = in_tr and re.match(r"(\d+):(\d\d)\s+(.+)", l)
            if m:
                lines.append((int(m.group(1)) * 60 + int(m.group(2)), m.group(3).strip()))
    return dur, chapters, lines


def slice_spec(S, E, dur, chapters, lines, dance):
    E = E if E else dur
    win = E - S
    # 1) chapters overlapping the window
    hits = []
    for st, et, t in chapters:
        ov = min(et, E) - max(st, S)
        if ov >= 15 or (et > st and ov / (et - st) >= 0.5):
            hits.append((max(st, S), min(et, E), clean_label(t)))
    if len(hits) >= 2:
        return [(l, s, e) for s, e, l in hits], "chapters"
    # 2) transcript-cue thin split
    wl = [(t, tx) for t, tx in lines if S <= t < E]
    if win >= 60 and len(wl) >= 4:
        first_cue = next((t for t, tx in wl if t >= S + 4 and INSTR.search(tx)), None)
        intro_end = min(first_cue if first_cue is not None else S + max(8, int(win * 0.1)), S + 40)
        music = None
        for t, tx in wl:
            if S + win * 0.5 <= t <= S + win * 0.95 and MUSIC.search(tx):
                music = t
        segs = [("Intro", S, intro_end), ("Breakdown", intro_end, music or E)]
        if music and music > intro_end + 20:
            segs.append(("Practice with music", music, E))
        if segs[1][2] - segs[1][1] >= 25:
            return segs, "cues"
    # 3) single window chip
    return [(dance, S, E)], "window"


def main():
    rows = [l.split("\t") for l in open(INV, encoding="utf-8").read().splitlines()[1:]]
    slices = [r for r in rows if r[0] == "C" and (not only or r[2] in only)]
    by_src = {}
    for r in slices:
        by_src.setdefault(r[2], []).append(r)

    stats = {"chapters": 0, "cues": 0, "window": 0}
    fails = []
    for ytid, group in sorted(by_src.items()):
        dur, chapters, lines = load_source(ytid)
        print(f"\n== {ytid} (dur {dur}s, {len(chapters)} chapters, {len(lines)} caplines) — {len(group)} slices ==")
        for lane, vid_db, _, _, vtype, st, et, *_rest in [r[:7] + [r[7:]] for r in group]:
            dance = r_dance = group[[g[1] for g in group].index(vid_db)][11]
            S = int(st); E = int(et) if et else 0
            segs, how = slice_spec(S, E, dur, chapters, lines, r_dance)
            stats[how] += 1
            spec = ";".join(f"{l}@{s}-{e}" for l, s, e in segs)
            print(f"  db{vid_db} [{S}-{E or dur}] ({how}): " + " | ".join(f"{l} {s}-{e}" for l, s, e in segs))
            if apply:
                p = subprocess.run(["python", os.path.join(ROOT, "scripts", "apply_sections.py"),
                                    vid_db, spec, "apply", "keeptype"],
                                   capture_output=True, text=True, encoding="utf-8")
                if "APPLIED" not in (p.stdout or ""):
                    fails.append((vid_db, (p.stderr or p.stdout or "")[-120:]))
                    print(f"    FAIL {fails[-1][1]}")
    print(f"\nsummary: {stats}" + ("" if apply else "  (dry-run)"))
    if fails:
        print(f"FAILED: {len(fails)} -> {[f[0] for f in fails]}")


if __name__ == "__main__":
    main()
