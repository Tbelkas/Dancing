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
A person teaching a dance uses dance vocabulary and counts. The exact test is two word
lists and three ways to pass - see the long note above CORE, which records what the
first two attempts got wrong and why. Every threshold in it is measured against real
transcripts; none is chosen.

Verdicts, written to QualityFlags so the Intake tab shows the reasoning:
  confirmed          says the move's name, teaching cues present, dance vocabulary
  partial            teaching + dance vocabulary, names the style but not the move
  dance-but-unnamed  clearly a dance lesson that never says the move's name
  not-a-dance-video  no dance vocabulary - the title was a coincidence
  silent             no speech; a real format (mirrored walkthroughs), so not a verdict
  no-transcript      extraction failed transiently; nothing is claimed either way
  video-unavailable  removed, private or age-walled; it will never play for anyone

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

# Does the speaker talk like someone teaching a dance? Two lists, because one does not
# work - and both thresholds here are measured against real transcripts, not chosen.
#
# The first attempt was a single list of body words with a cut at 4 distinct terms.
# Over 49 catalogue videos that looked fine (median 10, minimum 2) and it correctly
# scored the Super Smash Bros "Dancing Blade" guide at 1. Run against the real intake
# queue it rejected three genuine tutorials in the first ten rows - "The Bus Stop: a
# step by step dance guide" scored 2, because the list had "leg" and "heel" but not
# "kick", "cross", "together", "tap", or the count "two three four".
#
# Widening the single list fixed those and broke the other end: the Smash guide climbed
# to 4 on "beat", "cross", "forward" and "swings", level with a real tutorial. Generic
# motion verbs are not evidence of dancing. A fighting-game commentator uses every one.
#
# So: CORE is body parts and dance-technical vocabulary a Smash guide has no reason to
# say. GENERIC is motion verbs, which corroborate but cannot carry the verdict alone.
#
#   Smash guide       CORE 0  GENERIC 4   -> rejected
#   "The Bus Stop"    CORE 2              -> kept
#   "Ball & Heel"     CORE 1  GENERIC 3   -> kept
#   "Releves"         CORE 2              -> kept
#   117 catalogue videos: CORE median 10; the rule keeps 113.
CORE = re.compile(
    r"\b(foot|feet|leg|legs|knee|knees|arm|arms|hand|hands|hip|hips|shoulder|shoulders"
    r"|chest|torso|wrist|elbow|ankle|heel|heels|toe|toes|waist|spine"
    r"|posture|balance|bounce|groove|rhythm|footwork|choreo|choreography"
    r"|freestyle|eight count|counts?|plie|plies|releve|releves|tendu|passe"
    r"|barre|turnout|pirouette|arabesque|port de bras"
    r"|shuffle|flap|stomp|stomps|ball change|toe tap"
    # Partner and swing vocabulary. Without these the whole Lindy/Ballroom half of the
    # catalogue scores zero: "How to Do the Tandem Charleston | Swing Dance" named the
    # move, the style, and taught throughout, and still scored CORE 0, because every
    # word it uses - rock step, triple step, kick, swingout - sat in GENERIC.
    r"|rock step|triple step|swingout|swing out|closed position|open position"
    r"|kick ball|grapevine|chasse|weight change|basic step|counts? of eight|on count"
    r"|five six seven eight|5 6 7 8|one two three|two three four"
    r"|and one|and two|on the one|downbeat|upbeat)\b", re.I)

# Someone counting a routine out loud. Deliberately separate from CORE: ASR writes the
# counts interleaved with words ("kick three, step down four, five, pull up six"), so
# the fixed phrases above never match even when the teacher is plainly counting.
COUNTS = re.compile(r"\b(one|two|three|four|five|six|seven|eight)\b", re.I)
MIN_DISTINCT_COUNTS = 5
GENERIC = re.compile(
    r"\b(kick|kicks|cross|crossing|together|turn|turns|spin|spins|twist|twists"
    r"|slide|slides|tap|taps|drop|drops|jump|jumps|hop|hops|bend|bends|straighten"
    r"|point|flex|lift|lifts|swing|swings|rock|rocking|step|steps|stepping"
    r"|forward|backward|sideways|weight|body|beat|beats|routine)\b", re.I)


def talks_like_dancing(text):
    """(is_dance, core_count, generic_count). See the note above CORE.

    Three ways to pass, because no single one covers the styles:
      CORE >= 2                  technical vocabulary, the normal case
      CORE >= 1 and GENERIC >= 3 one technical term with movement behind it
      counting and GENERIC >= 4  a teacher counting a routine out loud

    Measured on 202 transcribed catalogue videos: 193 pass (95.5%). The Super Smash
    Bros "Dancing Blade" guide scores CORE 0 and does not count, so it still fails.
    """
    core = len({m.group(0).lower() for m in CORE.finditer(text)})
    gen = len({m.group(0).lower() for m in GENERIC.finditer(text)})
    counting = len({m.group(0).lower()
                    for m in COUNTS.finditer(text)}) >= MIN_DISTINCT_COUNTS
    ok = core >= 2 or (core >= 1 and gen >= 3) or (counting and gen >= 4)
    return ok, core, gen

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
    # A video that will not play is worse than one that is merely wrong: the page is
    # broken for every learner who opens it, and no amount of review makes it work.
    "video-unavailable": 0.05,
}

FETCH = """
select coalesce(json_agg(row_to_json(t)), '[]'::json) from (
  select v."Id" as "vid", v."VideoId" as "ytid", v."Platform" as "platform",
         v."Title" as "title", v."ReviewState" as "state",
         v."QualityScore" as "score",
         coalesce(d."Name", '') as "dance",
         coalesce((select string_agg(s."Name", ' ')
                   from "DanceStyles" ds join "Styles" s on s."Id" = ds."StyleId"
                   where ds."DanceId" = d."Id"), '') as "styles"
  from "Videos" v left join "Dances" d on d."Id" = v."DanceId"
  where v."ReviewState" = '%s'
) t;
"""


DEAD = re.compile(r"(not available|unavailable|private video|has been removed"
                  r"|terminated|does not exist|age.?restricted|sign in to confirm)", re.I)


def is_dead(ytid):
    """Ask YouTube whether the video still plays. Returns a reason, or None if fine.

    Worth a separate probe because a failed extraction has two very different causes.
    A transient network problem is nobody's fault and the video deserves another go;
    a video that has been removed, privated or age-walled can never play for a learner
    and must not sit in the catalogue at any score. Both look identical from here -
    signals.py just doesn't write a file - so the difference has to be asked for.
    """
    p = subprocess.run(
        ["yt-dlp", "--skip-download", "--no-warnings", "--simulate",
         f"https://www.youtube.com/watch?v={ytid}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if p.returncode == 0:
        return None
    m = DEAD.search((p.stderr or "") + (p.stdout or ""))
    return m.group(0).lower() if m else None


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
        # Extraction failing has two very different meanings - see is_dead().
        try:
            reason = is_dead(row["ytid"])
        except (subprocess.TimeoutExpired, OSError):
            reason = None
        if reason:
            return "video-unavailable", {"note": f"will not play: {reason}"}
        return "no-transcript", {"note": err or "extraction failed"}

    a = sig.get("asr") or {}
    text = " ".join(s.get("text", "") for s in (a.get("segments") or []))
    dens = [d["v"] for d in (sig.get("density") or [])]
    speechy = sum(1 for v in dens if v > 0.15) / len(dens) if dens else 0.0

    if speechy < 0.10:
        return "silent", {"note": "no speech - cannot be judged from audio",
                          "core": 0, "speechy": round(speechy, 3)}

    tt = vg.toks(text)
    dance_t = vg.toks(row["dance"])
    style_t = vg.toks(row["styles"])
    says_move = bool(dance_t & tt)
    says_style = bool(style_t & tt)
    teaches = bool(vg.TEACH_CUES.search(text))
    is_dance, core, gen = talks_like_dancing(text)

    d = {"core": core, "generic": gen, "speechy": round(speechy, 3),
         "says_move": says_move, "says_style": says_style, "teaches": teaches,
         "lang": a.get("language"),
         "note": f"move={'y' if says_move else 'n'} style={'y' if says_style else 'n'} "
                 f"teaching={'y' if teaches else 'n'} core={core} gen={gen}"}

    if not is_dance:
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
    total_in_state = len(rows)
    if args.only_unscored:
        rows = [r for r in rows if r.get("score") is None]
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        print(f"nothing to do in state '{args.state}' "
              f"({total_in_state} row(s), all already verified)")
        return
    print(f"{len(rows)} of {total_in_state} video(s) in '{args.state}' to verify")

    # Written per row rather than batched at the end: a queue of a few hundred takes
    # hours of GPU, and a run that is interrupted must not throw away what it learned.
    tally = {}
    for n, r in enumerate(rows, 1):
        t0 = time.time()
        verdict, d = judge(r)
        score = VERDICT_SCORE.get(verdict, 0.35)
        tally[verdict] = tally.get(verdict, 0) + 1
        print(f"  [{n}/{len(rows)}] #{r['vid']:<5} {r['dance'][:20]:<22} "
              f"{verdict:<18} {d.get('note', '')[:40]}  ({time.time()-t0:.0f}s)",
              flush=True)
        if not args.apply:
            continue
        flags = verdict
        if d.get("core") is not None:
            flags += f",core-{d['core']}"
        note = f"verify_intake: {d.get('note', verdict)}"[:280].replace("'", "''")
        ch.psql(f'''update "Videos"
                      set "QualityScore" = {score},
                          "QualityFlags" = '{flags}',
                          "ReviewNote" = '{note}'
                    where "Id" = {int(r["vid"])};''')

    print("\nverdicts:", "  ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    if not args.apply:
        print("\ndry run - pass 'apply' to write scores and flags")
        return
    print(f"\nwrote evidence to {len(rows)} row(s). "
          "Nothing was approved - promote from the Intake tab.")


if __name__ == "__main__":
    main()
