"""
find_videos.py [--limit N] [--per-dance K] [--min-views N] [apply]

Find a SECOND teaching video for dances that only have one.

    python scripts/find_videos.py --limit 20          dry run, 20 dances
    python scripts/find_videos.py --limit 20 apply    insert the survivors

980 of 1,051 dances have exactly one video, so a learner sees every move taught
exactly one way. A second instructor on the same move is the single cheapest
improvement available, and unlike the 2026-06 seeding runs there is now an intake
gate to stop the bad ones reaching the site.

WHY THIS IS NOT JUST "SEARCH AND INSERT"
----------------------------------------
The documented seeding failure was yt-dlp returning something unrelated for a
generically-named move - an electro clip for a salsa step. Searching "G Slide
latin dance tutorial" today still returns "Lil Mama - G slide", a song. So every
candidate is scored before it is offered, and inserted rows land as "pending":
the database default quarantines them behind the global query filter until
someone approves them in the dashboard's Intake tab. Nothing reaches the public
catalogue on a search engine's say-so.

Checks applied to every candidate, cheapest first:
  - already in the catalogue (same platform + video id anywhere)  -> drop
  - duration outside 45s..60min                                   -> drop
  - view count below --min-views                                  -> drop
  - title shares no meaningful word with the dance OR its style   -> drop
  - the dance's existing video is the same clip                   -> drop
Survivors are ranked by a coherence score and the best K per dance are offered.
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
import chip_health as ch  # noqa: E402
import chip_runstate as rs  # noqa: E402
import video_gate as vg  # noqa: E402

OUT = os.path.join(rs.PROTO, "found_videos.json")

MIN_DUR, MAX_DUR = 45, 3600
SEARCH_N = 6

# Words that make a title look like a music video or a performance rather than
# instruction. Not fatal on their own, but they lower the score.
NOT_TEACHING = re.compile(
    r"\b(official (video|audio)|music video|lyrics|remix|live (at|from)|concert"
    r"|full performance|episode \d+|reaction|vlog)\b", re.I)
TEACHING = re.compile(
    r"\b(tutorial|how to|learn|lesson|breakdown|step by step|basics|beginner"
    r"|technique|drill|explained)\b", re.I)


TARGETS = """
select coalesce(json_agg(row_to_json(t)), '[]'::json) from (
  select d."Id" as "danceid", d."Name" as "dance",
         coalesce((select string_agg(s."Name", ' ')
                   from "DanceStyles" ds join "Styles" s on s."Id" = ds."StyleId"
                   where ds."DanceId" = d."Id"), '') as "styles",
         (select max(coalesce(v."ViewCount",0)) from "Videos" v
           where v."DanceId" = d."Id") as "reach",
         (select string_agg(v."VideoId", ',') from "Videos" v
           where v."DanceId" = d."Id") as "existing"
  from "Dances" d
  where (select count(*) from "Videos" v where v."DanceId" = d."Id") <= 1
  order by (select max(coalesce(v."ViewCount",0)) from "Videos" v
            where v."DanceId" = d."Id") desc nulls last
) t;
"""


def catalogue_ids():
    raw = ch.psql('select coalesce(json_agg("VideoId"), \'[]\'::json) from "Videos";')
    return set(json.loads(raw.strip() or "[]"))


def search(query, n=SEARCH_N):
    p = subprocess.run(
        ["yt-dlp", f"ytsearch{n}:{query}", "--flat-playlist", "--no-warnings", "-q",
         "--print", "%(id)s\t%(duration)s\t%(view_count)s\t%(title)s"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180)
    out = []
    for line in (p.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        vid, dur, views, title = parts
        try:
            out.append({"ytid": vid, "dur": int(float(dur or 0)),
                        "views": int(float(views or 0)), "title": title})
        except ValueError:
            continue
    return out


def score_candidate(c, dance, styles):
    """Coherence score plus the reasons it is not obviously wrong."""
    d_t, s_t, t_t = vg.toks(dance), vg.toks(styles), vg.toks(c["title"])
    flags = []
    score = 0.0

    overlap_d = len(d_t & t_t)
    overlap_s = len(s_t & t_t)
    if overlap_d:
        score += 0.55 * min(1.0, overlap_d / max(1, len(d_t)))
        flags.append(f"names-the-move({overlap_d})")
    if overlap_s:
        score += 0.20
        flags.append("names-the-style")
    if TEACHING.search(c["title"]):
        score += 0.25
        flags.append("looks-instructional")
    if NOT_TEACHING.search(c["title"]):
        score -= 0.35
        flags.append("looks-like-a-performance")
    if c["views"] >= 100_000:
        score += 0.10
    elif c["views"] < 2_000:
        score -= 0.10
        flags.append("very-low-reach")
    if c["dur"] < 90:
        score -= 0.10
        flags.append("very-short")
    return round(max(0.0, min(1.0, score)), 3), flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apply", nargs="?")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--per-dance", type=int, default=1)
    ap.add_argument("--min-views", type=int, default=1000)
    ap.add_argument("--min-score", type=float, default=0.55)
    ap.add_argument("--from-file", action="store_true",
                    help="insert exactly what the last dry run found, without "
                         "searching again")
    args = ap.parse_args()

    if args.from_file:
        found = (rs._read(OUT, {}) or {}).get("candidates", [])
        if not found:
            print("nothing in " + OUT + " - run a dry pass first")
            return
        insert(found, args)
        return

    targets = json.loads(ch.psql(TARGETS).strip() or "[]")[:args.limit]
    known = catalogue_ids()
    print(f"{len(targets)} dance(s) with one video or none; "
          f"{len(known)} clips already in the catalogue")

    rs.start_run("find-videos", total=len(targets))
    found, seen_new = [], set()
    for t in targets:
        if not rs.wait_if_paused():
            break
        rs.begin(ytid=t["dance"][:24], stage="search")
        style_word = (t["styles"] or "").split(" ")[0]
        query = f"{t['dance']} {style_word} dance tutorial".strip()
        try:
            cands = search(query)
        except subprocess.TimeoutExpired:
            rs.done_one(ok=False, msg=f"{t['dance']}: search timed out")
            continue

        kept = []
        for c in cands:
            if c["ytid"] in known or c["ytid"] in seen_new:
                continue
            if not (MIN_DUR <= c["dur"] <= MAX_DUR):
                continue
            if c["views"] < args.min_views:
                continue
            sc, flags = score_candidate(c, t["dance"], t["styles"])
            if sc < args.min_score:
                continue
            kept.append({**c, "score": sc, "flags": flags,
                         "danceid": t["danceid"], "dance": t["dance"],
                         "query": query})
        kept.sort(key=lambda x: -x["score"])
        for c in kept[:args.per_dance]:
            seen_new.add(c["ytid"])
            found.append(c)
        rs.done_one(ok=True, msg=f"{t['dance']}: {len(kept)} candidate(s)")
        time.sleep(0.4)   # be polite to the search endpoint
    rs.finish()

    found.sort(key=lambda c: -c["score"])
    json.dump({"generated": rs._now(), "candidates": found},
              open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    print(f"\n{len(found)} candidate(s) survived the gate")
    print(f"  {'score':>5} {'views':>10} {'len':>6}  {'dance':<24} title")
    for c in found[:25]:
        print(f"  {c['score']:>5.2f} {c['views']:>10,} {c['dur']//60:>4}m  "
              f"{c['dance'][:22]:<24} {c['title'][:44]}")
    print(f"\nwrote {OUT}")

    if args.apply != "apply":
        print("dry run - pass 'apply' to insert them as PENDING")
        return
    insert(found, args)


def insert(found, args):
    """Insert exactly the reviewed candidates.

    Kept separate from the search so --from-file can write back precisely what a
    dry run produced. Re-searching at apply time could insert something a person
    never saw, which defeats the point of reviewing the dry run.
    """
    if not found:
        return

    for c in found:
        title = c["title"].replace("'", "''")[:300]
        ch.psql(f"""
        insert into "Videos"("Title","VideoId","Platform","VideoType","DateAdded",
                             "ViewCount","DurationSeconds","DanceId")
        values ('{title}','{c["ytid"]}','youtube','tutorial', now(),
                {c["views"]}, {c["dur"]}, {c["danceid"]});""")
    print(f"inserted {len(found)} video(s)")
    state = ch.psql('''select "ReviewState", count(*) from "Videos"
                       group by 1 order by 2 desc;''').strip()
    print("review state now:\n" + state)
    print("\nThey are QUARANTINED - invisible on the site until approved in the")
    print("dashboard's Intake tab. That is the database default doing its job.")


if __name__ == "__main__":
    main()
