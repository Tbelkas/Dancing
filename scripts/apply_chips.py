"""
apply_chips.py [--ytid Y ...] [--limit N] [--min-score S] [apply] [--undo RUNID]

Stages 05 + 06: gate a proposal, and only then write it.

    python scripts/apply_chips.py                 dry run over everything proposed
    python scripts/apply_chips.py apply           write the ones that pass
    python scripts/apply_chips.py --undo run-...  remove exactly what a run wrote

THE GATE
--------
Deterministic checks first because they are free. A proposal that fails ANY of
them is not written and not repaired - a half-fixed chip set is worse than the
one already there, because it looks reviewed.

Scoring reuses chip_health.score_video, which is the same rubric that graded the
existing catalogue. That is deliberate: a proposal has to be judged by the same
standard as the thing it would replace, or "better" means nothing.

THE OVERWRITE RULE
------------------
Replace an existing chip set ONLY if the new confidence beats the recorded one,
or the existing Source is "generic" (the 2026-07-13 placeholder tier). NEVER
overwrite "manual" - anything a person entered by hand outranks any generated
set, whatever it scores. This is what makes re-running safe and monotonic.

UNDO
----
Every write is tagged with a run id in Videos->VideoSegments.Model. --undo
deletes exactly the rows one run created and restores nothing else, so a bad
batch is one command to reverse.

Only full videos are touched (StartTime IS NULL). A montage slice is a window
into a longer clip and the proposal's timeline does not apply to it.
"""
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import chip_health as ch  # noqa: E402
import chip_runstate as rs  # noqa: E402
import candidates as cd  # noqa: E402
import propose as pr  # noqa: E402

PROTO = rs.PROTO
MIN_SCORE = 0.55          # below this, leave whatever is there alone
BANNED = ch.BANNED
MAX_LABEL = 34


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


VIDEO_ROWS = """
select coalesce(json_agg(row_to_json(t)), '[]'::json) from (
  select v."Id" as "vid", v."VideoId" as "ytid", v."Platform" as "platform",
         v."StartTime" as "clipstart", v."EndTime" as "clipend",
         coalesce(v."DurationSeconds", 0) as "dur",
         coalesce(v."ViewCount", 0) as "views",
         v."VideoType" as "vtype",
         coalesce(d."Name", '') as "dance",
         (select count(*) from "VideoSegments" s where s."VideoId" = v."Id") as "n",
         (select max(s."Confidence") from "VideoSegments" s where s."VideoId" = v."Id")
             as "conf",
         (select string_agg(distinct coalesce(s."Source",'?'), ',')
            from "VideoSegments" s where s."VideoId" = v."Id") as "sources"
  from "Videos" v
  left join "Dances" d on d."Id" = v."DanceId"
  where v."Platform" = 'youtube' and v."StartTime" is null
) t;
"""


def hard_checks(sections, dur):
    """Reasons this proposal must not be written. Empty list means it may be."""
    bad = []
    n = len(sections)
    if n < 3:
        bad.append(f"only-{n}-sections")
    if n > 14:
        bad.append(f"{n}-sections-too-many")
    starts = [s["start"] for s in sections]
    if starts != sorted(starts):
        bad.append("not-monotonic")
    if len(set(starts)) != n:
        bad.append("duplicate-starts")
    if sections and sections[0]["start"] > 30:
        bad.append("starts-late")
    labels = [(s.get("label") or "").strip() for s in sections]
    if any(not l for l in labels):
        bad.append("empty-label")
    if len({l.lower() for l in labels}) != n:
        bad.append("duplicate-labels")
    if any(len(l) > MAX_LABEL for l in labels):
        bad.append("label-too-long")
    if any(l.lower() in BANNED for l in labels):
        bad.append("banned-label")
    for i in range(n - 1):
        if sections[i + 1]["start"] - sections[i]["start"] < 12:
            bad.append("sections-too-close")
            break
    if dur:
        last = sections[-1]["start"] if sections else 0
        if dur - last > max(120, dur * 0.35):
            bad.append("stops-early")
    return bad


def score_proposal(row, sections):
    """Grade with the SAME rubric that graded the existing catalogue."""
    fake = {
        "vid": row["vid"], "dur": row["dur"], "dance": row["dance"],
        "clipstart": row["clipstart"], "clipend": row["clipend"],
        "segs": [{"label": s["label"], "start": s["start"], "end": s.get("end"),
                  "source": None, "conf": None} for s in sections],
    }
    return ch.score_video(fake)


def gather(args):
    rows = json.loads(ch.psql(VIDEO_ROWS).strip() or "[]")
    by_yt = {}
    for r in rows:
        by_yt.setdefault(r["ytid"], []).append(r)

    out = []
    wanted = set(args.ytid or [])
    for name in sorted(os.listdir(PROTO)):
        if not (name.startswith("prop_") and name.endswith(".json")):
            continue
        ytid = name[5:-5]
        if wanted and ytid not in wanted:
            continue
        prop = rs._read(os.path.join(PROTO, name), None)
        if not prop or not prop.get("sections"):
            continue
        for row in by_yt.get(ytid, []):
            sections = prop["sections"]
            reasons = hard_checks(sections, row["dur"] or prop.get("dur"))
            score, _src, issues = score_proposal(row, sections)
            existing = row["conf"]
            srcs = set((row["sources"] or "").split(","))

            verdict, why = "write", ""
            if reasons:
                verdict, why = "blocked", ",".join(reasons)
            elif score < args.min_score:
                verdict, why = "low-score", f"{score:.2f}<{args.min_score}"
            elif "manual" in srcs:
                verdict, why = "skip", "manual chips are never overwritten"
            elif row["n"] and existing is not None and "generic" not in srcs \
                    and score <= existing:
                verdict, why = "no-gain", f"{score:.2f} <= existing {existing:.2f}"
            out.append({"row": row, "sections": sections, "score": score,
                        "issues": issues, "verdict": verdict, "why": why,
                        "agreement": prop.get("agreement")})
    return out


def do_undo(runid):
    n = ch.psql(f"""select count(*) from "VideoSegments"
                    where "Model" = '{runid}';""").strip()
    print(f"run {runid} wrote {n} segment row(s)")
    if n == "0":
        return
    ch.psql(f"""delete from "VideoSegments" where "Model" = '{runid}';""")
    print(f"deleted {n} rows. NOTE: this removes what the run added; it does not")
    print("restore chips the run replaced - use the nightly pg_dump for that.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apply", nargs="?")
    ap.add_argument("--ytid", action="append")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--min-score", type=float, default=MIN_SCORE)
    ap.add_argument("--undo")
    args = ap.parse_args()

    if args.undo:
        do_undo(args.undo)
        return

    items = gather(args)
    if args.limit:
        items = items[:args.limit]
    by_v = {}
    for it in items:
        by_v[it["verdict"]] = by_v.get(it["verdict"], 0) + 1
    print(f"{len(items)} proposal/video pair(s): "
          + "  ".join(f"{k}={v}" for k, v in sorted(by_v.items())))

    writable = [it for it in items if it["verdict"] == "write"]
    print(f"\n  {'vid':>5} {'score':>5} {'now':>5} {'n':>3}  {'dance':<22} verdict")
    for it in items[:25]:
        r = it["row"]
        cur = f"{r['conf']:.2f}" if r["conf"] is not None else "  - "
        print(f"  {r['vid']:>5} {it['score']:>5.2f} {cur:>5} {len(it['sections']):>3}  "
              f"{(r['dance'] or '')[:20]:<22} {it['verdict']}"
              + (f" ({it['why']})" if it["why"] else ""))
    if len(items) > 25:
        print(f"  ... +{len(items)-25} more")

    if args.apply != "apply":
        print(f"\ndry run - {len(writable)} would be written. pass 'apply' to write.")
        return
    if not writable:
        print("\nnothing passes the gate")
        return

    runid = "chip-run-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") \
            + "-" + uuid.uuid4().hex[:6]
    print(f"\nrun id {runid}  (undo with: python scripts/apply_chips.py --undo {runid})")

    written = 0
    for it in writable:
        vid = it["row"]["vid"]
        vals = []
        for s in it["sections"]:
            label = s["label"].replace("'", "''")[:MAX_LABEL]
            end = "null" if s.get("end") is None else int(s["end"])
            vals.append(f"('{label}',{int(s['start'])},{end},{vid},"
                        f"'transcript',{it['score']},'{runid}',now())")
        ch.psql(f"""
        delete from "VideoSegments" where "VideoId" = {vid};
        insert into "VideoSegments"("Label","StartTime","EndTime","VideoId",
                                    "Source","Confidence","Model","GeneratedAt")
        values {",".join(vals)};""")
        written += 1
        if written % 10 == 0:
            print(f"  written {written}/{len(writable)}")
    print(f"done - {written} video(s) rechipped, tagged {runid}")


if __name__ == "__main__":
    main()
