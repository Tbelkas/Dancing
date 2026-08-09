"""
seed_waacking_foundations.py [apply]

Seed the Waacking foundations the catalog was missing, so the roadmap rewrite has real
moves to point at.

Why these: the old roadmap was built from the chapter list of a single beginner video, so
the catalog only ever grew the moves that video happened to mention. Four independent
teaching syllabi — Princess Lockerooo's waackingclass.com volumes, Versa-Style's four-part
tutorial, The Get Down's lesson series and Bagsy's twelve-part "Learn To Dance Waacking" —
agree on a vocabulary the catalog had none of: hand positions, warm-up, lines, overheads
(bolos), the inside/outside roll distinction, extensions, gestures, propeller, and punking
as a named character foundation rather than an afterthought.

Every video below was checked by transcript or by resolving it back to YouTube, not by
title alone. Durations and view counts are the real ones as of seeding.

Idempotent: skips any dance whose slug already exists in the Waacking style, and any video
whose YouTube id is already attached to the dance it would be added to.

Dry-run unless 'apply'.
"""
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

PGHOST = "192.168.0.197"; PGUSER = "dance_user"; PGDB = "dancing"


def _prod_password():
    """Read the prod DB password from appsettings (gitignored) rather than hardcoding it.

    This repo is public: a literal here leaks the production database on every push.
    """
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _cfg = os.path.join(_root, "DancePlatform.API", "appsettings.Development.json")
    for _v in json.load(open(_cfg, encoding="utf-8-sig")).get("ConnectionStrings", {}).values():
        if "192.168.0.197" in _v:
            return dict(_p.split("=", 1) for _p in _v.split(";") if "=" in _p).get("Password", "")
    raise SystemExit(f"No prod (192.168.0.197) connection string in {_cfg}")


PGPW = _prod_password()
APPLY = "apply" in sys.argv[1:]

STYLE_ID = 8    # Waacking
MUSIC_ID = 6    # Electronic / EDM — matches the seven existing Waacking dances.
                # There is no Disco musical style; adding one is a taxonomy decision,
                # not something to slip in here. See the note printed at the end.

# (name, difficulty, description, [(ytid, duration, views, title), ...])
DANCES = [
    ("The Whack", 1,
     "The strike the style is named for: the arm drives out from the centre of the chest "
     "with force, the chest activating behind it. Not a circle — that is a roll.",
     [("MTMcRWMsvW8", 394, 6103, "THE WHACK- Whacking Dance Tutorial")]),

    ("Overheads", 1,
     "Hands start at the chest, travel over the head to between the shoulder blades and "
     "snap back like a rubber band. The elbows lift with the arms.",
     [("XXI5YCKAbMA", 402, 4155, "OVERHEADS- Whacking Dance Tutorial"),
      ("z1KObpZM6Lk", 284, 977, "Waacking: Bolos or Overheads")]),

    ("Punking", 1,
     "The theatrical half of the dance: taking an image and bringing it to life through "
     "character, persona and drama. Also the style's reclaimed original name.",
     [("LRdc1wxBYTY", 372, 9860, "PUNKING- Whacking Dance Tutorial")]),

    ("Waacking Hand Positions", 1,
     "What the hands do while the arms work — blades, a loose fist, a blossomed flower, one "
     "or two fingers extended. Relaxed throughout, and largely a matter of personal style.",
     [("5AQ2TxY1Tt4", 110, 1437, "Waacking: Hand Positions")]),

    ("Waacking Warm-Up", 1,
     "Wrist and shoulder preparation before any whipping. The arms take the load in this "
     "style, and cold shoulders are how waackers get hurt.",
     [("wfet71YbQi8", 169, 1519, "Waacking: Warm Ups"),
      ("fPVgWK6P1ss", 239, 2987, "Waacking: Warm Up Drills")]),

    ("Waacking Lines", 1,
     "Arms travelling point to point — up, out, down — held parallel to the floor and fully "
     "extended, struck with force rather than placed.",
     [("kpTDmW44lBQ", 159, 1008, "Waacking: Lines"),
      ("lTZm0GVg6as", 443, 6885, "Online Tutorial Series: Waacking Dance - Lines & Twirls")]),

    ("Arm Rolls", 1,
     "Continuous rotation of the arm that never stops at the top — the connective tissue "
     "between one whip and the next pose.",
     [("ndAZQ4VBV2k", 275, 5415, "Waacking: Arm Rolls")]),

    ("Waacking Arm Drills", 1,
     "Repeatable drills that build arm control, stamina and muscle memory, worked slowly "
     "before any tempo is added.",
     [("1dYSUkQDFf4", 629, 94466, "5 BASIC WAACKING ARM DRILLS"),
      ("1FEOjMPhxLE", 369, 425095, "5 Essential Basic Waacking Arms + Basic Combo"),
      ("jWq5B8Z3ig4", 766, 1061, "Waacking Basics Drills")]),

    ("Show the Music", 1,
     "The founding instruction of the style: the arms exist to show what the record is "
     "doing. Includes the upright \"conductor's form\" everything else is thrown from.",
     [("R8YMW9ypfJI", 527, 60299,
       "Learn to Dance Waacking #1 | Bagsy | Arm Drills to Show The Music")]),

    ("Outside Rolls", 2,
     "Bolos rolled outward so the audience reads the whole circle: front of the shoulder, "
     "rotate, back, over the head, down the other side.",
     [("fj7dO7ns-fU", 475, 19526,
       "Learn to Dance Waacking #2 | Bagsy | Bolos 'Outside Rolls' Technique")]),

    ("Inside Rolls", 2,
     "The bolo taken on the inside line, pulling back rather than showing the shape — the "
     "dynamic the original waackers borrowed from martial arts films.",
     [("5LyUy8IhjGs", 547, 9957,
       "Learn To Dance Waacking #6 | Bagsy | Inside Rolling Technique")]),

    ("Extensions and Grooves", 2,
     "Reaching the arm all the way out of the body while a groove keeps running underneath, "
     "so the shape reads without the dance going static.",
     [("Ei90dashg6Q", 697, 15926,
       "Learn to Dance Waacking #3 | Bagsy | Extension and Grooves")]),

    ("Martial Arts Influence", 2,
     "The kung-fu and nunchuck dynamics the original waackers pulled out of 1970s martial "
     "arts films, and how they shape the paths the arms take.",
     [("iWNpt0Mti70", 488, 16918,
       "Learn To Dance Waacking #4 | Bagsy | Inspirations of Martial Arts")]),

    ("Loops and Musical Accents", 3,
     "Catching the repeating figures in a disco record and hitting the accents on top of "
     "them, instead of laying an eight-count over the song.",
     [("38iRXGiLItk", 565, 8808,
       "Learn To Dance Waacking #7 | Bagsy | Loops and Musical Accents")]),

    ("Propeller", 3,
     "Vertical and horizontal arm swings driven by momentum, the arm carried round on its "
     "own weight rather than thrown afresh each time.",
     [("YZuZtUjAU88", 440, 16877,
       "Learn To Dance Waacking #8 | Bagsy | Propeller and Helicopter Style")]),

    ("Power and Speed", 3,
     "Tightening the paths you already own until they snap, without letting the circle "
     "collapse or the elbow start leading the shoulder.",
     [("-CqBB7XIXrE", 626, 13514,
       "Learn To Dance Waacking #10 | Bagsy | Power and Speed")]),

    ("The Butterfly", 3,
     "Both arms mirroring each other open and closed across the body — a symmetrical "
     "pattern that reads from the far side of a battle floor.",
     [("kRU9wl7926Q", 376, 13121,
       "Learn To Dance Waacking #11 | Bagsy | The Butterfly Effect")]),

    ("Three-Point Waack Attack", 3,
     "A three-hit pattern aimed at three separate points, giving a phrase of whips "
     "somewhere definite to land.",
     [("QK-MSyX4Lns", 347, 16598,
       "Learn To Dance Waacking #9 | Bagsy | 3-Point Waack Attack Technique")]),

    ("Waacking Gestures", 2,
     "Hair brushes, face frames and the small hand gestures that carry the character "
     "between the bigger arm movements.",
     [("cTOEgW6NKQw", 345, 4198, "Online Tutorial Series: Waacking Dance - Gestures")]),

    ("Waacking Combo", 2,
     "A full routine stringing arms, poses and travel into one phrase — where the "
     "vocabulary starts reading as dancing rather than drilling.",
     [("N24G2AepRCM", 550, 19272,
       "Online Tutorial Series: Waacking Dance - Choreography")]),
]

# Extra videos onto dances that already exist, keyed by slug. Versa-Style's posing lesson
# belongs on the existing waacking-poses dance rather than duplicating the concept.
EXTRA_VIDEOS = {
    "waacking-poses": [("l3PfYPUt_bQ", 285, 3679, "POSING- Whacking Dance Tutorial")],
}


def psql(sql, fetch=True):
    env = dict(os.environ)
    env["PGPASSWORD"] = PGPW
    env["PGCLIENTENCODING"] = "UTF8"
    p = subprocess.run(
        ["psql", "-h", PGHOST, "-U", PGUSER, "-d", PGDB,
         "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t"],
        input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr)
        raise SystemExit(2)
    return [l.split("\t") for l in p.stdout.splitlines() if l] if fetch else None


def q(s):
    return "'" + s.replace("'", "''") + "'"


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "dance"


existing = {s: int(i) for i, s in psql(
    f'select d."Id", d."Slug" from "Dances" d join "DanceStyles" ds on ds."DanceId"=d."Id" '
    f'where ds."StyleId"={STYLE_ID};')}

new_dances, new_videos, skipped = [], [], []
for name, diff, desc, vids in DANCES:
    sl = slugify(name)
    if sl in existing:
        skipped.append(sl)
        continue
    new_dances.append((name, sl, diff, desc, vids))
    new_videos.extend(v[0] for v in vids)

print(f"=== {len(new_dances)} new dances, {len(new_videos)} new videos ===")
for name, sl, diff, desc, vids in new_dances:
    print(f"  + {name:28} diff {diff}  slug {sl}")
    for ytid, dur, views, title in vids:
        print(f"      video {ytid:<12} {dur:>4}s {views:>7} views  {title[:58]}")
if skipped:
    print(f"\n  already present, skipped: {', '.join(skipped)}")

print("\n=== extra videos on existing dances ===")
extra_plan = []
for sl, vids in EXTRA_VIDEOS.items():
    did = existing.get(sl)
    if did is None:
        print(f"  ! {sl}: not a Waacking dance, skipping")
        continue
    have = {r[0] for r in psql(f'select "VideoId" from "Videos" where "DanceId"={did};')}
    for ytid, dur, views, title in vids:
        if ytid in have:
            print(f"  = {sl}: {ytid} already attached")
            continue
        extra_plan.append((did, sl, ytid, dur, views, title))
        print(f"  + {sl} (dance {did}) <- {ytid} {dur}s  {title[:50]}")

if not APPLY:
    print("\n(dry-run; pass 'apply' to write)")
    raise SystemExit(0)

for name, sl, diff, desc, vids in new_dances:
    # The video rows have to be cross-joined onto the inserted dance: a VALUES list is
    # its own scope and cannot see the `d` CTE, which is what a first pass got wrong.
    vals = ", ".join(f'({q(t)}, {q(y)}, {vw}, {dur})' for y, dur, vw, t in vids)
    sql = f"""begin;
with d as (
  insert into "Dances" ("Name","Slug","Description","DateAdded","Difficulty")
  values ({q(name)}, {q(sl)}, {q(desc)}, now(), {diff}) returning "Id"),
 s as (insert into "DanceStyles" ("DanceId","StyleId") select "Id",{STYLE_ID} from d returning 1),
 m as (insert into "DanceMusicalStyles" ("DanceId","MusicalStyleId") select "Id",{MUSIC_ID} from d returning 1),
 v as (insert into "Videos" ("Title","VideoId","Platform","VideoType","DateAdded","ViewCount","DurationSeconds","DanceId")
       select x.title, x.ytid, 'youtube', 'tutorial', now(), x.views, x.dur, d."Id"
       from d cross join (values {vals}) as x(title, ytid, views, dur)
       returning "Id","DanceId")
select "DanceId", count(*) from v group by 1;
commit;"""
    psql(sql, fetch=False)
    # Read the ids back rather than parsing psql's output for the CTE: the multi-statement
    # transaction does not reliably put that row on stdout under -At.
    got = psql(f'select d."Id", (select count(*) from "Videos" v where v."DanceId"=d."Id") '
               f'from "Dances" d join "DanceStyles" ds on ds."DanceId"=d."Id" '
               f'where ds."StyleId"={STYLE_ID} and d."Slug"={q(sl)};')
    print(f"  + {sl:32} dance {got[0][0]}, {got[0][1]} video(s)")

for did, sl, ytid, dur, views, title in extra_plan:
    psql(f'insert into "Videos" ("Title","VideoId","Platform","VideoType","DateAdded",'
         f'"ViewCount","DurationSeconds","DanceId") values ({q(title)},{q(ytid)},\'youtube\','
         f"'tutorial', now(), {views}, {dur}, {did});", fetch=False)
    print(f"  + {sl:32} <- {ytid}")

print(f"\napplied: {len(new_dances)} dances, {len(new_videos) + len(extra_plan)} videos")
print("""
Follow-ups:
  - There is no Disco musical style, so these are tagged Electronic / EDM to match the
    existing Waacking dances. Waacking is a disco style and locking/hustle would want the
    same tag — worth adding one deliberately rather than as a side effect of seeding.
  - "Waacking Arm Drills" carries Marralisa D'silva's chaptered 5-drill video; run the
    find-chips flow on it so a roadmap step can pin one drill instead of all five.
""")
