"""
verify_intake.py [--limit N] [--state pending] [apply]

Attach transcript evidence to videos waiting in the intake queue.

    python scripts/verify_intake.py                 dry run over everything pending
    python scripts/verify_intake.py --limit 10      a taste
    python scripts/verify_intake.py apply           write scores/flags back

WHY THIS IS SEPARATE FROM DISCOVERY
-----------------------------------
Whatever finds a candidate - find_videos.py, a hand-written seed script, an admin
pasting a URL - the question at the end is the same: does the person in this video
actually teach this move? Answering it inside each discovery script means writing it
more than once and getting a different answer each time. So it lives here, behind the
queue rather than inside any one producer, and runs over whatever is holding.

WHY TITLES ARE NOT ENOUGH
-------------------------
Title-level scoring is cheap and it is genuinely useful, but it cannot see the failure
that matters. Searching the Breakdance move "Blade" returns a Super Smash Bros guide to
Marth's "Dancing Blade". It names the move. It is instructional. It is well-viewed. It
scores 0.90 on every title signal there is, and it is not a dance video. The only
evidence that settles it is what the speaker says.

THE RULE, AND WHERE IT CAME FROM
--------------------------------
A person teaching a dance names body parts and counts - hands, weight, heel, "one two
three". Measured across 49 transcribed catalogue videos the median is 10 distinct such
terms and the minimum is 2. The Smash guide scores 1. A real BLACKPINK tutorial scores
23. Four separates them with room on both sides, so four is the bar - a measured
threshold, not a guessed one.

Verdicts, written to QualityFlags so the Intake tab shows the reasoning:
  confirmed          says the move's name, teaching cues present, dance vocabulary
  partial            teaching + dance vocabulary, names the style but not the move
  dance-but-unnamed  clearly a dance lesson that never says the move's name
  not-a-dance-video  no dance vocabulary - the title was a coincidence
  silent             no speech; a real format (mirrored walkthroughs), so not a verdict
  no-transcript      extraction failed; nothing is claimed either way

This NEVER approves anything. It writes QualityScore, QualityFlags and ReviewNote so a
person reviewing the queue sees what the evidence was. Promotion stays a human decision
in the dashboard's Intake tab.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import chip_health as ch     # noqa: E402
import video_gate as vg      # noqa: E402

ROOT = ch.ROOT

BODY = re.compile(r"\b(foot|feet|leg|legs|knee|knees|arm|arms|hand|hands|hip|hips"
                  r"|shoulder|shoulders|chest|torso|wrist|elbow|ankle|heel|heels"
                  r"|toe|toes|head|body|weight|posture|bounce|groove|rhythm"
                  r"|beat|beats|count|counts|eight|choreo|choreography|footwork"
                  r"|step|steps|routine|freestyle|five six seven eight|5 6 7 8"
                  r"|one two three)\b", re.I)
MIN_BODY_TERMS = 4

# How much each verdict is worth as a score. "silent" and "no-transcript" deliberately
# sit at the review boundary rather than low: absence of evidence is not evidence of a
# bad video, and scoring them as bad would quietly reject every wordless tutorial.
VERDICT_SCORE = {
    "confirmed": 0.90,
    "partial": 0.70,
    "dance-but-unnamed": 0.50,
    "silent": 0.50,
    "no-transcript": 0.50,
    "not-a-dance-video": 0.10,
}

FETCH = """
select coalesce(json_agg(row_to_json(t)), '[]'::json) from (
  select v."Id" as "vid", v."VideoId" as "ytid", v."Platform" as "platform",
         v."Title" as "title", v."ReviewState" as "state",
         coalesce(d."Name", '') as "dance",
         coalesce((select string_agg(s."Name", ' ')
                   from "DanceStyles" ds join "Styles" s on s."Id" = ds."StyleId"
                   where ds."DanceId" = d."Id"), '') as "styles"
  from "Videos" v left join "Dances" d on d."Id" = v."DanceId"
  where v."ReviewState" = '%s'
) t;
"""


def transcript_for(ytid):
    """Cached signals if we have them, otherwise extract once. Returns (sig, err)."""
    sig = vg.load_sig(ytid)
    if sig is not None:
        return sig, None
    p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "signals.py"),
                        "--", ytid],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=ROOT)
    sig = vg.load_sig(ytid)
    return sig, None if sig else (p.stderr or "extraction failed")[-160:]


def judge(row):
    """Return (verdict, detail-dict)."""
    if row["platform"] != "youtube":
        return "no-transcript", {"note": f"{row['platform']} - no extractor"}

    sig, err = transcript_for(row["ytid"])
    if sig is None:
        return "no-transcript", {"note": err or "extraction failed"}

    a = sig.get("asr") or {}
    text = " ".join(s.get("text", "") for s in (a.get("segments") or []))
    dens = [d["v"] for d in (sig.get("density") or [])]
    speechy = sum(1 for v in dens if v > 0.15) / len(dens) if dens else 0.0

    if speechy < 0.10:
        return "silent", {"note": "no speech - cannot be judged from audio",
                          "body": 0, "speechy": round(speechy, 3)}

    tt = vg.toks(text)
    dance_t = vg.toks(row["dance"])
    style_t = vg.toks(row["styles"])
    says_move = bool(dance_t & tt)
    says_style = bool(style_t & tt)
    teaches = bool(vg.TEACH_CUES.search(text))
    body = {m.group(0).lower() for m in BODY.finditer(text)}

    d = {"body": len(body), "speechy": round(speechy, 3),
         "says_move": says_move, "says_style": says_style, "teaches": teaches,
         "lang": a.get("language"),
         "note": f"move={'y' if says_move else 'n'} style={'y' if says_style else 'n'} "
                 f"teaching={'y' if teaches else 'n'} body={len(body)}"}

    if len(body) < MIN_BODY_TERMS:
        return "not-a-dance-video", d
    if says_move and teaches:
        return "confirmed", d
    if teaches and (says_style or says_move):
        return "partial", d
    if teaches:
        return "dance-but-unnamed", d
    return "unconfirmed", d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apply", nargs="?")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--state", default="pending")
    ap.add_argument("--only-unscored", action="store_true",
                    help="skip rows that already carry a verdict")
    args = ap.parse_args()

    rows = json.loads(ch.psql(FETCH % args.state).strip() or "[]")
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        print(f"nothing in state '{args.state}'")
        return
    print(f"{len(rows)} video(s) in '{args.state}'")

    results, tally = [], {}
    for n, r in enumerate(rows, 1):
        t0 = time.time()
        verdict, d = judge(r)
        score = VERDICT_SCORE.get(verdict, 0.35)
        results.append((r, verdict, score, d))
        tally[verdict] = tally.get(verdict, 0) + 1
        print(f"  [{n}/{len(rows)}] #{r['vid']:<5} {r['dance'][:20]:<22} "
              f"{verdict:<18} {d.get('note', '')[:40]}  ({time.time()-t0:.0f}s)",
              flush=True)

    print("\nverdicts:", "  ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    if not args.apply:
        print("\ndry run - pass 'apply' to write scores and flags")
        return

    for r, verdict, score, d in results:
        flags = verdict
        if d.get("body") is not None:
            flags += f",body-{d['body']}"
        note = f"verify_intake: {d.get('note', verdict)}"[:280].replace("'", "''")
        ch.psql(f'''update "Videos"
                      set "QualityScore" = {score},
                          "QualityFlags" = '{flags}',
                          "ReviewNote" = '{note}'
                    where "Id" = {int(r["vid"])};''')
    print(f"\nwrote evidence to {len(results)} row(s). "
          "Nothing was approved - promote from the Intake tab.")


if __name__ == "__main__":
    main()
