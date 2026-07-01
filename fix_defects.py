"""fix_defects.py [apply] — execute the video-quality-audit DEFECT fixes in one tx.
Dry-run prints the plan; pass 'apply' to write. Read PGPW from this file. Idempotent-ish
(guards on existence). Covers: copy chips Cross-Body Lead, delete dupe dances, delete dup row."""
import os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
APPLY = len(sys.argv) > 1 and sys.argv[1] == "apply"
PGPW = "LW3Q19jZyVSXRzNyGoRnWY2G3TKFT8eoRuYR"

def psql(sql):
    env = dict(os.environ); env["PGPASSWORD"] = PGPW; env["PGCLIENTENCODING"] = "UTF8"
    p = subprocess.run(["psql", "-h", "192.168.0.197", "-U", "dance_user", "-d", "dancing",
                        "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t"],
                       input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr); raise SystemExit(1)
    return p.stdout

# dances to delete entirely (id -> reason). All verified zero-user-data in audit.
DEL_DANCES = {
    1992: "dupe of Hair Flip d1781",
    1991: "dupe of Floor Roll d1734",
    2044: "dupe of Spin and Dip d1732",
    1970: "dupe of Wing d1864",
    1873: "dupe of Locking d899",
    1860: "dupe of Cross-Body Lead d269 (chips copied first)",
    672:  "Krump mis-tag dupe of Attitude Turn d1859",
    1687: "Jazz mis-tag dupe of Heels Choreography d1980",
}
DEL_VIDEO_ROWS = [2051]  # Pas de Bourree duplicate row (keep v1757)

def fetch_segments(video_id):
    rows = psql(f'''SELECT "Label","StartTime",COALESCE("EndTime"::text,'') FROM "VideoSegments"
                    WHERE "VideoId"={video_id} ORDER BY "StartTime";''')
    return [r.split("\t") for r in rows.splitlines() if r]

# --- pre-step: copy Cross-Body Lead chips from dupe video (v1904) to keeper video (v262) ---
src_segs = fetch_segments(1904)
keeper_has = fetch_segments(262)
print(f"Cross-Body Lead: dupe v1904 has {len(src_segs)} chips; keeper v262 has {len(keeper_has)}")

def sql_lit(s): return s.replace("'", "''")

stmts = ["BEGIN;"]
if src_segs and not keeper_has:
    vals = ",".join(
        f"('{sql_lit(lbl)}',{st},{'NULL' if not et else et},262)" for lbl, st, et in src_segs)
    stmts.append(f'UPDATE "Videos" SET "VideoType"=\'tutorial\' WHERE "Id"=262;')
    stmts.append(f'DELETE FROM "VideoSegments" WHERE "VideoId"=262;')
    stmts.append(f'INSERT INTO "VideoSegments"("Label","StartTime","EndTime","VideoId") VALUES {vals};')
    print(f"  -> will copy {len(src_segs)} chips onto v262")

# --- delete dupe dances (videos -> segments/ratings/loops -> joins -> dance) ---
for did, reason in DEL_DANCES.items():
    print(f"DELETE dance {did}: {reason}")
    stmts += [
        f'DELETE FROM "VideoSegments" WHERE "VideoId" IN (SELECT "Id" FROM "Videos" WHERE "DanceId"={did});',
        f'DELETE FROM "VideoRatings"  WHERE "VideoId" IN (SELECT "Id" FROM "Videos" WHERE "DanceId"={did});',
        f'DELETE FROM "UserVideoLoops" WHERE "VideoId" IN (SELECT "Id" FROM "Videos" WHERE "DanceId"={did});',
        f'DELETE FROM "Videos" WHERE "DanceId"={did};',
        f'DELETE FROM "DanceStyles" WHERE "DanceId"={did};',
        f'DELETE FROM "DanceMusicalStyles" WHERE "DanceId"={did};',
        f'DELETE FROM "DanceInstructors" WHERE "DanceId"={did};',
        f'DELETE FROM "Dances" WHERE "Id"={did};',
    ]

# --- delete duplicate video rows (keep the other row on same dance) ---
for vid in DEL_VIDEO_ROWS:
    print(f"DELETE video row {vid} (duplicate on same dance)")
    stmts += [
        f'DELETE FROM "VideoSegments" WHERE "VideoId"={vid};',
        f'DELETE FROM "VideoRatings"  WHERE "VideoId"={vid};',
        f'DELETE FROM "UserVideoLoops" WHERE "VideoId"={vid};',
        f'DELETE FROM "Videos" WHERE "Id"={vid};',
    ]
stmts.append("COMMIT;")

if not APPLY:
    print("\n(dry-run; pass 'apply' to write)")
    raise SystemExit(0)
out = psql("\n".join(stmts))
sys.stdout.write(out)
print("APPLIED")
