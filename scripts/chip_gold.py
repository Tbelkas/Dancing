"""
chip_gold.py — the eval set. Without this, "the chips got better" is unfalsifiable.

    python scripts/chip_gold.py select [--n 30]   pick a stratified set, write stubs
    python scripts/chip_gold.py status            how much is reviewed
    python scripts/chip_gold.py baseline          score today's prod chips against gold
    python scripts/chip_gold.py score <file.json> score a candidate run against gold

Gold entries live in _proto/gold/<vid>.json, prefilled with whatever prod has now so
reviewing means correcting rather than authoring from scratch. An entry only counts
once "reviewed": true — a stub scored against itself would report a perfect 1.0 and
tell you nothing.

Metric: boundary F1 at +/-TOL seconds, plus a token-overlap proxy for label quality.
The trivial t=0 boundary is excluded from both sides; every chip set has it, and
counting it inflates F1 by a flat margin that hides real movement.
"""
import argparse
import json
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO = os.path.join(ROOT, "_proto")
GOLD = os.path.join(PROTO, "gold")
HEALTH = os.path.join(PROTO, "chip_health.json")

TOL = 3  # seconds; a boundary this close to a gold boundary counts as a hit

STOP = {"the", "a", "an", "and", "to", "of", "with", "for", "your", "you", "it",
        "in", "on", "into", "up", "&"}


# ------------------------------------------------------------ signal detection

def signal_of(r):
    """What text signal exists for this video: chapters / captions / none / nonyt."""
    if r["platform"] != "youtube":
        return "nonyt"
    meta = os.path.join(PROTO, f"{r['ytid']}.json")
    if os.path.exists(meta):
        try:
            d = json.load(open(meta, encoding="utf-8"))
        except (OSError, ValueError):
            d = {}
        if len(d.get("chapters") or []) >= 3:
            return "chapters"
        auto = (d.get("automatic_captions") or {})
        subs = (d.get("subtitles") or {})
        if any(k.startswith("en") for k in list(auto) + list(subs)):
            return "captions"
        return "none"
    vtt = glob.glob(os.path.join(PROTO, f"sub_{r['ytid']}.*.vtt"))
    if vtt and sum(1 for l in open(vtt[0], encoding="utf-8", errors="ignore")
                   if "-->" in l) >= 20:
        return "captions"
    return "unknown"


def channel_of(r):
    """Who made it. Capping per channel stops the eval from measuring how well we
    reproduce one creator's chaptering habits instead of chaptering in general."""
    meta = os.path.join(PROTO, f"{r['ytid']}.json")
    if os.path.exists(meta):
        try:
            d = json.load(open(meta, encoding="utf-8"))
            ch = d.get("channel") or d.get("uploader") or d.get("uploader_id")
            if ch:
                return "ch:" + str(ch).strip().lower()
        except (OSError, ValueError):
            pass
    # "How to Moonwalk ... | Mihran Kirakosian" -> the trailing credit is the channel
    m = re.search(r"[|–—]\s*([^|–—]{3,40})\s*$", r.get("title") or "")
    if m:
        return "t:" + m.group(1).strip().lower()
    return f"v:{r['vid']}"  # unknown: unique, so it never triggers the cap


MAX_PER_CHANNEL = 2


def bucket_of(r):
    if not r["n"]:
        return "none"
    if r["score"] < 0.35:
        return "poor"
    if r["score"] < 0.65:
        return "weak"
    return "ok"


# ------------------------------------------------------------------- selection

QUOTA = {"none": 8, "poor": 7, "weak": 8, "ok": 7}


def cmd_select(args):
    health = json.load(open(HEALTH, encoding="utf-8"))
    rows = health["videos"]
    for r in rows:
        r["bucket"] = bucket_of(r)
        r["signal"] = signal_of(r)

    quota = dict(QUOTA)
    if args.n != 30:
        scale = args.n / 30
        quota = {k: max(1, round(v * scale)) for k, v in quota.items()}

    picked, seen_yt, chan = [], set(), {}
    for b, want in quota.items():
        pool = [r for r in rows if r["bucket"] == b]
        # Group by signal so the set doesn't end up all-chapters, then round-robin
        # the highest-priority video from each signal group until the quota is met.
        groups = {}
        for r in sorted(pool, key=lambda x: -x["priority"]):
            groups.setdefault(r["signal"], []).append(r)
        order = sorted(groups, key=lambda k: -len(groups[k]))
        took = 0
        while took < want and any(groups[k] for k in order):
            for k in order:
                if took >= want:
                    break
                while groups[k]:
                    r = groups[k].pop(0)
                    if r["ytid"] in seen_yt:
                        continue  # same source clip twice teaches nothing
                    c = channel_of(r)
                    if chan.get(c, 0) >= MAX_PER_CHANNEL:
                        continue
                    seen_yt.add(r["ytid"])
                    chan[c] = chan.get(c, 0) + 1
                    r["channel"] = c
                    picked.append(r)
                    took += 1
                    break
    os.makedirs(GOLD, exist_ok=True)

    fresh = 0
    for r in picked:
        path = os.path.join(GOLD, f"{r['vid']}.json")
        if os.path.exists(path):
            continue
        segs = prod_sections(r["vid"])
        json.dump({
            "vid": r["vid"], "ytid": r["ytid"], "platform": r["platform"],
            "title": r["title"], "dance": r["dance"], "dur": r["dur"],
            "views": r["views"], "bucket": r["bucket"], "signal": r["signal"],
            "reviewed": False,
            "note": "",
            "prefilled_from": "prod" if segs else "empty",
            "sections": segs,
        }, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        fresh += 1

    manifest = [{k: r[k] for k in
                 ("vid", "ytid", "title", "dance", "dur", "views", "bucket", "signal")}
                for r in picked]
    json.dump(manifest, open(os.path.join(GOLD, "_manifest.json"), "w",
                             encoding="utf-8"), indent=1, ensure_ascii=False)

    print(f"selected {len(picked)} videos ({fresh} new stubs) -> {GOLD}")
    by_b, by_s = {}, {}
    for r in picked:
        by_b[r["bucket"]] = by_b.get(r["bucket"], 0) + 1
        by_s[r["signal"]] = by_s.get(r["signal"], 0) + 1
    print("  by health tier:", "  ".join(f"{k}={v}" for k, v in by_b.items()))
    print("  by signal     :", "  ".join(f"{k}={v}" for k, v in by_s.items()))
    print(f"  distinct channels: {len({r.get('channel') for r in picked})} "
          f"(cap {MAX_PER_CHANNEL}/channel)")
    print(f"\n  {'vid':>5}  {'tier':<5} {'signal':<9} {'dur':>5} {'views':>11}  title")
    for r in picked:
        print(f"  {r['vid']:>5}  {r['bucket']:<5} {r['signal']:<9} {r['dur']:>5} "
              f"{r['views']:>11,}  {(r['title'] or r['dance'])[:52]}")


def prod_sections(vid):
    """Current prod chips for one video, from the health snapshot's source data."""
    return _prod_map().get(vid, [])


_PROD = None


def _prod_map():
    """vid -> [{start,end,label}] straight from the DB, for prefill and baseline."""
    global _PROD
    if _PROD is None:
        import chip_health as ch
        raw = ch.psql("""
        select coalesce(json_agg(row_to_json(t)), '[]'::json) from (
          select s."VideoId" as "vid", s."StartTime" as "start",
                 s."EndTime" as "end", s."Label" as "label"
          from "VideoSegments" s order by s."VideoId", s."StartTime", s."Id"
        ) t;""")
        _PROD = {}
        for row in json.loads(raw.strip() or "[]"):
            _PROD.setdefault(row["vid"], []).append(
                {"start": row["start"], "end": row["end"], "label": row["label"]})
    return _PROD


# --------------------------------------------------------------------- scoring

def _starts(sections):
    """Boundary starts, excluding the trivial 0 that every chip set has."""
    return sorted({s["start"] for s in sections if s["start"] > TOL})


def _toks(label):
    return {w for w in re.findall(r"[a-z0-9']+", (label or "").lower())
            if w not in STOP}


def boundary_f1(pred, gold, tol=TOL):
    """Greedy 1-1 match of predicted boundaries to gold within tol seconds."""
    p, g = _starts(pred), _starts(gold)
    if not p and not g:
        return 1.0, 1.0, 1.0, 0
    unused = list(g)
    hits = 0
    for t in p:
        best, bd = None, tol + 1
        for u in unused:
            d = abs(u - t)
            if d <= tol and d < bd:
                best, bd = u, d
        if best is not None:
            unused.remove(best)
            hits += 1
    prec = hits / len(p) if p else 0.0
    rec = hits / len(g) if g else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return f1, prec, rec, hits


def label_overlap(pred, gold, tol=TOL):
    """Token-F1 of labels on boundaries that matched. A cheap proxy for the judge:
    it rewards naming the same move, not identical phrasing."""
    gmap = {s["start"]: s.get("label", "") for s in gold}
    scores = []
    for s in pred:
        if s["start"] <= TOL:
            continue
        near = [gs for gs in gmap if abs(gs - s["start"]) <= tol]
        if not near:
            continue
        gl = _toks(gmap[min(near, key=lambda x: abs(x - s["start"]))])
        pl = _toks(s.get("label", ""))
        if not gl and not pl:
            scores.append(1.0)
            continue
        inter = len(gl & pl)
        if not inter:
            scores.append(0.0)
            continue
        prec, rec = inter / len(pl), inter / len(gl)
        scores.append(2 * prec * rec / (prec + rec))
    return sum(scores) / len(scores) if scores else 0.0


def load_gold(reviewed_only=True):
    out = {}
    for p in glob.glob(os.path.join(GOLD, "*.json")):
        if os.path.basename(p).startswith("_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        if reviewed_only and not d.get("reviewed"):
            continue
        out[d["vid"]] = d
    return out


def evaluate(candidate, gold, title):
    """candidate: vid -> [sections]. Prints a per-video table and the aggregate."""
    if not gold:
        print("No reviewed gold entries yet — nothing to score against.")
        print("Mark an entry with \"reviewed\": true once its sections are correct.")
        return
    print(f"\n{title}   (tolerance +/-{TOL}s, t=0 boundary excluded)")
    print(f"  {'vid':>5}  {'F1':>5} {'prec':>5} {'rec':>5}  {'label':>5}  "
          f"{'pred':>4} {'gold':>4}  tier")
    fs, ls = [], []
    for vid, g in sorted(gold.items()):
        pred = candidate.get(vid, [])
        f1, pr, rc, _ = boundary_f1(pred, g["sections"])
        lo = label_overlap(pred, g["sections"])
        fs.append(f1)
        ls.append(lo)
        print(f"  {vid:>5}  {f1:>5.2f} {pr:>5.2f} {rc:>5.2f}  {lo:>5.2f}  "
              f"{len(pred):>4} {len(g['sections']):>4}  {g.get('bucket','')}")
    n = len(fs)
    print(f"\n  videos scored : {n}")
    print(f"  boundary F1   : {sum(fs)/n:.3f}")
    print(f"  label overlap : {sum(ls)/n:.3f}")


def cmd_status(args):
    all_g = load_gold(reviewed_only=False)
    done = [d for d in all_g.values() if d.get("reviewed")]
    print(f"gold entries: {len(all_g)}   reviewed: {len(done)}   "
          f"remaining: {len(all_g) - len(done)}")
    if all_g:
        by = {}
        for d in all_g.values():
            k = (d.get("bucket"), bool(d.get("reviewed")))
            by[k] = by.get(k, 0) + 1
        for b in ("none", "poor", "weak", "ok"):
            print(f"  {b:<5} reviewed {by.get((b,True),0)} / "
                  f"{by.get((b,True),0)+by.get((b,False),0)}")
    if not done:
        print("\nNothing reviewed yet. Open the dashboard's Gold tab to chip them:")
        print("  python scripts/chip_ui.py")


def cmd_baseline(args):
    gold = load_gold()
    evaluate(_prod_map(), gold, "BASELINE — today's prod chips vs gold")


def cmd_score(args):
    cand = json.load(open(args.file, encoding="utf-8"))
    if isinstance(cand, dict) and "videos" in cand:
        cand = {v["vid"]: v.get("sections", []) for v in cand["videos"]}
    else:
        cand = {int(k): v for k, v in cand.items()}
    evaluate(cand, load_gold(), f"CANDIDATE — {os.path.basename(args.file)} vs gold")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select"); s.add_argument("--n", type=int, default=30)
    s.set_defaults(fn=cmd_select)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("baseline").set_defaults(fn=cmd_baseline)
    s = sub.add_parser("score"); s.add_argument("file"); s.set_defaults(fn=cmd_score)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
