"""
visual.py [ytid ...] [--silent] [--limit N] [--force] [--sheets-only]

Stage 04: read the frames when there is nothing to hear.

    python scripts/visual.py --silent --limit 5     the silent backlog
    python scripts/visual.py TwGMF58xriI            one video

Roughly one video in seven has no usable audio - 30 of 457 cached transcripts
contain zero words, and 155 of 691 transcribed videos say nothing scoreable.
No ASR model fixes that; silence is silence. For those, the only evidence left
is what is on screen, which makes this the sole route to chips for the silent
chip backlog AND to intake evidence for ~150 already-approved videos.

HOW IT WORKS
------------
1. Pull a 240p proxy (cheap, deleted afterwards - these are not our videos).
2. Sample frames on a fixed grid, each with its timecode burned in by ffmpeg's
   drawtext, and tile them into contact sheets.
3. Hand the sheets to `claude -p`, which reads them with the Read tool and
   returns sections.

The model chooses from the SAMPLED TIMECODES, exactly as stage 03 chooses from
candidate ids: a timecode it did not see on a frame is rejected on parse. Without
that it would invent plausible-looking times for a video it can only see in
stills, and there would be no transcript to catch it.

Writes _proto/prop_<ytid>.json in the same shape stage 03 produces, so
apply_chips.py gates and applies it with no special casing. Sheets are kept in
_proto/frames/ for inspection - they are derived stills, not the source video.

COST: one `claude -p` call per video (a few sheets per call). Frames and the
proxy are local ffmpeg work and free.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
import chip_runstate as rs  # noqa: E402
import chip_health as ch  # noqa: E402
import candidates as cd  # noqa: E402
import propose as pr  # noqa: E402
import signals as sg  # noqa: E402

PROTO = rs.PROTO
FRAMES = os.path.join(PROTO, "frames")

COLS, ROWS = 5, 4              # 20 frames per contact sheet
MAX_FRAMES = 60                # 3 sheets is plenty of context for one call
TILE_W = 320                   # per-frame width in the sheet
FONT = "C\\:/Windows/Fonts/consola.ttf"


def mmss(t):
    t = int(t or 0)
    return f"{t // 60}:{t % 60:02d}"


def sample_times(dur, n, start=None, end=None):
    """Evenly spaced, skipping the very start and end - a title card and an
    end screen tell you nothing about the lesson.

    With start/end, sample only that window and do not trim it: a montage slice is
    already the interesting part, and shaving 1% off each end of a four-second window
    throws away most of what there is to see.
    """
    if start is not None:
        lo, hi = float(start), float(end if end else dur)
        if hi <= lo:
            return [int(lo)]
        step = (hi - lo) / max(1, n - 1)
        return [int(lo + i * step) for i in range(n)]
    lo, hi = max(2, dur * 0.01), dur * 0.98
    if hi <= lo:
        return [0]
    step = (hi - lo) / max(1, n - 1)
    return [int(lo + i * step) for i in range(n)]


def build_sheets(ytid, dur, force=False, start=None, end=None):
    """Contact sheets with the timecode burned into every frame.

    The burned-in timecode is the whole trick: the model reads the time off the
    picture, so its answer is anchored to a frame it actually saw.

    start/end restrict sampling to one window, for a row that is a slice of a montage
    rather than a whole video. Without it a four-second slice of a 203-second video was
    judged on twenty frames spread across the whole three minutes, almost none of which
    fell inside the window at all - and because the cache is keyed on the video, every
    slice of the same montage received identical sheets and identical evidence. Callers
    that pass neither get exactly the previous behaviour.
    """
    os.makedirs(FRAMES, exist_ok=True)
    # The window is part of the cache identity. Sharing one set of sheets between the
    # whole video and each of its slices is what made the slices wrong.
    key = ytid if start is None else f"{ytid}@{int(start)}-{int(end or dur)}"
    existing = sorted(f for f in os.listdir(FRAMES)
                      if f.startswith(f"{key}_sheet") and f.endswith(".png"))
    if existing and not force:
        return [os.path.join(FRAMES, f) for f in existing], None

    proxy = sg.fetch_video_proxy(ytid)
    if not proxy:
        return [], "no video stream"

    try:
        span = (float(end or dur) - float(start)) if start is not None else float(dur)
        n = min(MAX_FRAMES, max(COLS * ROWS, int(span // 12) or COLS * ROWS))
        n -= n % (COLS * ROWS) or 0
        n = max(COLS * ROWS, n)
        times = sample_times(dur, n, start, end)

        # One PNG per sampled second, timecode drawn on it.
        stills = []
        for i, t in enumerate(times):
            out = os.path.join(FRAMES, f"{key}_f{i:03d}.png")
            label = mmss(t).replace(":", "\\:")
            vf = (f"scale={TILE_W}:-2,"
                  f"drawtext=fontfile='{FONT}':text='{label}':x=6:y=6:"
                  f"fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.65:boxborderw=5")
            r = sg.run(["ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error",
                        "-ss", str(t), "-i", proxy, "-frames:v", "1",
                        "-vf", vf, "-y", out], timeout=120)
            if os.path.exists(out):
                stills.append(out)
        if not stills:
            return [], "no frames extracted"

        # Tile them, ROWS*COLS to a sheet.
        sheets = []
        per = COLS * ROWS
        for s in range(0, len(stills), per):
            chunk = stills[s:s + per]
            listfile = os.path.join(FRAMES, f"{key}_list{s}.txt")
            with open(listfile, "w", encoding="utf-8") as f:
                for p in chunk:
                    f.write("file '" + os.path.basename(p) + "'\n")
            sheet = os.path.join(FRAMES, f"{key}_sheet{s // per:02d}.png")
            r = sg.run(["ffmpeg", "-hide_banner", "-loglevel", "error",
                        "-f", "concat", "-safe", "0", "-i", listfile,
                        "-vf", f"tile={COLS}x{ROWS}", "-frames:v", "1",
                        "-y", sheet], timeout=300)
            os.unlink(listfile)
            if os.path.exists(sheet):
                sheets.append(sheet)
        for p in stills:
            try:
                os.unlink(p)
            except OSError:
                pass
        return sheets, None
    finally:
        try:
            os.remove(proxy)
        except OSError:
            pass


def build_prompt(ytid, dance, dur, sheets, times):
    grid = ", ".join(mmss(t) for t in times)
    files = "\n".join("  " + os.path.abspath(p).replace("\\", "/") for p in sheets)
    return f"""A dance tutorial with no usable audio - nothing was said, or nothing that transcribes. The only evidence is what is on screen.

VIDEO
  dance: {dance or "unknown"}
  length: {mmss(dur)}

CONTACT SHEETS - read every one of these image files with the Read tool:
{files}

Each sheet is a {COLS}x{ROWS} grid of frames in time order, left to right, top to
bottom. Every frame has its timecode burned into the top-left corner in yellow.

TASK
Work out how the lesson is structured and name its sections.

RULES
- A section starts where WHAT IS BEING TAUGHT changes: a new move, a new body
  part, a drill, a run-through, a change of camera or setup that marks a new
  part of the lesson.
- Use ONLY timecodes you can actually read on a frame. These are the sampled
  times: {grid}
- Do not invent a time between samples. If a change happens between two frames,
  use the first frame where you can see it has happened.
- 3 to 10 sections. Fewer, meaningful ones beat many guesses.
- Label what a dancer would look for: "Arm wave, elbow lead", "Practice with
  music", "Full run-through". 2-5 words, under 34 characters, all distinct.
- Never use "Tutorial", "Part 1", "Section 2", or the dance name alone.
- You are reading stills. If you genuinely cannot tell what is being taught,
  describe what is visibly happening rather than guessing a move name.

OUTPUT
A single JSON array, nothing else - no prose, no code fence:
[{{"start": 0, "label": "Intro", "evidence": "what you see in that frame", "confidence": 0.7}}]
"""


def parse(raw, times):
    """Keep only sections anchored to a timecode the model was actually shown."""
    m = re.search(r"\[[\s\S]*\]", raw.strip())
    if not m:
        raise ValueError("no JSON array in model output")
    allowed = set(times)
    out, seen = [], set()
    for row in json.loads(m.group(0)):
        if not isinstance(row, dict):
            continue
        try:
            t = int(row.get("start"))
        except (TypeError, ValueError):
            continue
        # Snap to the nearest sampled frame; reject anything not near one.
        near = min(allowed, key=lambda x: abs(x - t)) if allowed else None
        if near is None or abs(near - t) > 3 or near in seen:
            continue
        label = (row.get("label") or "").strip()[:60]
        if not label:
            continue
        seen.add(near)
        out.append({"start": near, "label": label,
                    "evidence": (row.get("evidence") or "")[:200],
                    "confidence": row.get("confidence")})
    out.sort(key=lambda s: s["start"])
    for i, s in enumerate(out):
        s["end"] = out[i + 1]["start"] if i + 1 < len(out) else None
    return out


def appliable_ytids():
    """Clips that have a catalogue row stage 06 could actually write chips to.

    apply_chips only writes rows whose StartTime IS NULL, so a clip whose every
    catalogue row is a montage slice can never receive its proposal, and a clip
    with no row at all has nowhere to put one. Both used to be selected anyway -
    13 of 71 silent targets, 18% of a stage that costs one `claude -p` call per
    video. The filter is here rather than in process() because the waste is in
    the selection, not the run.
    """
    raw = ch.psql('''select coalesce(json_agg(distinct "VideoId"), '[]'::json)
                     from "Videos"
                     where "Platform" = 'youtube' and "StartTime" is null;''')
    return set(json.loads(raw.strip() or "[]"))


def silent_targets(limit):
    """Cached videos with a transcript that says essentially nothing."""
    try:
        appliable = appliable_ytids()
    except Exception as e:                      # no DB - do not silently drop
        print(f"warning: could not read the catalogue ({e}); not filtering")
        appliable = None
    out, skipped = [], 0
    for name in sorted(os.listdir(PROTO)):
        if not (name.startswith("sig_") and name.endswith(".json")):
            continue
        ytid = name[4:-5]
        d = rs._read(os.path.join(PROTO, name), None)
        if not d:
            continue
        segs = (d.get("asr") or {}).get("segments") or []
        words = sum(len(s.get("text", "").split()) for s in segs)
        dur = d.get("dur") or 0
        if not (words < 25 and dur >= 120):
            continue
        if appliable is not None and ytid not in appliable:
            skipped += 1
            continue
        out.append((ytid, dur))
    if skipped:
        print(f"skipped {skipped} silent clip(s) with no appliable catalogue row")
    out.sort(key=lambda x: -x[1])
    return [y for y, _ in out[:limit]]


def process(ytid, names, force=False, sheets_only=False):
    sig = rs._read(cd.sig_path(ytid), None)
    if not sig:
        return "no-signals", None
    dur = sig.get("dur") or 0
    if dur < 60:
        return "too-short", None

    rs.stage("frames")
    sheets, err = build_sheets(ytid, dur, force=force)
    if err or not sheets:
        return f"no-sheets:{err or 'none'}", None
    n = len(sheets) * COLS * ROWS
    times = sample_times(dur, n)
    if sheets_only:
        return "sheets-only", {"sheets": sheets}

    rs.stage("reading frames")
    raw = pr.call_claude(build_prompt(ytid, names.get(ytid), dur, sheets, times))
    sections = parse(raw, times)
    if len(sections) < 3:
        return f"too-few-sections:{len(sections)}", None

    doc = {"ytid": ytid, "dur": dur, "source": "visual",
           "sheets": [os.path.basename(s) for s in sheets],
           "sections": sections}
    json.dump(doc, open(pr.prop_path(ytid), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return "ok", doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ytids", nargs="*")
    ap.add_argument("--silent", action="store_true")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sheets-only", action="store_true",
                    help="build the contact sheets and stop - no model call")
    args = ap.parse_args()

    ids = list(args.ytids)
    if args.silent:
        ids += silent_targets(args.limit)
    ids = list(dict.fromkeys(ids))[:args.limit] if args.silent else list(dict.fromkeys(ids))
    if not ids:
        ap.error("nothing to do: pass ytids or --silent")

    names = pr.dance_names()
    print(f"{len(ids)} video(s)"
          + ("  (sheets only, no model calls)" if args.sheets_only else
             f" = {len(ids)} claude -p call(s)"))
    rs.start_run("visual", total=len(ids))
    counts = {}
    for ytid in ids:
        if not rs.wait_if_paused():
            break
        rs.begin(ytid=ytid, stage="start")
        t0 = time.time()
        try:
            status, doc = process(ytid, names, args.force, args.sheets_only)
        except pr.QuotaExhausted as e:
            rs.done_one(ok=False, msg=f"QUOTA EXHAUSTED: {e}")
            print(f"  quota exhausted: {e}")
            break
        except Exception as e:  # noqa: BLE001
            status, doc = f"error:{type(e).__name__}", None
            rs.log(f"{ytid}: {type(e).__name__}: {str(e)[:150]}")
        counts[status] = counts.get(status, 0) + 1
        extra = f"  {len(doc['sections'])} sections" if doc and doc.get("sections") else ""
        rs.done_one(ok=status in ("ok", "sheets-only"), msg=f"{ytid} {status}{extra}")
        print(f"  {ytid:<14} {status:<22} {time.time()-t0:>5.0f}s{extra}")
    rs.finish()
    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"sheets kept in {FRAMES} for inspection")


if __name__ == "__main__":
    main()
