"""
sweep.py [--videos N] [--variants a,b,c] [--samples 1]

Run several prompt variants over the same eval videos and score each against gold,
so the next prompt is chosen from evidence instead of taste.

    python scripts/sweep.py --videos 40          all variants, 40 videos each

Why this exists: the first real run scored F1 0.302 against a prod baseline of
0.449, and the diagnosis was over-segmentation - median 12 sections proposed
against 6 in gold, 30 of 58 videos over-segmenting by more than 1.5x. Precision
collapses and takes F1 with it. Every variant below is a different answer to
"how coarse should a section be", plus one control.

Writes _proto/sweep/<variant>/prop_<ytid>.json and _proto/sweep_results.json.
Touches NOTHING in the database.

COST: one `claude -p` call per video per variant. 5 variants x 40 videos = 200
calls on the Claude Code subscription. Honours the dashboard's Pause button.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import chip_runstate as rs  # noqa: E402
import candidates as cd  # noqa: E402
import chip_gold as cg  # noqa: E402
import propose as pr  # noqa: E402

SWEEP = os.path.join(rs.PROTO, "sweep")
RESULTS = os.path.join(rs.PROTO, "sweep_results.json")

# secs_per_section: how coarse to aim. The control uses 90, which produced ~2x
# the sections a creator writes. extra: additional guidance appended to RULES.
VARIANTS = {
    "control": {
        "secs": 90,
        "extra": "",
    },
    "coarse120": {
        "secs": 120,
        "extra": "",
    },
    "coarse150": {
        "secs": 150,
        "extra": "",
    },
    "major-phases": {
        "secs": 150,
        "extra": (
            "- Prefer FEWER, larger sections. A section is a major phase of the "
            "lesson - a whole move taught start to finish, a drill, a run-through "
            "- not every new detail or count within one move.\n"
            "- If two adjacent candidates teach parts of the SAME move, choose only "
            "the first.\n"
            "- A viewer should be able to scan your list in one glance and know how "
            "the lesson is structured."
        ),
    },
    "strong-signals": {
        "secs": 120,
        "extra": (
            "- Strongly prefer candidates with a HIGH strength score; they have "
            "several independent signals agreeing. A low-strength candidate is a "
            "guess unless the transcript clearly starts a new topic there.\n"
            "- Leave at least 60 seconds between sections unless the transcript "
            "plainly shows a new move starting sooner."
        ),
    },
}


def build_prompt(ytid, sig, cand, dance, variant):
    """pr.build_prompt with the variant's density and extra rules applied."""
    v = VARIANTS[variant]
    dur = sig.get("dur") or 0
    base = dict(cand)
    base["suggested_sections"] = max(3, min(14, round((dur or 300) / v["secs"])))
    prompt = pr.build_prompt(ytid, sig, base, dance)
    if v["extra"]:
        prompt = prompt.replace(
            "- Sections should be at least ~15s apart.",
            "- Sections should be at least ~15s apart.\n" + v["extra"])
    return prompt


def run_all(variants, ytids, names):
    """Interleave: every variant on video 1, then video 2, and so on.

    Variant-major order is what wrecked the 06:00 run - it spent the whole quota
    on `control`, the one variant already known to lose, and left the other four
    with nothing. Video-major means a run cut short still compares every variant
    on the same prefix of videos, which is the only thing that makes the numbers
    comparable at all.
    """
    made, stopped, reason = 0, False, ""
    for ytid in ytids:
        if stopped:
            break
        sig = rs._read(cd.sig_path(ytid), None)
        cand = rs._read(cd.cand_path(ytid), None)
        if not sig or not cand or not cand.get("candidates"):
            continue
        for variant in variants:
            if not rs.wait_if_paused():
                return made, True, "paused"
            outdir = os.path.join(SWEEP, variant)
            os.makedirs(outdir, exist_ok=True)
            dest = os.path.join(outdir, f"prop_{ytid}.json")
            if os.path.exists(dest):
                continue
            rs.begin(ytid=ytid, stage=variant)
            try:
                prompt = build_prompt(ytid, sig, cand, names.get(ytid), variant)
                secs = pr.parse_sections(pr.call_claude(prompt), cand)
                json.dump({"ytid": ytid, "variant": variant, "sections": secs},
                          open(dest, "w", encoding="utf-8"), ensure_ascii=False)
                made += 1
                rs.done_one(ok=True, msg=f"{variant}/{ytid}: {len(secs)} sections")
            except pr.QuotaExhausted as e:
                # Stop dead. Continuing just burns failing calls and reports success.
                rs.done_one(ok=False, msg=f"QUOTA EXHAUSTED: {e}")
                return made, True, f"quota exhausted: {e}"
            except Exception as e:  # noqa: BLE001
                rs.done_one(ok=False, msg=f"{variant}/{ytid} failed: {type(e).__name__}")
    return made, stopped, reason


def score_variant(variant, gold_by_vid, ytid_to_vid, restrict=None):
    outdir = os.path.join(SWEEP, variant)
    if not os.path.isdir(outdir):
        return None
    cand = {}
    for name in os.listdir(outdir):
        if not name.startswith("prop_"):
            continue
        ytid = name[5:-5]
        vid = ytid_to_vid.get(ytid)
        d = rs._read(os.path.join(outdir, name), None)
        if restrict is not None and ytid not in restrict:
            continue
        if vid in gold_by_vid and d and d.get("sections"):
            cand[vid] = d["sections"]
    if not cand:
        return None
    f1s, labs, ratios = [], [], []
    for vid, secs in cand.items():
        g = gold_by_vid[vid]
        f1, _, _, _ = cg.boundary_f1(secs, g["sections"])
        f1s.append(f1)
        labs.append(cg.label_overlap(secs, g["sections"]))
        if g["sections"]:
            ratios.append(len(secs) / len(g["sections"]))
    n = len(f1s)
    return {"variant": variant, "n": n,
            "f1": round(sum(f1s) / n, 3),
            "label": round(sum(labs) / n, 3),
            "size_ratio": round(sum(ratios) / len(ratios), 2) if ratios else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", type=int, default=40)
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--samples", type=int, default=1)
    args = ap.parse_args()

    wanted = [v.strip() for v in args.variants.split(",") if v.strip() in VARIANTS]
    gold_entries = cd.gold_entries()
    gold_by_vid = cg.load_gold()
    ytid_to_vid = {y: e["vid"] for y, e in gold_entries.items() if e.get("vid")}

    # Same videos for every variant, or the comparison means nothing.
    ytids = sorted(y for y, e in gold_entries.items()
                   if e.get("vid") in gold_by_vid
                   and os.path.exists(cd.cand_path(y))
                   and os.path.exists(cd.sig_path(y)))[:args.videos]

    calls = len(ytids) * len(wanted)
    print(f"sweep: {len(wanted)} variant(s) x {len(ytids)} videos = {calls} claude -p calls")
    print("variants:", ", ".join(wanted))

    names = pr.dance_names()
    rs.start_run("sweep", total=calls)
    t0 = time.time()
    made, stopped, reason = run_all(wanted, ytids, names)
    rs.finish()
    print(f"  {made} proposal(s) in {time.time()-t0:.0f}s"
          + (f"  STOPPED: {reason}" if stopped else ""))
    if stopped and "quota" in reason:
        print("  -> re-run when the window resets; finished proposals are cached")

    # Score every variant on the SAME videos - the ones all of them completed.
    # Without this a variant that ran on 33 videos is compared against one that
    # ran on 12, and the numbers mean nothing.
    done = []
    for v in wanted:
        d = os.path.join(SWEEP, v)
        done.append({n[5:-5] for n in os.listdir(d)} if os.path.isdir(d) else set())
    common = set.intersection(*done) if done else set()
    print()
    print("scoring on the " + str(len(common)) + " video(s) every variant completed")
    rows = [r for r in (score_variant(v, gold_by_vid, ytid_to_vid, common)
                        for v in wanted) if r]
    rows.sort(key=lambda r: -r["f1"])
    json.dump({"generated": rs._now(), "rows": rows},
              open(RESULTS, "w", encoding="utf-8"), indent=1)

    print(f"\n{'variant':<16} {'n':>4} {'F1':>7} {'label':>7} {'size vs gold':>13}")
    for r in rows:
        print(f"{r['variant']:<16} {r['n']:>4} {r['f1']:>7.3f} {r['label']:>7.3f} "
              f"{r['size_ratio']:>13.2f}x")
    print("\nprod baseline on the informative subset: F1 0.449 / label 0.514")
    print("A variant only matters if it beats that AND its size ratio is near 1.0.")
    print(f"\nwrote {RESULTS}")


if __name__ == "__main__":
    main()
