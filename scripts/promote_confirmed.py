"""
promote_confirmed.py [--state pending] [--verdict confirmed] [apply]

Promote intake rows whose TRANSCRIPT verdict is "confirmed" to approved.

    python scripts/promote_confirmed.py             dry run, show what would go live
    python scripts/promote_confirmed.py apply       approve them

WHY NOT video_gate.py stamp --auto-admit
----------------------------------------
That command grades from the title/metadata rubric and writes its own score and
flags over whatever is already there, preserving only "visual:" verdicts. Running
it after verify_intake.py would replace the one piece of real evidence these rows
carry - what the person in the video actually says - with a number derived from
the title. So promotion on a transcript verdict gets its own step, and this script
never recomputes a verdict: it only reads the flags verify_intake wrote.

WHY ONLY "confirmed"
--------------------
verify_intake.py's ladder is confirmed > partial > dance-but-unnamed > unclear/
silent > not-a-dance-video. Only "confirmed" means all three of: the speaker says
the move's name, teaching cues are present, and the vocabulary is a dancer's. That
is the verdict that carries the same claim a human approval would. "partial" names
the style but not the move - which is exactly how a generic "Bachata Basic Steps"
ends up on the page for "Over-the-Top with a Lift" - so it stays for a human.

Writes the same three columns the dashboard's Intake tab writes, scoped by id.
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

import chip_health as ch  # noqa: E402

FETCH = """
select coalesce(json_agg(row_to_json(t)), '[]'::json) from (
  select v."Id" as "vid", v."Title" as "title", v."VideoId" as "ytid",
         v."QualityFlags" as "flags", v."QualityScore" as "score",
         coalesce(d."Name", '') as "dance",
         coalesce((select string_agg(s."Name", ' ')
                   from "DanceStyles" ds join "Styles" s on s."Id" = ds."StyleId"
                   where ds."DanceId" = d."Id"), '') as "styles"
  from "Videos" v left join "Dances" d on d."Id" = v."DanceId"
  where v."ReviewState" = '%s' and v."QualityFlags" like '%s%%'
) t;
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apply", nargs="?")
    ap.add_argument("--state", default="pending")
    ap.add_argument("--verdict", default="confirmed")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    rows = json.loads(ch.psql(FETCH % (args.state, args.verdict)).strip() or "[]")
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        print(f"nothing in '{args.state}' with verdict '{args.verdict}'")
        return

    by_style = {}
    for r in rows:
        by_style[(r["styles"] or "?").split(" ")[0]] = \
            by_style.get((r["styles"] or "?").split(" ")[0], 0) + 1
    print(f"{len(rows)} video(s) in '{args.state}' verified '{args.verdict}'")
    print("  " + "  ".join(f"{k}={v}" for k, v in
                           sorted(by_style.items(), key=lambda x: -x[1])))
    for r in rows[:15]:
        print(f"  #{r['vid']:<6} {r['dance'][:24]:<26} {r['title'][:46]}")

    if args.apply != "apply":
        print("\ndry run - pass 'apply' to approve them")
        return

    note = f"auto-approved: transcript verdict {args.verdict}"
    for i in range(0, len(rows), 300):
        ids = ",".join(str(r["vid"]) for r in rows[i:i + 300])
        ch.psql(f"""update "Videos" set "ReviewState" = 'approved',
                    "ReviewedAt" = now(), "ReviewNote" = '{note}'
                     where "Id" in ({ids});""")
    print(f"approved {len(rows)}")
    print(ch.psql('''select "ReviewState", count(*) from "Videos"
                     group by 1 order by 2 desc;''').strip())


if __name__ == "__main__":
    main()
