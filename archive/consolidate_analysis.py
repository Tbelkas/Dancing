"""
DRY-RUN analysis for DancePlatform prod cleanup.
1) Detect name-variant duplicate dances (same move under "The X" / accent / spacing variants).
2) Plan style de-dup (strip redundant 2nd style tag, keep more-specific style).
No writes. Emits a report + writes merge_plan.json for the executor.
"""
import csv, io, json, os, re, subprocess, unicodedata, sys

PGHOST = "192.168.0.197"; PGUSER = "dance_user"; PGDB = "dancing"; PGPW = "dancebabydance"

def q(sql):
    env = dict(os.environ); env["PGPASSWORD"] = PGPW
    p = subprocess.run(
        ["psql", "-h", PGHOST, "-U", PGUSER, "-d", PGDB, "-At", "-F", "\t", "-c", sql],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    if p.returncode != 0:
        sys.stderr.write(p.stderr); raise SystemExit("psql failed")
    return [line.split("\t") for line in p.stdout.splitlines() if line]

def norm(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().strip()
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s

# ---- pull dances with video + style + user-data signal ----
rows = q("""
SELECT d."Id", d."Name", d."Slug",
  COALESCE((SELECT count(*) FROM "Videos" v WHERE v."DanceId"=d."Id"),0),
  COALESCE((SELECT count(*) FROM "Videos" v WHERE v."DanceId"=d."Id" AND v."StartTime" IS NOT NULL AND v."EndTime" IS NOT NULL),0),
  COALESCE((SELECT max(v."VideoId") FROM "Videos" v WHERE v."DanceId"=d."Id"),''),
  (SELECT count(*) FROM "UserFavoriteDances" x WHERE x."DanceId"=d."Id")
   +(SELECT count(*) FROM "UserLearnedDances" x WHERE x."DanceId"=d."Id")
   +(SELECT count(*) FROM "UserInProgressDances" x WHERE x."DanceId"=d."Id")
   +(SELECT count(*) FROM "DanceRatings" x WHERE x."DanceId"=d."Id")
   +(SELECT count(*) FROM "PracticeSessions" x WHERE x."DanceId"=d."Id"),
  COALESCE((SELECT string_agg(s."Name",',') FROM "DanceStyles" ds JOIN "Styles" s ON s."Id"=ds."StyleId" WHERE ds."DanceId"=d."Id"),'')
FROM "Dances" d ORDER BY d."Id";
""")

dances = {}
for r in rows:
    did = int(r[0])
    dances[did] = dict(id=did, name=r[1], slug=r[2], nvid=int(r[3]),
                       nclip=int(r[4]), videoid=r[5], udata=int(r[6]), styles=r[7])

# ---- group by normalized name ----
groups = {}
for d in dances.values():
    groups.setdefault(norm(d["name"]), []).append(d)
dupgroups = {k: v for k, v in groups.items() if len(v) > 1}

def survivor(members):
    # prefer: has real clip, then most user-data, then most videos, then lowest id
    return sorted(members, key=lambda m: (-(m["nclip"]>0), -m["udata"], -m["nvid"], m["id"]))[0]

plan = []
total_losers = 0
print(f"=== NAME-VARIANT DUPLICATE GROUPS: {len(dupgroups)} groups ===\n")
for k in sorted(dupgroups):
    members = dupgroups[k]
    surv = survivor(members)
    losers = [m for m in members if m["id"] != surv["id"]]
    total_losers += len(losers)
    style_set = {m["styles"] for m in members}
    flag = "  <<< STYLES DIFFER - REVIEW" if len(style_set) > 1 else ""
    print(f"[{k}]{flag}")
    for m in members:
        tag = "KEEP " if m["id"] == surv["id"] else "drop "
        print(f"   {tag} #{m['id']:<5} {m['name']:<32} vid={m['videoid']:<12} clip={m['nclip']} udata={m['udata']} styles={m['styles']}")
    plan.append(dict(norm=k, survivor=surv["id"], losers=[m["id"] for m in losers],
                     survivor_name=surv["name"]))
    print()

print(f"=== SUMMARY: {len(dupgroups)} groups, {total_losers} dances to merge away "
      f"({len(dances)} -> {len(dances)-total_losers}) ===")
losers_with_udata = sum(1 for g in dupgroups.values() for m in g
                        if m["id"] != survivor(g)["id"] and m["udata"] > 0)
print(f"Loser dances carrying user data (need repoint): {losers_with_udata}")

json.dump(plan, open("merge_plan.json", "w"), indent=2)
print("\nWrote merge_plan.json")
