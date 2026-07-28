"""
fix_labels.py [apply]
Retag mis-styled dances found by audit_labels.py (2026-07-14 label audit).
The video content is the ground truth: seeding gave montage slices random
styles (e.g. shuffle moves tagged Hip-hop, vernacular-jazz vocab tagged
Waacking/Krump/House). Sets the dance's single style AND matching music
(Stretching gets NO music, per platform convention).

- MONTAGES: every dance attached to these ytids gets the montage's style,
  EXCEPT the 6 known mis-sourced p2JrE6JICKk video rows (444,469,686,890,
  1582,1584) which keep their style pending re-source.
- SINGLES: per-dance reviewed decisions.
Dry-run by default (ROLLBACK); pass `apply` to COMMIT.
"""
import json, os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPSETTINGS = os.path.join(ROOT, "DancePlatform.API", "appsettings.Development.json")

STYLE = {"Latin":1,"Ballroom":2,"Classical / Ballet":4,"Folk / Traditional":5,"Swing":6,
         "Contemporary":7,"Waacking":8,"Hip-hop":10,"House":11,"Breakdance":12,"Afrobeats":13,
         "Dancehall":14,"Jazz":20,"Tap":19,"Stretching":23,"Shuffle":29,"Bachata":36}
MUSIC = {"Latin":1,"Ballroom":5,"Classical / Ballet":2,"Folk / Traditional":2,"Swing":4,
         "Contemporary":2,"Waacking":6,"Hip-hop":3,"House":6,"Breakdance":3,"Afrobeats":11,
         "Dancehall":12,"Jazz":4,"Tap":4,"Stretching":None,"Shuffle":6,"Bachata":17}

# ytid -> target style; every dance with a video on that ytid moves.
MONTAGES = {
    "p2JrE6JICKk": "Shuffle",             # 47 Shuffle Dance Moves
    "jAIwJd2tQo0": "Swing",               # Alphabetical Jazz Steps (vernacular jazz)
    "xWiAh_EizqI": "Swing",               # Authentic Jazz Dance Vocabulary
    "NK6feUaxOgg": "Classical / Ballet",  # Beginner Ballet Barre
    "ELpdOqsl0Xw": "House",               # House Dance 30 Basic Moves
    "HZruz8wO0g8": "Tap",                 # Tap Dance Basics 5 Steps
    "N5c5buh5YJk": "Tap",                 # How to Tap Dance - Time Step
    "MdyoeIogMFo": "Tap",                 # Hatty's Tapdance Lesson 1
    "J3WmepkloY8": "Swing",               # ECS Basics
    "4veppv9jBXc": "Swing",               # ECS Basic Steps
    "MCsWJ5BFevk": "Swing",               # ECS Basic Steps
    "jkI-b5qrgis": "Swing",               # ECS Beginner
    "595AKDailds": "Folk / Traditional",  # Irish Jig step
    "RiG18QIHk-8": "Contemporary",        # Contemporary follow-along
    "mV-7A7SrkaA": "Latin",               # Salsa technique
    "EAP1E-B5qk8": "Folk / Traditional",  # Cowboy Hustle line dance
}
MISSOURCED_VIDEO_IDS = {444, 469, 686, 890, 1582, 1584}

# danceId -> target style (reviewed one by one against real YT titles)
SINGLES = {
    # was Waacking
    370:"Classical / Ballet", 407:"Classical / Ballet", 556:"Latin", 630:"Hip-hop",
    1050:"Dancehall", 345:"Jazz", 679:"Jazz", 800:"Jazz", 353:"Ballroom", 401:"Ballroom",
    375:"House", 704:"Shuffle", 851:"Breakdance", 815:"Bachata", 825:"Bachata",
    1661:"Swing", 1662:"Swing", 79:"Hip-hop", 1275:"Swing",
    # was Vogue
    1660:"Swing", 833:"Bachata", 387:"Ballroom", 333:"Swing", 488:"Latin",
    # was Ballroom
    687:"Classical / Ballet", 298:"Hip-hop", 806:"Jazz",
    # was Breakdance
    340:"Classical / Ballet", 822:"Bachata", 796:"Jazz", 224:"Classical / Ballet",
    1656:"Swing", 1284:"Swing", 1265:"Swing",
    # was House
    713:"Hip-hop", 459:"Folk / Traditional", 830:"Bachata", 932:"Afrobeats",
    1003:"Afrobeats", 284:"Latin", 1259:"Swing", 1242:"Swing",
    # was Jazz
    1728:"Folk / Traditional",
    # was Krump
    1646:"Swing", 1622:"Swing", 1647:"Swing",
    # was Latin
    676:"Contemporary", 814:"Jazz", 337:"Classical / Ballet", 1354:"Classical / Ballet",
    # was Contemporary / misc
    1323:"Stretching", 635:"Hip-hop", 369:"Ballroom",
    # was Hip-hop (non-montage singles)
    364:"Waacking", 393:"Waacking", 476:"Waacking",
    377:"Ballroom", 378:"Ballroom", 380:"Swing", 381:"Ballroom", 388:"Swing",
    390:"Ballroom", 453:"Ballroom", 496:"Ballroom", 744:"Ballroom", 838:"Ballroom",
    662:"Latin", 667:"Latin", 669:"Contemporary", 707:"Shuffle", 710:"Shuffle",
    768:"Swing", 772:"Swing", 790:"Jazz", 803:"Jazz", 834:"Bachata", 857:"Shuffle",
    1006:"Afrobeats", 1033:"Dancehall", 1238:"Swing", 1240:"Swing", 1244:"Swing",
    1252:"Swing", 1257:"Swing", 1269:"Swing", 1273:"Swing", 1280:"Swing",
    1451:"Stretching", 1455:"Stretching", 1567:"Tap", 1571:"Tap",
    1619:"Swing", 1623:"Swing", 1625:"Ballroom", 1626:"Swing", 1630:"Swing",
    1632:"Swing", 1634:"Ballroom", 1653:"Swing", 1657:"Swing", 1658:"Swing", 1659:"Swing",
}


def prod_conn():
    d = json.load(open(APPSETTINGS, encoding="utf-8-sig"))
    for v in d.get("ConnectionStrings", {}).values():
        if "192.168.0.197" in v:
            return dict(p.split("=", 1) for p in v.split(";") if "=" in p)
    raise SystemExit("No prod connection string")


def psql(sql):
    c = prod_conn()
    env = dict(os.environ); env["PGPASSWORD"] = c.get("Password",""); env["PGCLIENTENCODING"] = "UTF8"
    p = subprocess.run(["psql","-h",c["Host"],"-U",c["Username"],"-d",c["Database"],
                        "-At","-F","\t","-v","ON_ERROR_STOP=1","-f","-"],
                       input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr); raise SystemExit(2)
    return p.stdout


def main():
    apply = "apply" in sys.argv
    # Resolve montage dances (minus mis-sourced rows), current styles/music.
    yt = ",".join(f"'{y}'" for y in MONTAGES)
    rows = psql(f'''SELECT v."VideoId", v."Id", v."DanceId", d."Name", s."Name",
                           COALESCE(m."Id"::text,'')
        FROM "Videos" v JOIN "Dances" d ON d."Id"=v."DanceId"
        JOIN "DanceStyles" ds ON ds."DanceId"=d."Id" JOIN "Styles" s ON s."Id"=ds."StyleId"
        LEFT JOIN "DanceMusicalStyles" dm ON dm."DanceId"=d."Id"
        LEFT JOIN "MusicalStyles" m ON m."Id"=dm."MusicalStyleId"
        WHERE v."VideoId" IN ({yt});''')
    plan = {}   # danceId -> (name, oldStyle, newStyle, hasMusic)
    for ln in rows.splitlines():
        ytid, vid, did, name, style, mid = ln.split("\t")
        if int(vid) in MISSOURCED_VIDEO_IDS:
            continue
        plan[int(did)] = (name, style, MONTAGES[ytid], mid != "")
    ids = ",".join(str(i) for i in SINGLES)
    rows = psql(f'''SELECT d."Id", d."Name", s."Name", COALESCE(dm."MusicalStyleId"::text,'')
        FROM "Dances" d JOIN "DanceStyles" ds ON ds."DanceId"=d."Id"
        JOIN "Styles" s ON s."Id"=ds."StyleId"
        LEFT JOIN "DanceMusicalStyles" dm ON dm."DanceId"=d."Id"
        WHERE d."Id" IN ({ids});''')
    seen = set()
    for ln in rows.splitlines():
        did, name, style, mid = ln.split("\t")
        plan[int(did)] = (name, style, SINGLES[int(did)], mid != "")
        seen.add(int(did))
    missing = set(SINGLES) - seen
    if missing:
        raise SystemExit(f"singles not found in DB: {sorted(missing)}")

    sqls, n = ["BEGIN;"], 0
    for did, (name, old, new, has_music) in sorted(plan.items()):
        if old == new:
            continue
        n += 1
        print(f"{did}\t{name}\t{old} -> {new}")
        sqls.append(f'UPDATE "DanceStyles" SET "StyleId"={STYLE[new]} WHERE "DanceId"={did};')
        mu = MUSIC[new]
        if mu is None:
            if has_music:
                sqls.append(f'DELETE FROM "DanceMusicalStyles" WHERE "DanceId"={did};')
        elif has_music:
            sqls.append(f'UPDATE "DanceMusicalStyles" SET "MusicalStyleId"={mu} WHERE "DanceId"={did};')
        else:
            sqls.append(f'INSERT INTO "DanceMusicalStyles" ("DanceId","MusicalStyleId") VALUES ({did},{mu});')
    sqls.append("COMMIT;" if apply else "ROLLBACK;")
    print(f"\n{n} dances to retag; {'APPLYING' if apply else 'dry-run (rollback)'}")
    if n:
        psql("\n".join(sqls))
        print("done")


if __name__ == "__main__":
    main()
