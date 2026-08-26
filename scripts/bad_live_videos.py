"""
bad_live_videos.py [--min-tier 2] [--limit N]

List videos that are LIVE on the site and that the evidence says should not be.

    python scripts/bad_live_videos.py            the shortlist, worst first
    python scripts/bad_live_videos.py --all      include weaker evidence

READ-ONLY. It never writes to the database and never changes a ReviewState. Taking a
video off the site is a decision a person makes in the dashboard's Intake tab; this
just says where to look.

WHY THIS IS THE SHARP END
-------------------------
Everything else in the intake pipeline guards the front door: new videos land as
"pending" and are judged before anyone sees them. But the catalogue's quality problem
is not in the queue, it is already on the site. 1,153 videos were imported by a flow
that never checked whether the video taught the move, and they were all backfilled to
"approved" when the gate was added, because there was no evidence to do anything else.

So this asks the opposite question to the rest of the pipeline: not "should this get
in", but "would this get in today". A video that is live, and that the rubric plus the
transcript both refuse, is a video a learner is being shown right now.

EVIDENCE TIERS - and why the default excludes most of the catalogue
-------------------------------------------------------------------
A video only appears here if something actually looked at it. Videos graded from the
database row alone score 1.0 because nothing examined them, not because they are good,
and listing those as "fine" would be the same mistake the original seeding made in the
other direction. --min-tier 2 (the default) means: only videos whose audio was
transcribed. Anything less is a guess.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import chip_health as ch     # noqa: E402
import video_gate as vg      # noqa: E402

# Flags that mean "this may be the wrong video", as opposed to "this video is thin".
# Thin is a reason to improve a page; wrong is a reason to take it down.
WRONG = {"title-dance-mismatch", "dance-never-mentioned", "not-instructional",
         "no-speech-for-a-tutorial", "availability-needs_auth", "livestream"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-tier", type=int, default=2)
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--all", action="store_true",
                    help="include tier 0/1 rows (weaker evidence)")
    args = ap.parse_args()
    if args.all:
        args.min_tier = 0

    raw = json.loads(ch.psql(vg.FETCH).strip() or "[]")
    rows = []
    for r in raw:
        if r["state"] != "approved":
            continue
        meta = vg.load_meta(r["ytid"]) if r["platform"] == "youtube" else None
        sig = vg.load_sig(r["ytid"]) if r["platform"] == "youtube" else None
        score, verdict, flags, tier = vg.grade(r, meta, sig)
        if tier < args.min_tier:
            continue
        stored = r.get("qflags") or ""
        audio_says_no = "not-a-dance-video" in stored
        wrong = sorted(set(flags) & WRONG)
        if verdict == "admit" and not audio_says_no and not wrong:
            continue
        rows.append({**r, "score": score, "verdict": verdict, "flags": flags,
                     "tier": tier, "wrong": wrong, "audio": stored})

    # Worst first, but a video the audio refuses outright leads regardless of score.
    rows.sort(key=lambda r: (not ("not-a-dance-video" in r["audio"]),
                             not r["wrong"], r["score"]))

    n_audio = sum(1 for r in rows if "not-a-dance-video" in r["audio"])
    n_wrong = sum(1 for r in rows if r["wrong"])
    print(f"{len(rows)} live video(s) the evidence would not admit today "
          f"(tier >= {args.min_tier})")
    print(f"  {n_audio} the transcript says are not dance videos at all")
    print(f"  {n_wrong} carrying a may-be-the-wrong-video flag")
    print()
    print(f"  {'id':>5} {'score':>5} {'t':>1} {'views':>9}  {'dance':<22} why")
    for r in rows[:args.limit]:
        why = ",".join(r["wrong"]) or ",".join(r["flags"]) or r["verdict"]
        if "not-a-dance-video" in r["audio"]:
            why = "AUDIO:not-a-dance-video  " + why
        print(f"  {r['vid']:>5} {r['score']:>5.2f} {r['tier']:>1} {r['views']:>9,}  "
              f"{(r['dance'] or '')[:20]:<22} {why[:60]}")
        print(f"        https://youtu.be/{r['ytid']}  {r['title'][:64]}")

    print("\nRead-only. Nothing was changed. Review these in the dashboard's Intake "
          "tab (they show under 'live but flagged').")


if __name__ == "__main__":
    main()
