"""
score_sweep.py [--variants a,b,c] [--json PATH]

Score whatever sweep proposals are on disk, on the SAME subset the 0.449 prod
baseline was measured on.

Why this exists separately from sweep.py's own scoring: sweep.py averages F1 over
every gold video it has a proposal for, then prints "prod baseline on the
informative subset: F1 0.449" underneath it. Those two numbers are not measured on
the same videos. 37 of the 60 gold videos are "chapter-adopted" - prod copied the
creator's chapters, which is exactly what gold is, so prod scores ~0.995 there and
the honest baseline is the 23 videos where it did not. A variant scored over all 60
and compared against an informative-only baseline is being flattered by the mix.

This scores each variant twice - all videos, and the informative subset - so the
comparison against 0.449 is like for like. Read the INFORMATIVE column.

Read-only: touches no database, and does not write sweep_results.json (the running
sweep owns that file).

    python scripts/score_sweep.py
"""
import argparse
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# pythonw.exe (used to run the dashboard detached) has no stdout, and an
# unguarded reconfigure() throws on import - which surfaced as an HTTP handler
# dying with an empty response rather than an error.
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
import chip_runstate as rs  # noqa: E402
import candidates as cd  # noqa: E402
import chip_gold as cg  # noqa: E402

SWEEP = os.path.join(rs.PROTO, "sweep")


def adopted_vids(gold_by_vid):
    """The videos prod scores >=0.9 on because it copied the same chapters.

    Mirrors chip_gold.evaluate's `adopted` flag exactly: it is a property of the
    PROD chips, not of whatever we are scoring, so the subset stays fixed across
    variants and stays comparable to the published baseline.
    """
    prod = cg._prod_map()
    out = set()
    for vid, g in gold_by_vid.items():
        f1, _, _, _ = cg.boundary_f1(prod.get(vid, []), g["sections"])
        if f1 >= 0.9 and g.get("origin") == "chapters":
            out.add(vid)
    return out


def score(cand_by_vid, gold_by_vid, vids):
    """Mean boundary F1 / label overlap / size ratio over `vids`."""
    f1s, labs, ratios, counts = [], [], [], []
    for vid in vids:
        secs, g = cand_by_vid[vid], gold_by_vid[vid]
        f1, _, _, _ = cg.boundary_f1(secs, g["sections"])
        f1s.append(f1)
        labs.append(cg.label_overlap(secs, g["sections"]))
        counts.append(len(secs))
        if g["sections"]:
            ratios.append(len(secs) / len(g["sections"]))
    if not f1s:
        return None
    return {
        "n": len(f1s),
        "f1": round(sum(f1s) / len(f1s), 3),
        "label": round(sum(labs) / len(labs), 3),
        "size_ratio": round(sum(ratios) / len(ratios), 2) if ratios else None,
        "median_sections": statistics.median(counts) if counts else None,
    }


def load_variant(variant, ytid_to_vid, gold_by_vid):
    outdir = os.path.join(SWEEP, variant)
    if not os.path.isdir(outdir):
        return {}
    out = {}
    for name in os.listdir(outdir):
        if not name.startswith("prop_") or not name.endswith(".json"):
            continue
        vid = ytid_to_vid.get(name[5:-5])
        d = rs._read(os.path.join(outdir, name), None)
        if vid in gold_by_vid and d and d.get("sections"):
            out[vid] = d["sections"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants")
    ap.add_argument("--json", help="also write the rows here (NOT sweep_results.json)")
    args = ap.parse_args()

    gold_by_vid = cg.load_gold()
    ytid_to_vid = {y: e["vid"] for y, e in cd.gold_entries().items() if e.get("vid")}
    adopted = adopted_vids(gold_by_vid)

    names = ([v.strip() for v in args.variants.split(",") if v.strip()] if args.variants
             else sorted(os.listdir(SWEEP)) if os.path.isdir(SWEEP) else [])

    prod = cg._prod_map()
    gold_median = statistics.median([len(g["sections"]) for g in gold_by_vid.values()])

    rows = []
    for v in names:
        cand = load_variant(v, ytid_to_vid, gold_by_vid)
        if not cand:
            continue
        vids = sorted(cand)
        inf = [x for x in vids if x not in adopted]
        rows.append({"variant": v, "all": score(cand, gold_by_vid, vids),
                     "informative": score(cand, gold_by_vid, inf) if inf else None})

    # Prod on the same informative videos, so the bar is measured not quoted.
    all_inf = [v for v in gold_by_vid if v not in adopted]
    base = score({v: prod.get(v, []) for v in all_inf}, gold_by_vid, all_inf)

    print()
    print(f"gold median sections: {gold_median:.0f}   "
          f"informative subset: {len(all_inf)} of {len(gold_by_vid)} gold videos")
    print(f"PROD BASELINE (informative, live): F1 {base['f1']:.3f}  "
          f"label {base['label']:.3f}  n={base['n']}")
    print()
    hdr = ("{:<16} {:>4} {:>7} {:>7} {:>7} {:>6}   {:>4} {:>7} {:>7} {:>6}")
    print(hdr.format("", "--", "-- ALL", "VIDEOS", "--", "", "--", "INFORMATIVE",
                     "SUBSET", "--"))
    print(hdr.format("variant", "n", "F1", "label", "ratio", "med",
                     "n", "F1", "label", "med"))
    rows.sort(key=lambda r: -(r["informative"]["f1"] if r["informative"] else -1))
    for r in rows:
        a, i = r["all"], r["informative"]
        print(hdr.format(
            r["variant"], a["n"], f"{a['f1']:.3f}", f"{a['label']:.3f}",
            f"{a['size_ratio']:.2f}x", f"{a['median_sections']:.0f}",
            i["n"] if i else 0, f"{i['f1']:.3f}" if i else "-",
            f"{i['label']:.3f}" if i else "-",
            f"{i['median_sections']:.0f}" if i else "-"))
    print()
    print(f"A variant beats prod only if its INFORMATIVE F1 > {base['f1']:.3f} "
          "and its size ratio is 0.8-1.3.")
    print("Counts are partial while the sweep is still running - check n.")

    if args.json:
        json.dump({"generated": rs._now(), "baseline_informative": base,
                   "gold_median_sections": gold_median, "rows": rows},
                  open(args.json, "w", encoding="utf-8"), indent=1)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
