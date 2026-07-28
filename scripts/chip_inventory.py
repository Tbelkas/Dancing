"""
chip_inventory.py
Inventory every video with zero VideoSegments (ALL platforms/types — the
"chip everything" push, 2026-07-13) and classify each into a processing lane
using the cached _proto metadata. No DB writes.

Lanes:
  A  standalone, >=240s, has native chapters (>=3)     -> bulk chapter adopt
  B  standalone, >=240s, captions only (>=20 lines)    -> transcript inference
  C  montage slice (StartTime set), grouped by source  -> per-window chips
  D  standalone, <240s, has transcript                 -> thin heuristic chips
  E  no text signal (no chapters, <20 caplines)        -> multimodal / residual
  T  non-youtube (tiktok etc.)                         -> separate handling
  U  youtube but no cached metadata yet                -> fetch first

Output: _proto/chip_all_inventory.tsv
  lane, videoDbId, ytid, platform, videoType, start, end, srcDur, chapters,
  caplines, danceId, danceName
"""
import json, os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPSETTINGS = os.path.join(ROOT, "DancePlatform.API", "appsettings.Development.json")
OUT = os.path.join(ROOT, "_proto", "chip_all_inventory.tsv")


def prod_conn():
    d = json.load(open(APPSETTINGS, encoding="utf-8-sig"))
    for v in d.get("ConnectionStrings", {}).values():
        if "192.168.0.197" in v:
            return dict(p.split("=", 1) for p in v.split(";") if "=" in p)
    raise SystemExit("No prod connection string found")


def psql(sql):
    c = prod_conn()
    env = dict(os.environ); env["PGPASSWORD"] = c.get("Password", ""); env["PGCLIENTENCODING"] = "UTF8"
    p = subprocess.run(["psql", "-h", c["Host"], "-U", c["Username"], "-d", c["Database"],
                        "-At", "-F", "\t", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr); raise SystemExit(2)
    return [l.split("\t") for l in p.stdout.splitlines() if l]


def cache_signal(ytid):
    """(srcDur, nChapters, nCaplines) from _proto caches, or None if uncached."""
    sec = os.path.join(ROOT, "_proto", f"sec_{ytid}.txt")
    meta = os.path.join(ROOT, "_proto", f"{ytid}.json")
    dur = chapters = caplines = 0
    if os.path.exists(meta):
        try:
            d = json.load(open(meta, encoding="utf-8"))
            dur = int(d.get("duration") or 0)
            chapters = len(d.get("chapters") or [])
        except Exception:
            pass
    if os.path.exists(sec):
        in_tr = False
        for l in open(sec, encoding="utf-8").read().splitlines():
            if l.strip() == "transcript:":
                in_tr = True; continue
            if in_tr and re.match(r"\d\d:\d\d\s+\S", l):
                caplines += 1
            if not in_tr and not dur:
                m = re.match(r"dur\s*:.*\((\d+)s\)", l)
                if m:
                    dur = int(m.group(1))
        return (dur, chapters, caplines)
    if os.path.exists(meta):
        return (dur, chapters, -1)  # metadata yes, transcript never fetched
    return None


def main():
    rows = psql("""SELECT v."Id", v."VideoId", v."Platform", coalesce(v."VideoType",''),
       coalesce(v."StartTime"::text,''), coalesce(v."EndTime"::text,''),
       coalesce(v."DurationSeconds"::text,''), d."Id", d."Name"
FROM "Videos" v JOIN "Dances" d ON d."Id"=v."DanceId"
WHERE NOT EXISTS (SELECT 1 FROM "VideoSegments" s WHERE s."VideoId"=v."Id")
ORDER BY v."VideoId", v."StartTime" NULLS FIRST, v."Id";""")

    out, lanes, uncached = [], {}, set()
    for vid_db, ytid, platform, vtype, st, et, dbdur, dance_id, dance in rows:
        if platform != "youtube":
            lane, dur, ch, cap = "T", int(dbdur or 0), 0, 0
        else:
            sig = cache_signal(ytid)
            if sig is None:
                lane, dur, ch, cap = "U", int(dbdur or 0), 0, 0
                uncached.add(ytid)
            else:
                dur, ch, cap = sig
                dur = dur or int(dbdur or 0)
                if st != "":
                    lane = "C"
                elif dur >= 240 and ch >= 3:
                    lane = "A"
                elif dur >= 240 and cap >= 20:
                    lane = "B"
                elif dur < 240 and cap >= 5:
                    lane = "D"
                else:
                    lane = "E"
        lanes[lane] = lanes.get(lane, 0) + 1
        out.append("\t".join(map(str, (lane, vid_db, ytid, platform, vtype, st, et, dur, ch, cap, dance_id, dance))))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(
        "lane\tvideoDbId\tytid\tplatform\tvideoType\tstart\tend\tsrcDur\tchapters\tcaplines\tdanceId\tdanceName\n"
        + "\n".join(out) + "\n")

    print(f"{len(out)} unchipped videos -> {OUT}")
    for k in sorted(lanes):
        print(f"  lane {k}: {lanes[k]}")
    if uncached:
        print(f"uncached ytids ({len(uncached)}): fetch with prep_sections.py")
        open(os.path.join(ROOT, "_proto", "chip_uncached.txt"), "w").write("\n".join(sorted(uncached)) + "\n")


if __name__ == "__main__":
    main()
