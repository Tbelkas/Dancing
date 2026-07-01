"""resource_apply.py [apply] — re-source mis-sourced Video rows to verified-embeddable
replacements (updates VideoId/Title, clears StartTime/EndTime + old segments), and delete
2 fabricated montage-artifact dances. Dry-run unless 'apply'."""
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

# videoRowId -> (newYtid, newTitle, dance)
RESOURCE = {
    433:  ("KFo9wrVVqA4", "Learn How to Breakdance - Knee Slide (Lesson 3)", "Knee Slide d446"),
    464:  ("ezYQ_emrvJc", "House Dance Tutorial - Slide Variations", "The Slide d477"),
    402:  ("zn81KebgGNg", "House Dance Tutorial - Spiral Turn", "Spiral d411 (was Contemporary clip)"),
    1583: ("pdflPRTL1a8", "How to do the Backwards Shuffle (Reverse Running Man)", "Backward Shuffle d1639"),
}
DEL_FABRICATED = {366: "Lift-Off (fabricated montage move, generic kids routine)",
                  940: "Small Thing (fabricated montage move, generic kids routine)"}

def lit(s): return s.replace("'", "''")
stmts = ["BEGIN;"]
for vrow, (yt, title, who) in RESOURCE.items():
    print(f"RE-SOURCE v{vrow} [{who}] -> {yt}")
    stmts += [
        f'DELETE FROM "VideoSegments" WHERE "VideoId"={vrow};',
        f'''UPDATE "Videos" SET "VideoId"='{yt}', "Title"='{lit(title)}', "Platform"='youtube',
            "VideoType"='tutorial', "StartTime"=NULL, "EndTime"=NULL WHERE "Id"={vrow};''',
    ]
for did, why in DEL_FABRICATED.items():
    print(f"DELETE dance {did}: {why}")
    stmts += [
        f'DELETE FROM "VideoSegments" WHERE "VideoId" IN (SELECT "Id" FROM "Videos" WHERE "DanceId"={did});',
        f'DELETE FROM "VideoRatings" WHERE "VideoId" IN (SELECT "Id" FROM "Videos" WHERE "DanceId"={did});',
        f'DELETE FROM "UserVideoLoops" WHERE "VideoId" IN (SELECT "Id" FROM "Videos" WHERE "DanceId"={did});',
        f'DELETE FROM "Videos" WHERE "DanceId"={did};',
        f'DELETE FROM "DanceStyles" WHERE "DanceId"={did};',
        f'DELETE FROM "DanceMusicalStyles" WHERE "DanceId"={did};',
        f'DELETE FROM "DanceInstructors" WHERE "DanceId"={did};',
        f'DELETE FROM "Dances" WHERE "Id"={did};',
    ]
stmts.append("COMMIT;")
if not APPLY:
    print("\n(dry-run; pass 'apply')"); raise SystemExit(0)
sys.stdout.write(psql("\n".join(stmts)))
print("APPLIED")
