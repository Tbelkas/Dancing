"""
audit_labels.py [--fetch-missing]
Audit dance style labels against the REAL YouTube titles of their videos.
The DB Video.Title stores the move name, so a mis-styled dance (e.g. a
dancehall tutorial filed under Waacking) is invisible from the DB alone.

- Pulls dance id/name/slug/style + each video's ytid/platform/StartTime.
- Real YT title comes from _proto/<ytid>.json (yt-dlp cache); optionally
  fetches missing ones via YouTube oembed with --fetch-missing.
- Flags rows where the YT title (or its channel/tags) clearly names a
  DIFFERENT style than the dance's tag.
Writes _proto/label_audit.tsv (all rows) and prints flagged ones.
Detection only — never writes to the DB.
"""
import json, os, re, subprocess, sys, urllib.request
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
PROTO = os.path.join(ROOT, "_proto")
OUT = os.path.join(PROTO, "label_audit.tsv")


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
                        "-At", "-F", "\t"],
                       input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr); raise SystemExit(2)
    return [l.split("\t") for l in p.stdout.splitlines() if l]


# Style keyword signatures. A title hit on style X while the dance is tagged Y
# (and Y's own keywords are absent) = flagged.
SIGS = {
    "Waacking":       [r"\bwaack", r"\bwhack"],
    "Vogue":          [r"\bvogu", r"\bvoguing", r"\bball(room)? culture"],
    "Dancehall":      [r"\bdancehall", r"\bragga", r"\breggae danc"],
    "Hip-hop":        [r"\bhip[ -]?hop"],
    # \bbreak(danc|ing)\b never matched the word "breakdance" itself (the \b
    # fails on the trailing "e"), so breaking clips read as having no style.
    "Breakdance":     [r"\bbreakdanc", r"\bbreakin", r"\bbboy", r"\bb-boy"],
    "House":          [r"\bhouse danc"],
    "Popping":        [r"\bpopping\b", r"\bpoppin\b"],
    "Locking":        [r"\block(ing|in)\b"],
    "Krump":          [r"\bkrump"],
    "Ballet":         [r"\bballet\b"],
    "Contemporary":   [r"\bcontemporary\b", r"\blyrical\b"],
    "Jazz":           [r"\bjazz\b"],
    "Tap":            [r"\btap danc", r"\btap tutorial", r"\btap steps"],
    "Salsa":          [r"\bsalsa\b"],
    "Bachata":        [r"\bbachata\b"],
    "Kizomba":        [r"\bkizomba\b"],
    "Tango":          [r"\btango\b"],
    "Ballroom":       [r"\bwaltz\b", r"\bfoxtrot\b", r"\bquickstep\b", r"\bballroom\b", r"\bcha[ -]?cha\b", r"\brumba\b", r"\bsamba\b(?! reggae)", r"\bjive\b", r"\bpaso doble\b", r"\bviennese\b"],
    "Swing":          [r"\bswing\b", r"\blindy hop", r"\bcharleston\b", r"\bshag\b", r"\bbalboa\b"],
    "K-Pop":          [r"\bk-?pop\b", r"\bkpop\b"],
    "Shuffle":        [r"\bshuffl", r"\bcutting shapes", r"\bmelbourne bounce"],
    "Litefeet":       [r"\blitefeet\b", r"\blite feet\b"],
    "Amapiano":       [r"\bamapiano\b"],
    "Afro":           [r"\bafrobeat", r"\bafro danc", r"\bafrodance", r"\bazonto\b", r"\bgwara\b", r"\bndombolo\b"],
    "Twerk":          [r"\btwerk"],
    "Heels":          [r"\bheels (danc|choreo|class|tutorial)"],
    "Reggaeton":      [r"\breggaeton\b", r"\bperreo\b"],
    "Jersey Club":    [r"\bjersey club\b"],
    "Soca":           [r"\bsoca\b"],
    "Brazilian Funk": [r"\bbrazilian funk\b", r"\bpassinho\b", r"\bfunk carioca\b"],
    "Afro House":     [r"\bafro house\b"],
    "Gqom":           [r"\bgqom\b"],
    "Stretching":     [r"\bstretch", r"\bflexib", r"\bmobility\b", r"\bsplits?\b", r"\byoga\b"],
    "Kuduro":         [r"\bkuduro\b"],
    "Flamenco":       [r"\bflamenco\b"],
    "Irish":          [r"\birish danc", r"\briverdance\b"],
    "Belly Dance":    [r"\bbelly ?danc"],
    "Bollywood":      [r"\bbollywood\b", r"\bbhangra\b"],
    "Country":        [r"\bline danc", r"\bcountry danc", r"\btwo[ -]step\b"],
    "Zumba":          [r"\bzumba\b"],
    "Disco":          [r"\bdisco\b", r"\bhustle\b"],
    "Techno":         [r"\btechno\b", r"\brave\b", r"\bhakken\b", r"\bgabber\b", r"\bjumpstyle\b"],
}

# DB style name -> the SIGS key that means the same thing. Without this the
# style's own keywords can never match its own tag, so every video of e.g. a
# "Classical / Ballet" dance whose title says "ballet" was flagged.
ALIAS = {
    "Classical / Ballet": "Ballet",
    "Afrobeats":          "Afro",
    "Bhangra":            "Bollywood",   # the DB's home for all Indian dance
}

# Styles whose umbrella covers others: a hit on the value list is NOT a
# conflict for the key style.
ALLOW = {
    "Hip-hop":       {"Popping", "Locking", "Breakdance", "Krump", "House", "Litefeet", "Jersey Club", "Twerk"},
    "Street / Urban": set(SIGS.keys()),
    "Ballroom":      {"Tango", "Swing", "Salsa", "Disco"},
    "Latin":         {"Salsa", "Bachata", "Reggaeton", "Tango", "Ballroom", "Brazilian Funk", "Soca", "Kizomba", "Zumba"},
    "Swing":         {"Jazz", "Ballroom", "Disco", "Tap"},
    "Jazz":          {"Swing", "Tap", "Ballet", "Contemporary"},
    "Contemporary":  {"Ballet", "Jazz"},
    "Ballet":        {"Contemporary", "Jazz", "Stretching"},
    "Tap":           {"Jazz", "Swing"},
    "Afro":          {"Dancehall", "Amapiano", "Afro House", "Gqom", "Kuduro", "Soca", "Brazilian Funk"},
    "Amapiano":      {"Afro", "Afro House"},
    "Afro House":    {"Afro", "Amapiano", "House"},
    "Gqom":          {"Afro"},
    "Dancehall":     {"Afro", "Reggaeton", "Twerk"},
    "House":         {"Hip-hop", "Afro House", "Shuffle"},
    "Shuffle":       {"House", "Techno"},
    "Litefeet":      {"Hip-hop"},
    "Breakdance":    {"Hip-hop"},
    "Popping":       {"Hip-hop", "Locking"},
    "Locking":       {"Hip-hop", "Popping", "Disco"},
    "Krump":         {"Hip-hop"},
    "Heels":         {"Jazz", "Contemporary", "Vogue", "Twerk", "K-Pop", "Reggaeton"},
    "Twerk":         {"Dancehall", "Hip-hop", "Brazilian Funk"},
    "K-Pop":         {"Hip-hop", "Jazz", "Heels"},
    "Vogue":         {"Waacking", "Heels"},
    "Waacking":      {"Vogue", "Disco", "Locking"},
    "Reggaeton":     {"Dancehall", "Latin", "Twerk"},
    "Stretching":    {"Ballet", "Contemporary"},
    "Salsa":         {"Latin"},
    "Bachata":       {"Latin"},
    "Kizomba":       {"Latin", "Afro"},
    "Soca":          {"Afro", "Latin", "Dancehall"},
    "Brazilian Funk": {"Latin", "Twerk"},
    "Jersey Club":   {"Hip-hop", "Litefeet"},
    "Disco":         {"Waacking", "Locking", "Ballroom"},
    # "Ballroom" in a Vogue title is the ballroom/house scene (Paris Is Burning),
    # not the ballroom-dance discipline. Every Vogue flag was this.
    "Vogue+":        {"Ballroom"},
    # Tutting is a popping sub-style, is taught inside hip-hop classes, and has
    # its own hand/wrist stretch entries.
    "Tutting":       {"Popping", "Hip-hop", "Stretching", "Breakdance"},
    # Folk / Traditional is this DB's catch-all umbrella: Irish, line/country,
    # belly dance, flamenco, Ballet Folklorico, and the African-American social
    # line dances that show up in hip-hop vocabulary montages.
    "Folk / Traditional": {"Irish", "Country", "Belly Dance", "Flamenco", "Bollywood",
                           "Ballet", "Hip-hop", "Shuffle", "Disco", "Swing", "Salsa"},
    "Bollywood":     {"Bollywood"},
    # "shuffle" is a tap step (shuffle off to Buffalo) long before it was a genre.
    "Tap+":          {"Shuffle"},
}
ALLOW["Vogue"] = ALLOW["Vogue"] | ALLOW.pop("Vogue+")
ALLOW["Tap"] = ALLOW["Tap"] | ALLOW.pop("Tap+")
# Stretch / warm-up / mobility content is style-agnostic: a "stretches for X"
# video never means the dance is filed under the wrong style.
UNIVERSAL_ALLOW = {"Stretching"}


def yt_title(ytid, fetch=False):
    p = os.path.join(PROTO, f"{ytid}.json")
    if os.path.exists(p):
        try:
            d = json.load(open(p, encoding="utf-8"))
            return d.get("title", ""), d.get("channel") or d.get("uploader") or ""
        except Exception:
            pass
    if fetch:
        try:
            u = f"https://www.youtube.com/oembed?url=https://youtu.be/{ytid}&format=json"
            d = json.load(urllib.request.urlopen(u, timeout=10))
            json.dump({"title": d.get("title", ""), "channel": d.get("author_name", ""),
                       "_src": "oembed"}, open(p, "w", encoding="utf-8"))
            return d.get("title", ""), d.get("author_name", "")
        except Exception:
            return None, None
    return None, None


def hits(text):
    t = text.lower()
    return {s for s, pats in SIGS.items() if any(re.search(p, t) for p in pats)}


def own_styles(style):
    """The set of SIGS keys that count as 'this dance's own style'."""
    return {style} | ({ALIAS[style]} if style in ALIAS else set())


def allowed_for(style):
    a = set(UNIVERSAL_ALLOW)
    for s in own_styles(style):
        a |= ALLOW.get(s, set()) | {s}
    return a


def main():
    fetch = "--fetch-missing" in sys.argv
    rows = psql('''
        SELECT d."Id", d."Name", d."Slug", s."Name", v."Id", v."VideoId",
               COALESCE(v."Platform",'youtube'), COALESCE(v."StartTime"::text,'')
        FROM "Dances" d
        JOIN "DanceStyles" ds ON ds."DanceId"=d."Id"
        JOIN "Styles" s ON s."Id"=ds."StyleId"
        JOIN "Videos" v ON v."DanceId"=d."Id"
        ORDER BY s."Name", d."Id";''')
    # Pass 1: resolve every row's title, its title-hits and its channel-hits.
    # A conflict may only be raised by the TITLE - channel names ("Brian Shuffle",
    # "2 to Tango", "line dance sl, ut", "Sleek Ballet Fitness") produce hits that
    # describe the uploader, not the clip. The channel still counts as positive
    # evidence FOR the dance's own style, which is the safe direction.
    resolved, nometa = [], 0
    corroborated = set()     # danceIds where some video confirms the tag
    for did, dname, slug, style, vid, ytid, plat, start in rows:
        if plat.lower() != "youtube":
            continue
        title, channel = yt_title(ytid, fetch)
        if title is None:
            nometa += 1
            resolved.append((did, dname, slug, style, vid, ytid, start, None, "", set(), set()))
            continue
        t_hits, c_hits = hits(title), hits(f"{title} {channel}")
        # Corroboration: this video either names the dance's own style, or its
        # style signals are all inside the tag's allowed family (e.g. a
        # "How to Breakdance ... Footwork 101" clip on a Hip-hop dance).
        if (own_styles(style) & c_hits) or (c_hits and not c_hits - allowed_for(style)):
            corroborated.add(did)
        resolved.append((did, dname, slug, style, vid, ytid, start, title, channel, t_hits, c_hits))

    # Pass 2: verdicts. The question is "is this DANCE mis-styled", not "does
    # this one clip's title name the style" - so if ANY video of the dance
    # confirms the tag, an off-brand extra video is a sourcing problem, not a
    # label problem, and is reported as EXTRA rather than MISMATCH.
    flagged, extra = [], 0
    out = open(OUT, "w", encoding="utf-8")
    out.write("danceId\tdance\tslug\tstyle\tvideoDbId\tytid\tstart\tytTitle\tchannel\ttitleStyles\tverdict\n")
    for did, dname, slug, style, vid, ytid, start, title, channel, t_hits, c_hits in resolved:
        if title is None:
            out.write(f"{did}\t{dname}\t{slug}\t{style}\t{vid}\t{ytid}\t{start}\t(no metadata)\t\t\tNOMETA\n")
            continue
        conflicts = t_hits - allowed_for(style)
        if not conflicts or own_styles(style) & c_hits:
            verdict = "ok"
        elif did in corroborated:
            verdict = "EXTRA"; extra += 1
        else:
            verdict = "MISMATCH"
            flagged.append((did, dname, slug, style, vid, ytid, start, title, sorted(conflicts)))
        out.write(f"{did}\t{dname}\t{slug}\t{style}\t{vid}\t{ytid}\t{start}\t{title}\t{channel}\t{','.join(sorted(t_hits))}\t{verdict}\n")
    out.close()
    print(f"rows={len(rows)} flagged={len(flagged)} off-style-extra-video={extra} "
          f"no-metadata={nometa}  -> {OUT}\n")
    for f in flagged:
        print(f"dance {f[0]} [{f[3]}] {f[1]} (/{f[2]})  video {f[4]} yt={f[5]} start={f[6]}\n"
              f"    YT: {f[7]}\n    title says: {', '.join(f[8])}")


if __name__ == "__main__":
    main()
