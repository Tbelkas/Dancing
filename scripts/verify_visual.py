"""
verify_visual.py [--limit N] [--state pending] [apply]

Judge the videos that audio cannot judge, by looking at them.

    python scripts/verify_visual.py --limit 5        try it
    python scripts/verify_visual.py apply            write verdicts back

WHY
---
verify_intake.py answers "does this teach this move" from what the speaker says, and
for most of the catalogue that works. For a substantial minority there is nothing to
hear: 155 of 1,153 approved videos (13%) transcribe to fewer than twenty words, and
another slice comes back "unclear". I recorded that as a permanent ceiling - evidence
that could never arrive however long the transcription backfill ran.

That was wrong, and the other session found why while building stage 04: silent
tutorials frequently carry their instruction as ON-SCREEN TEXT. "IT IS IMPORTANT TO
PREPARE THE KNEES FOR MOVEMENT WHEN YOU DANCE" is a sentence the video is saying, in a
channel nothing here was reading. The videos were not evidence-free. We were only
listening.

So this is the same question as verify_intake, asked of the frames instead of the audio,
and ONLY for the rows where audio came back empty. It is deliberately not a general
re-judge: frames cost a download, a proxy, a contact sheet and a model call, where a
cached transcript costs nothing.

HOW IT AVOIDS INVENTING THINGS
------------------------------
It reuses visual.build_sheets from stage 04, which burns the timecode into every frame,
and it asks for a verdict plus the evidence that supports it - a caption read off the
screen, or what is visibly happening. A verdict with no evidence is discarded rather
than trusted, the same shape as stage 03 refusing any boundary that is not a real
candidate id.

COST
----
One `claude -p` call per video, on the Claude Code subscription. Quota exhaustion is
caught and stops the run cleanly, leaving everything already written in place - rerun
after the reset and it resumes.

This NEVER approves anything. It writes QualityScore/QualityFlags/ReviewNote so the
Intake tab shows what was seen. Promotion stays a person's decision.
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import chip_health as ch        # noqa: E402
import propose as pr            # noqa: E402  call_claude + QuotaExhausted
import verify_intake as vi      # noqa: E402  VERDICT_SCORE
import video_gate as vg        # noqa: E402  FETCH - the one that selects QualityFlags
import visual as vs             # noqa: E402  build_sheets (stage 04)

ROOT = ch.ROOT

# Only these audio verdicts are worth spending frames on. "confirmed" needs nothing more,
# and "video-unavailable" cannot be filmed because there is no video to fetch.
BLIND = {"silent", "unclear", "no-transcript"}

VISUAL_SCORE = {
    "teaches-this-move": 0.85,
    "dance-but-other-move": 0.45,
    "dance-performance": 0.35,
    "not-a-dance-video": 0.10,
    "cannot-tell": 0.50,
}

PROMPT = """You are looking at contact sheets of frames from one video. Every frame has
its timecode burned into it.

The video is attached to a dance move in a learning catalogue:

  move:  {dance}
  style: {styles}
  title: {title}

This video has no usable audio - it is silent, or its speech could not be transcribed.
So the frames are the only evidence. Many silent tutorials carry their instruction as
on-screen text; if you can read captions, they are your best evidence.

Answer ONLY with a JSON object:

{{"verdict": "<one of: teaches-this-move, dance-but-other-move, dance-performance,
              not-a-dance-video, cannot-tell>",
  "evidence": "<what you actually SAW that supports this - quote on-screen text
                verbatim where there is any, otherwise describe what is happening
                and at which timecode>",
  "onscreen_text": "<any instructional text you can read, or empty string>"}}

Rules:
- "teaches-this-move" requires visible instruction (demonstration, breakdown, captions)
  AND that it plausibly IS the named move.
- "dance-but-other-move" is dancing and teaching, but a different move.
- "dance-performance" is dancing with no instruction.
- "not-a-dance-video" is nobody dancing at all.
- "cannot-tell" if the frames genuinely do not settle it. Prefer this to guessing.
- The evidence field must describe something in the frames. Do not infer from the title.

Sheets:
{sheets}
"""


def judge_visually(row):
    dur = int(row.get("dur") or 0)
    if dur <= 0:
        return "cannot-tell", {"note": "no duration known, cannot sample frames"}
    sheets, err = vs.build_sheets(row["ytid"], dur)
    if not sheets:
        return "cannot-tell", {"note": f"no frames: {err or 'unknown'}"}

    prompt = PROMPT.format(
        dance=row["dance"] or "(unnamed)", styles=row["styles"] or "(none)",
        title=row["title"] or "", sheets="\n".join(sheets))
    raw = pr.call_claude(prompt)

    m = re.search(r"\{[\s\S]*\}", raw or "")
    if not m:
        return "cannot-tell", {"note": "model returned no JSON"}
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return "cannot-tell", {"note": "model returned malformed JSON"}

    verdict = (d.get("verdict") or "").strip()
    evidence = (d.get("evidence") or "").strip()
    onscreen = (d.get("onscreen_text") or "").strip()
    if verdict not in VISUAL_SCORE:
        return "cannot-tell", {"note": f"unknown verdict {verdict!r}"}
    # A verdict with nothing behind it is an opinion, not evidence. Same shape as
    # stage 03 refusing a boundary that is not a real candidate id.
    if not evidence:
        return "cannot-tell", {"note": f"{verdict} claimed with no evidence - discarded"}

    return verdict, {"note": evidence[:200], "onscreen": onscreen[:200],
                     "sheets": len(sheets)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apply", nargs="?")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--state", default="pending")
    args = ap.parse_args()

    # video_gate's FETCH rather than verify_intake's: it is the one that selects
    # QualityFlags and DurationSeconds, both of which this needs. verify_intake's
    # omits them, and reading r["qflags"] off it silently yields None for every row -
    # which presents as "nothing to do" rather than as an error.
    rows = json.loads(ch.psql(vg.FETCH).strip() or "[]")
    rows = [r for r in rows if r["state"] == args.state]
    # Only rows the audio pass already gave up on.
    todo = [r for r in rows
            if (r.get("qflags") or "").split(",")[0] in BLIND]
    if args.limit:
        todo = todo[:args.limit]
    if not todo:
        print(f"nothing in '{args.state}' is waiting on frames "
              f"(need an audio verdict of {'/'.join(sorted(BLIND))} first)")
        return
    print(f"{len(todo)} video(s) the audio could not judge")
    print(f"COST: one claude -p call each, on the subscription.\n")

    tally = {}
    for n, r in enumerate(todo, 1):
        t0 = time.monotonic()
        try:
            verdict, d = judge_visually(r)
        except pr.QuotaExhausted as e:
            print(f"\nquota exhausted: {e}")
            print("Everything already written is kept. Re-run after the reset "
                  "and it resumes from here.")
            break
        except Exception as e:  # noqa: BLE001 - one bad video must not end the run
            verdict, d = "cannot-tell", {"note": f"{type(e).__name__}: {str(e)[:120]}"}
        tally[verdict] = tally.get(verdict, 0) + 1
        print(f"  [{n}/{len(todo)}] #{r['vid']:<5} {(r['dance'] or '')[:20]:<22} "
              f"{verdict:<22} {d.get('note','')[:46]}  "
              f"({time.monotonic()-t0:.0f}s)", flush=True)

        if not args.apply:
            continue
        flags = f"visual:{verdict}"
        if d.get("onscreen"):
            flags += ",has-onscreen-text"
        note = f"verify_visual: {d.get('note','')}"[:280].replace("'", "''")
        ch.psql(f'''update "Videos"
                      set "QualityScore" = {VISUAL_SCORE[verdict]},
                          "QualityFlags" = '{flags}',
                          "ReviewNote" = '{note}'
                    where "Id" = {int(r["vid"])};''')

    print("\nverdicts:", "  ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    if not args.apply:
        print("\ndry run - pass 'apply' to write")
    else:
        print("Nothing was approved - promote from the Intake tab.")


if __name__ == "__main__":
    main()
