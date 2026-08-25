"""
merge_variant_dances.py [--apply]

Folds "variant" dance rows back into the base dance they were sliced off.

Background: several seeding runs took a single tutorial and cut it into one *dance*
per time-range — so `Icb8TMr5s9k` ("LEARN 3 HIP HOP GROOVES") produced twelve dances
(Bart Simpson (Breakdown), (Practice), (Variation), (Practice Variation), and the same
again for Biz Markie and Gucci) alongside the three real moves that already existed.
A tap video did the same thing with slow/fast passes of five combos. The result is one
move spread over five pages, sometimes under five different styles.

A slice is a *video of* a move, not a move. So each variant's video is reattached to the
base dance (where the dance page already renders several videos as an accordion), the
video is retitled to what the slice actually shows ("Breakdown", "Fast", …), and the
now-empty variant dance row is deleted.

Every FK into "Dances" is ON DELETE CASCADE, including PracticeSessionItems and the
user status joins — so user state MUST be repointed at the base before the delete, or
deleting the row silently takes practice history with it. That is what MOVE_USER_STATE
below does; do not reorder it after the DELETE.

Reads the prod connection string from DancePlatform.API/appsettings.Development.json.
Dry-run by default: prints the plan and touches nothing. Pass --apply to commit.
"""
import json, os, subprocess, sys

# pythonw.exe (used to run the dashboard detached) has no stdout, and an
# unguarded reconfigure() throws on import - which surfaced as an HTTP handler
# dying with an empty response rather than an error.
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPSETTINGS = os.path.join(ROOT, "DancePlatform.API", "appsettings.Development.json")

# variant dance id -> (base dance id, title for the video once it lands on the base)
MERGES = {
    # Icb8TMr5s9k — "LEARN 3 HIP HOP GROOVES" sliced per move x per section
    198: (78, "Breakdown"),
    199: (78, "Practice"),
    200: (78, "Variation"),
    201: (78, "Practice Variation"),
    202: (72, "Breakdown"),
    203: (72, "Practice"),
    204: (72, "Variation"),
    205: (72, "Practice Variation"),
    206: (67, "Breakdown"),
    207: (67, "Practice"),
    208: (67, "Variation"),
    209: (67, "Practice Variation"),
    # MdyoeIogMFo — five tap combos taught slow, then the same five fast
    1471: (1461, "Fast"),
    1473: (1463, "Fast"),
    1474: (1465, "Fast"),
    1476: (1467, "Fast"),
    1487: (1469, "Fast"),
    # jAIwJd2tQo0 — single-slice variants of a move already in the catalogue
    1012: (1011, "Clap behind"),
    1045: (1044, "Turning"),
    1066: (1065, "Jackson 5"),
}

# The base dance's own video keeps a raw YouTube title ("60 Hip Hop Dance Steps | …"),
# which reads badly in an accordion next to "Breakdown"/"Practice". Relabel it to its
# role in the set. Only applied to bases that gain siblings below.
BASE_TITLES = {
    78: "Overview", 72: "Overview", 67: "Overview",
    1461: "Slow", 1463: "Slow", 1465: "Slow", 1467: "Slow", 1469: "Slow",
    1011: "Basic", 1044: "Basic", 1065: "Basic",
}


def prod_conn():
    d = json.load(open(APPSETTINGS, encoding="utf-8-sig"))
    for v in d.get("ConnectionStrings", {}).values():
        if "192.168.0.197" in v:
            return dict(p.split("=", 1) for p in v.split(";") if "=" in p)
    raise SystemExit("No prod (192.168.0.197) connection string in appsettings.Development.json")


def psql(sql, quiet=False):
    c = prod_conn()
    env = dict(os.environ)
    env["PGPASSWORD"] = c.get("Password", "")
    env["PGCLIENTENCODING"] = "UTF8"
    p = subprocess.run(["psql", "-h", c["Host"], "-U", c["Username"], "-d", c["Database"],
                        "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr)
        raise SystemExit(2)
    if not quiet and p.stderr.strip():
        sys.stderr.write(p.stderr)
    return [l.split("\t") for l in p.stdout.splitlines() if l]


def show_plan():
    ids = ",".join(str(i) for i in MERGES)
    bases = ",".join(str(b) for b, _ in MERGES.values())
    names = {r[0]: r[1] for r in psql(f'select "Id", "Name" from "Dances" where "Id" in ({ids},{bases})', quiet=True)}
    print(f"{len(MERGES)} variant dances -> {len(set(b for b, _ in MERGES.values()))} base dances\n")
    for var, (base, title) in sorted(MERGES.items(), key=lambda kv: (kv[1][0], kv[0])):
        print(f"  {names.get(str(base),'?'):<45} <- {names.get(str(var),'?'):<45} as \"{title}\"")

    state = psql(f"""
        select 'favorites', count(*) from "UserFavoriteDances" where "DanceId" in ({ids})
        union all select 'learned', count(*) from "UserLearnedDances" where "DanceId" in ({ids})
        union all select 'in-progress', count(*) from "UserInProgressDances" where "DanceId" in ({ids})
        union all select 'practice items', count(*) from "PracticeSessionItems" where "DanceId" in ({ids})
    """, quiet=True)
    print("\nuser state to carry over to the base dance:")
    for k, n in state:
        print(f"  {k:<16} {n}")


def build_sql():
    parts = ["begin;"]

    for base, title in BASE_TITLES.items():
        parts.append(f"""update "Videos" set "Title" = '{title}' where "DanceId" = {base};""")

    for var, (base, title) in MERGES.items():
        parts.append(f"""
-- {var} -> {base}
insert into "UserFavoriteDances" ("UserId", "DanceId", "DateAdded")
  select "UserId", {base}, "DateAdded" from "UserFavoriteDances" where "DanceId" = {var}
  on conflict do nothing;
insert into "UserLearnedDances" ("UserId", "DanceId", "DateAdded")
  select "UserId", {base}, "DateAdded" from "UserLearnedDances" where "DanceId" = {var}
  on conflict do nothing;
insert into "UserInProgressDances" ("UserId", "DanceId", "DateAdded")
  select "UserId", {base}, "DateAdded" from "UserInProgressDances" where "DanceId" = {var}
  on conflict do nothing;
update "PracticeSessionItems" set "DanceId" = {base} where "DanceId" = {var};
update "Videos" set "DanceId" = {base}, "Title" = '{title}' where "DanceId" = {var};
delete from "Dances" where "Id" = {var};""")

    parts.append("commit;")
    return "\n".join(parts)


def verify():
    ids = ",".join(str(i) for i in MERGES)
    bases = sorted(set(b for b, _ in MERGES.values()))
    left = psql(f'select count(*) from "Dances" where "Id" in ({ids})', quiet=True)[0][0]
    orphan = psql(f'select count(*) from "Videos" where "DanceId" in ({ids})', quiet=True)[0][0]
    print(f"\nvariant dance rows remaining: {left} (expected 0)")
    print(f"videos still pointing at them: {orphan} (expected 0)")
    print("\nresulting dances:")
    for b in bases:
        rows = psql(f"""select d."Name", d."Slug",
                          (select count(*) from "Videos" v where v."DanceId" = d."Id"),
                          (select string_agg(v."Title", ', ' order by v."StartTime")
                             from "Videos" v where v."DanceId" = d."Id")
                        from "Dances" d where d."Id" = {b}""", quiet=True)
        for name, slug, n, titles in rows:
            print(f"  {name:<45} /{slug:<40} {n} videos: {titles}")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    show_plan()
    if not apply:
        print("\n[dry run] nothing written. re-run with --apply to commit.")
        sys.exit(0)
    print("\napplying...")
    psql(build_sql())
    verify()
