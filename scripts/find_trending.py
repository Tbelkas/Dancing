"""
find_trending.py [--per-style N] [--min-channels 2] [--min-views N] [apply]

Find dance moves that are trending on YouTube and are NOT in the catalogue yet.

    python scripts/find_trending.py                 dry run, show the proposals
    python scripts/find_trending.py --per-style 12  cast wider
    python scripts/find_trending.py apply           insert as PENDING dances

find_videos.py answers "another way to teach a move we already have". This answers
the other half: what are people learning right now that we do not carry at all.

THE HARD PART IS NOT SEARCHING, IT IS NAMING
--------------------------------------------
Pulling trending dance tutorials is a single yt-dlp call. Turning their titles into
dance NAMES is where the 2026-06 seeding runs produced hundreds of entries that had
to be deleted by hand - "Practice with Music", "How to Enroll?", "1st Position",
instructor names, raw movement instructions. Every one of those came from trusting a
string that sat where a move name should be.

So the test here is not a cleverer regex. It is CORROBORATION:

    a real move is taught by more than one person

A move that is genuinely trending has several creators making tutorials for it, on
separate channels, within the same search. A phrase that merely occupies the same slot
in one title - "My New Routine", "Practice with Music" - appears once, from one
channel, and never again. --min-channels is therefore the primary quality gate, and it
is doing the job the blocklist could never do reliably, because it does not depend on
having anticipated the specific junk phrase.

The blocklist below is still applied, but as a cheap pre-filter, not as the guarantee.

WHAT GETS WRITTEN
-----------------
Nothing reaches the public catalogue. Dances are inserted with ReviewState='pending'
EXPLICITLY - note that "Dances"."ReviewState" defaults to 'approved', the opposite of
"Videos", so a raw insert that forgets the column goes straight live. Their videos are
inserted too, and those do default to pending. Both need promoting by hand, and the
videos should go through verify_intake.py first like any other intake batch.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import chip_health as ch  # noqa: E402
import video_gate as vg   # noqa: E402

OUT = os.path.join(ch.ROOT, "_proto", "trending.json")

MIN_DUR, MAX_DUR = 45, 3600

# Query shapes. "2026" and "new" bias the ranking toward recent uploads without
# needing a date filter, which ytsearch does not expose usefully.
STYLE_QUERIES = [
    "new {style} dance moves 2026 tutorial",
    "{style} dance tutorial 2026",
    "trending {style} dance move tutorial",
]
GLOBAL_QUERIES = [
    "viral dance tutorial 2026",
    "tiktok dance move tutorial 2026",
    "new dance move tutorial 2026",
    "trending dance challenge tutorial 2026",
    "how to do the new dance 2026",
]

# Where a move name sits in a tutorial title. Ordered most to least reliable.
NAME_PATS = [
    re.compile(r"how to (?:do|dance|hit)? ?(?:the )?[\"']?([^|\-\(\)\[\]\"':]{2,34})", re.I),
    re.compile(r"learn (?:the |how to do the )?[\"']?([^|\-\(\)\[\]\"':]{2,34})", re.I),
    re.compile(r"[\"']([^\"']{2,34})[\"']\s*(?:dance|move|tutorial|challenge)", re.I),
    re.compile(r"^([^|\-\(\)\[\]]{2,34})\s*(?:dance )?tutorial", re.I),
]

# Trailing noise that clings to an extracted name.
TAIL = re.compile(
    r"\b(dance|dancing|tutorial|tutorials|move|moves|step|steps|challenge|for"
    r"|beginners|beginner|easy|slow|mirrored|explained|breakdown|part|pt|ep"
    r"|in|with|to|and|the|a|an|2024|2025|2026)\b\s*$", re.I)

# The junk classes documented in seeding-pitfalls. Cheap pre-filter only - the real
# guarantee is --min-channels.
BLOCK = [
    re.compile(r"^\d+ .+ mistake$", re.I),
    re.compile(r"^(practice with|what is|how to enroll|lesson preview|recap"
               r"|breakdown|demo|intro|outro|warm ?up|conclusion)\b", re.I),
    re.compile(r"^(sec|level|part|chapter|day|week|class|lesson|combo|routine)\s*\d*$", re.I),
    re.compile(r"^\d{1,2}(st|nd|rd|th)? position$", re.I),
    re.compile(r"^[a-z] (slide|step|turn)( ?\d+)?$", re.I),
    # Single generic words are never a move on their own.
    re.compile(r"^(step|walk|close|rock|arms|slide|bounce|sway|tap|glide|move"
               r"|dance|dancing|music|song|beat|body|feet|hands)$", re.I),
    # A sentence, not a name.
    re.compile(r"\b(your|you|my|i|we|they|this|that|these|it's|its|here|there)\b", re.I),
    re.compile(r"[?!]"),
    # Channel/brand furniture.
    re.compile(r"\b(subscribe|patreon|instagram|tiktok|shorts|vlog|reaction)\b", re.I),
]

GENERIC_STYLE_WORD = re.compile(
    r"^(hip ?hop|house|vogue|waacking|krump|tutting|shuffle|salsa|bachata|swing"
    r"|ballet|jazz|tap|contemporary|afrobeats?|amapiano|dancehall|k-?pop|twerk"
    r"|heels|litefeet|reggaeton|soca|kizomba|bhangra|flamenco|breakdanc\w*"
    r"|line danc\w*|ballroom|latin)$", re.I)


def clean_name(raw):
    """Normalise an extracted string, or return None if it is not a name."""
    n = (raw or "").strip()
    n = re.sub(r"\s+", " ", n)
    # Pitfall 6: strip a leading ordinal ONLY when punctuation follows, so that
    # "6 Step" and "7 Step" survive but "1. Running Man" loses the "1.".
    n = re.sub(r"^\d+[\.\):\-]\s*", "", n)
    n = n.strip(" -–—:|.,\"'")
    # "Robot aka Botting" is one move under two names, not a move called both.
    n = re.split(r"\s+(?:aka|a\.k\.a\.?|or)\s+", n, maxsplit=1, flags=re.I)[0]
    # A surviving leading count is a video's inventory, not a name: "LEARN 3 HIP HOP
    # GROOVES" is three moves. Keep "6 Step" and "7 Step", which really are named
    # after the number - the giveaway is that nothing but one word follows.
    m = re.match(r"^(\d+)\s+(.+)$", n)
    if m and len(m.group(2).split()) > 1:
        return None
    # Peel repeated trailing noise, but never a peel that destroys the name. "step"
    # is noise in "Griddy Dance Step" and load-bearing in "6 Step", and the only
    # difference visible here is what survives it.
    prev = None
    while prev != n:
        prev = n
        cand = TAIL.sub("", n).strip(" -–—:|.,\"'")
        if len(cand) < 2 or not re.search(r"[A-Za-z]", cand):
            break
        n = cand
    if not (2 <= len(n) <= 34):
        return None
    words = n.split()
    if not (1 <= len(words) <= 4):
        return None
    if not re.search(r"[A-Za-z]", n):
        return None
    if GENERIC_STYLE_WORD.match(n):       # "Hip Hop" is a style, not a move
        return None
    for b in BLOCK:
        if b.search(n):
            return None
    return " ".join(w if w.isupper() and len(w) <= 4 else w.capitalize()
                    for w in words)


def search(query, n):
    p = subprocess.run(
        ["yt-dlp", f"ytsearch{n}:{query}", "--flat-playlist", "--no-warnings", "-q",
         "--print", "%(id)s\t%(duration)s\t%(view_count)s\t%(channel_id)s\t"
                    "%(channel)s\t%(title)s"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=240)
    out = []
    for line in (p.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) != 6:
            continue
        vid, dur, views, chid, chan, title = parts
        try:
            out.append({"ytid": vid, "dur": int(float(dur or 0)),
                        "views": int(float(views or 0)), "channel_id": chid,
                        "channel": chan, "title": title})
        except ValueError:
            continue
    return out


def extract(title):
    for pat in NAME_PATS:
        m = pat.search(title)
        if m:
            n = clean_name(m.group(1))
            if n:
                return n
    return None


def existing_names():
    raw = ch.psql('select coalesce(json_agg("Name"), \'[]\'::json) from "Dances";')
    names = json.loads(raw.strip() or "[]")
    # Pitfall 4: compare case- and punctuation-insensitively, because the API's
    # duplicate check only catches an exact slug match.
    return {re.sub(r"[^a-z0-9]+", "", (n or "").lower()) for n in names}


def slugify(n):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", n.lower())).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apply", nargs="?")
    ap.add_argument("--per-style", type=int, default=10)
    ap.add_argument("--per-global", type=int, default=25)
    ap.add_argument("--min-channels", type=int, default=2)
    ap.add_argument("--min-views", type=int, default=5000)
    ap.add_argument("--styles", help="comma-separated subset, default all")
    args = ap.parse_args()

    styles = json.loads(ch.psql(
        'select coalesce(json_agg(row_to_json(t)), \'[]\'::json) from '
        '(select "Id" as id, "Name" as name from "Styles" order by "Name") t;'
    ).strip() or "[]")
    if args.styles:
        want = {s.strip().lower() for s in args.styles.split(",")}
        styles = [s for s in styles if s["name"].lower() in want]

    queries = [(None, q) for q in GLOBAL_QUERIES]
    for s in styles:
        for tpl in STYLE_QUERIES:
            queries.append((s, tpl.format(style=s["name"])))

    print(f"{len(queries)} search(es) over {len(styles)} style(s)")

    # name -> evidence
    hits = defaultdict(lambda: {"videos": [], "channels": set(), "styles": defaultdict(int)})
    seen_vid = set()
    for i, (style, q) in enumerate(queries, 1):
        n = args.per_global if style is None else args.per_style
        try:
            res = search(q, n)
        except subprocess.TimeoutExpired:
            print(f"  [{i}/{len(queries)}] timeout: {q}")
            continue
        for r in res:
            if not (MIN_DUR <= r["dur"] <= MAX_DUR) or r["views"] < args.min_views:
                continue
            name = extract(r["title"])
            if not name:
                continue
            h = hits[name]
            if r["ytid"] not in seen_vid:
                seen_vid.add(r["ytid"])
            h["videos"].append(r)
            h["channels"].add(r["channel_id"])
            if style:
                h["styles"][style["name"]] += 1
        if i % 10 == 0:
            print(f"  [{i}/{len(queries)}] {len(hits)} distinct name(s) so far")
        time.sleep(0.3)

    known = existing_names()
    props, rejected = [], []
    for name, h in hits.items():
        flat = re.sub(r"[^a-z0-9]+", "", name.lower())
        if flat in known:
            rejected.append({"name": name, "why": "already-in-catalogue",
                             "channels": len(h["channels"])})
            continue
        if len(h["channels"]) < args.min_channels:
            # Kept in the output on purpose: a name one channel short is the most
            # interesting thing here, because it is either a move that has not
            # spread yet or a title phrase that never will, and only a human
            # glancing at the list can tell which.
            rejected.append({"name": name, "why": "too-few-channels",
                             "channels": len(h["channels"]),
                             "reach": sum(v["views"] for v in h["videos"]),
                             "style": (max(h["styles"].items(),
                                           key=lambda kv: kv[1])[0]
                                       if h["styles"] else None),
                             "example": h["videos"][0]["title"][:90]})
            continue
        best = max(h["videos"], key=lambda v: v["views"])
        style = (max(h["styles"].items(), key=lambda kv: kv[1])[0]
                 if h["styles"] else None)
        props.append({
            "name": name, "slug": slugify(name), "style": style,
            "channels": len(h["channels"]), "videos": len(h["videos"]),
            "reach": sum(v["views"] for v in h["videos"]),
            "best": best,
            "all": [{"ytid": v["ytid"], "title": v["title"], "views": v["views"],
                     "dur": v["dur"], "channel": v["channel"]} for v in h["videos"]],
        })
    props.sort(key=lambda p: (-p["channels"], -p["reach"]))

    rejected.sort(key=lambda r: -r.get("reach", 0))
    json.dump({"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "proposals": props,
               "rejected": rejected},
              open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    nre = sum(1 for r in rejected if r["why"] == "already-in-catalogue")
    print(f"\nfiltered: {nre} already in the catalogue, "
          f"{len(rejected) - nre} short of --min-channels")

    print(f"\n{len(hits)} distinct name(s) seen, {len(props)} new to the catalogue "
          f"and taught by >= {args.min_channels} channel(s)")
    print(f"  {'ch':>3} {'vids':>4} {'reach':>11}  {'style':<14} name")
    for p in props[:40]:
        print(f"  {p['channels']:>3} {p['videos']:>4} {p['reach']:>11,}  "
              f"{(p['style'] or '?')[:12]:<14} {p['name']}")
    print(f"\nwrote {OUT}")

    if args.apply != "apply":
        print("dry run - pass 'apply' to insert them as PENDING dances")
        return
    insert(props)


def insert(props):
    if not props:
        return
    style_ids = {r["name"]: r["id"] for r in json.loads(ch.psql(
        'select coalesce(json_agg(row_to_json(t)), \'[]\'::json) from '
        '(select "Id" as id, "Name" as name from "Styles") t;').strip() or "[]")}
    made = 0
    for p in props:
        name = p["name"].replace("'", "''")
        slug = p["slug"]
        # ReviewState is named EXPLICITLY: the column defaults to 'approved', so a
        # raw insert that omits it publishes an unreviewed dance immediately.
        got = ch.psql(f"""
            insert into "Dances"("Name","Slug","Description","DateAdded",
                                 "Difficulty","ReviewState")
            values ('{name}','{slug}', null, now(), 0, 'pending')
            on conflict do nothing
            returning "Id";""").strip()
        did = next((ln for ln in got.splitlines() if ln.strip().isdigit()), None)
        if not did:
            continue
        did = int(did)
        made += 1
        sid = style_ids.get(p["style"] or "")
        if sid:
            ch.psql(f'''insert into "DanceStyles"("DanceId","StyleId")
                        values ({did},{sid}) on conflict do nothing;''')
        for v in p["all"][:3]:
            title = v["title"].replace("'", "''")[:300]
            ch.psql(f"""
            insert into "Videos"("Title","VideoId","Platform","VideoType","DateAdded",
                                 "ViewCount","DurationSeconds","DanceId")
            values ('{title}','{v["ytid"]}','youtube','tutorial', now(),
                    {v["views"]}, {v["dur"]}, {did});""")
    print(f"inserted {made} dance(s), all ReviewState='pending'")
    print(ch.psql('''select "ReviewState", count(*) from "Dances"
                     group by 1 order by 2 desc;''').strip())


if __name__ == "__main__":
    main()
