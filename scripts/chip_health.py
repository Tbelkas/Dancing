"""
chip_health.py [apply] [--json]

Score every video's chip set against the deterministic rubric and (with 'apply')
backfill VideoSegments.Source / .Confidence for rows that have no provenance yet.

This is stage 1 + 3 of the Chip Refinery flow: it turns "which chips are bad?"
from a guess into a stored number, and it is the same rubric the pipeline's gate
will run before it is ever allowed to write. Read-only unless 'apply' is passed.

Only fills rows where "Source" IS NULL, so it is safe to re-run and it never
touches anything the pipeline or the admin form has already stamped.

Deliberately does NOT set GeneratedAt or Model on backfill: we don't know when
these chips were made or what made them, and inventing a timestamp would poison
the one signal the queue ranks on.

Writes _proto/chip_health.json for the dashboard (scripts/chip_ui.py).
"""
import json
import math
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPSETTINGS = os.path.join(ROOT, "DancePlatform.API", "appsettings.Development.json")
OUT = os.path.join(ROOT, "_proto", "chip_health.json")

SCORER_VERSION = "shape-v1"

# Labels that carry no navigational information. The whole point of the refinery
# is to replace these, so a set made of them cannot score above its cap.
BANNED = {"tutorial", "untitled", "section", "video", "part", "chapter"}
PART_RE = re.compile(r"^(part|section|chapter)\s*\d+$", re.I)


# ---------------------------------------------------------------- db plumbing

def prod_conn():
    """Read the prod connection string from appsettings (gitignored, rotates)."""
    cfg = json.load(open(APPSETTINGS, encoding="utf-8-sig"))
    for v in cfg.get("ConnectionStrings", {}).values():
        if "192.168.0.197" in v:
            return dict(p.split("=", 1) for p in v.split(";") if "=" in p)
    raise SystemExit(f"No prod (192.168.0.197) connection string in {APPSETTINGS}")


def psql(sql, conn=None):
    """Run SQL via psql stdin with PGCLIENTENCODING=UTF8 (keeps dashes/accents intact)."""
    c = conn or prod_conn()
    env = dict(os.environ)
    env["PGPASSWORD"] = c.get("Password", "")
    env["PGCLIENTENCODING"] = "UTF8"
    p = subprocess.run(
        ["psql", "-h", c["Host"], "-U", c["Username"], "-d", c["Database"], "-At", "-v", "ON_ERROR_STOP=1"],
        input=sql, capture_output=True, text=True, env=env, encoding="utf-8",
    )
    if p.returncode:
        raise SystemExit(f"psql failed:\n{(p.stderr or '')[-800:]}")
    return p.stdout


FETCH = """
select coalesce(json_agg(row_to_json(t)), '[]'::json) from (
  select v."Id" as "vid", v."VideoId" as "ytid", v."Platform" as "platform",
         v."VideoType" as "vtype", v."Title" as "title",
         v."StartTime" as "clipstart", v."EndTime" as "clipend",
         coalesce(v."DurationSeconds", 0) as "dur",
         coalesce(v."ViewCount", 0) as "views",
         coalesce(d."Name", '') as "dance",
         coalesce((
           select json_agg(json_build_object(
                    'id', s."Id", 'label', s."Label",
                    'start', s."StartTime", 'end', s."EndTime",
                    'source', s."Source", 'conf', s."Confidence")
                  order by s."StartTime", s."Id")
           from "VideoSegments" s where s."VideoId" = v."Id"), '[]'::json) as "segs"
  from "Videos" v
  left join "Dances" d on d."Id" = v."DanceId"
) t;
"""


# ------------------------------------------------------------------- scoring

def score_video(v):
    """Return (score 0..1, source, [issue codes]) for one video's chip set.

    Deductions come off a perfect 1.0; the shape rules then cap the result,
    because a set of placeholder labels is bad no matter how tidy its timings.
    """
    segs = v["segs"]
    n = len(segs)
    dur = v["dur"] or 0
    is_slice = v["clipstart"] is not None
    issues = []

    if n == 0:
        return 0.0, "none", ["no-chips"]

    labels = [(s["label"] or "").strip() for s in segs]
    norm = [l.lower() for l in labels]
    dance = (v["dance"] or "").strip().lower()

    # --- window covered by the clip, for coverage checks --------------------
    win_start = v["clipstart"] or 0
    win_end = v["clipend"] or (dur if dur else None)
    win_len = (win_end - win_start) if win_end else dur

    # --- shape rules: identify the known generated tiers --------------------
    cap = 1.0
    source = "legacy"

    if n == 3 and norm == ["intro", "tutorial", "outro"]:
        cap, source = 0.20, "generic"
        issues.append("generic-triple")
    elif n == 1 and dance and norm[0] == dance and not is_slice and dur >= 180:
        cap, source = 0.25, "generic"
        issues.append("single-dance-name")
    elif sum(1 for l in norm if PART_RE.match(l)) >= max(2, n / 2):
        cap, source = 0.35, "generic"
        issues.append("part-labels")
    elif is_slice:
        # A montage window is already a segment; one chip is correct by
        # construction. It is unverified, not wrong, so it sits mid-scale.
        source = "slice"
        if n == 1:
            cap = 0.60

    base = 1.0

    # --- deductions ---------------------------------------------------------
    if not is_slice:
        if dur >= 600 and n < 5:
            base -= 0.30
            issues.append("thin-for-length")
        elif dur >= 300 and n < 3:
            base -= 0.30
            issues.append("thin-for-length")
        elif dur >= 180 and n < 2:
            base -= 0.25
            issues.append("thin-for-length")

    if any(l.lower() in BANNED for l in labels):
        base -= 0.20
        issues.append("banned-label")

    if len({l.lower() for l in labels}) != n:
        base -= 0.15
        issues.append("duplicate-labels")

    if any(len(l) > 34 for l in labels):
        base -= 0.05
        issues.append("long-label")

    if not labels or any(not l for l in labels):
        base -= 0.20
        issues.append("empty-label")

    if n > 14:
        base -= 0.05
        issues.append("too-many")

    starts = [s["start"] for s in segs]
    if starts != sorted(starts):
        base -= 0.25
        issues.append("not-monotonic")

    if segs[0]["start"] - win_start > 15:
        base -= 0.05
        issues.append("late-start")

    # Effective end of each chip: its own end, else the next chip's start,
    # else the end of the clip window.
    gaps = 0
    tiny = False
    for i, s in enumerate(segs):
        nxt = segs[i + 1]["start"] if i + 1 < n else win_end
        end = s["end"] if s["end"] is not None else nxt
        if end is None:
            continue
        if end - s["start"] < 12:
            tiny = True
        if nxt is not None and nxt - end > 45:
            gaps += 1
    if tiny:
        base -= 0.05
        issues.append("tiny-section")
    if gaps:
        base -= min(0.30, 0.10 * gaps)
        issues.append("coverage-gap")

    if win_end and win_len and (win_end - (segs[-1]["end"] or segs[-1]["start"])) > 90:
        base -= 0.10
        issues.append("short-tail")

    if dur == 0:
        base -= 0.05
        issues.append("no-duration")

    return round(max(0.0, min(cap, base)), 3), source, issues


def priority(views, score):
    """Rank by reach x deficit. Log-scaled so one 42M-view outlier doesn't
    flatten everything below it into a rounding error."""
    return round(math.log1p(views) / math.log1p(50_000_000) * (1.0 - score), 4)


# ---------------------------------------------------------------------- main

def main():
    argv = sys.argv[1:]
    apply = "apply" in argv

    videos = json.loads(psql(FETCH).strip() or "[]")
    rows = []
    for v in videos:
        sc, src, issues = score_video(v)
        already = {s["source"] for s in v["segs"] if s["source"]}
        rows.append({
            "vid": v["vid"], "ytid": v["ytid"], "platform": v["platform"],
            "vtype": v["vtype"], "title": v["title"], "dance": v["dance"],
            "dur": v["dur"], "views": v["views"],
            "slice": v["clipstart"] is not None,
            "n": len(v["segs"]), "score": sc, "source": src,
            "issues": issues, "priority": priority(v["views"], sc),
            "stamped": sorted(already),
        })

    rows.sort(key=lambda r: -r["priority"])

    # -------------------------------------------------------------- summary
    def bucket(r):
        if r["n"] == 0:
            return "none"
        if r["score"] < 0.35:
            return "poor"
        if r["score"] < 0.65:
            return "weak"
        return "ok"

    summary = {"none": 0, "poor": 0, "weak": 0, "ok": 0}
    by_source = {}
    for r in rows:
        summary[bucket(r)] += 1
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1

    print(f"videos: {len(rows)}   segments: {sum(r['n'] for r in rows)}")
    print("health:  " + "   ".join(f"{k}={v}" for k, v in summary.items()))
    print("source:  " + "   ".join(f"{k}={v}" for k, v in sorted(by_source.items())))
    print("\ntop 15 by priority (reach x deficit):")
    print(f"  {'vid':>5}  {'score':>5}  {'n':>3}  {'dur':>5}  {'views':>10}  {'source':<9} issues")
    for r in rows[:15]:
        print(f"  {r['vid']:>5}  {r['score']:>5.2f}  {r['n']:>3}  {r['dur']:>5}  "
              f"{r['views']:>10,}  {r['source']:<9} {','.join(r['issues'])}")

    os.makedirs(os.path.join(ROOT, "_proto"), exist_ok=True)
    json.dump({"scorer": SCORER_VERSION, "summary": summary,
               "by_source": by_source, "videos": rows},
              open(OUT, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {OUT}")

    # ------------------------------------------------------------- backfill
    todo = [r for r in rows if r["n"] > 0 and not r["stamped"]]
    print(f"\nunstamped chip sets: {len(todo)}"
          f"  ({sum(r['n'] for r in todo)} segment rows)")
    if not apply:
        print("dry run — pass 'apply' to write Source/Confidence to prod")
        return
    if not todo:
        print("nothing to backfill")
        return

    written = 0
    for i in range(0, len(todo), 200):
        chunk = todo[i:i + 200]
        values = ",".join(
            f"({r['vid']},'{r['source']}',{r['score']})" for r in chunk
        )
        sql = f"""
        update "VideoSegments" s
           set "Source" = v.src, "Confidence" = v.conf
          from (values {values}) as v(vid, src, conf)
         where s."VideoId" = v.vid and s."Source" is null;
        """
        psql(sql)
        written += sum(r["n"] for r in chunk)
        print(f"  backfilled {written} segment rows...")

    left = psql('select count(*) from "VideoSegments" where "Source" is null;').strip()
    print(f"done — segments still without provenance: {left}")


if __name__ == "__main__":
    main()
