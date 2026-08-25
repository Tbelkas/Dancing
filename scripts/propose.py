"""
propose.py [ytid ...] [--gold] [--limit N] [--samples 1|2] [--force]

Stage 03: ask Claude to choose section boundaries from the candidate list and name
them. The model never emits a timecode - it returns candidate ids, so a boundary
is either one the signals actually found or it is rejected. That is the whole
anti-hallucination design; see candidates.py.

    python scripts/propose.py --gold --limit 5      try it on five
    python scripts/propose.py --gold --samples 2    the full run

Reads  _proto/sig_<ytid>.json, _proto/cand_<ytid>.json
Writes _proto/prop_<ytid>.json

COST
----
Each sample is one headless `claude -p` invocation and runs on the Claude Code
subscription - the same quota as an interactive session, the same mechanism
chip_auto.bat already uses nightly. One call per video per sample, so --samples 2
over 68 videos is 136 calls. Start small.

--samples 2 runs the prompt twice and records boundary agreement (IoU at +/-3s).
That is the routing signal for stage 04: low agreement means the transcript alone
is not deciding it, and the video needs eyes on the frames.

Honours the dashboard's Pause button between videos.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

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

PROTO = rs.PROTO
def _claude_bin():
    """Find the Claude Code binary.

    Hardcoding this is how chip_auto.bat came to call a path that no longer
    existed: the install moved, the nightly drain failed every night for weeks,
    and the only trace was a batch error in a log nobody reads. Resolve it.
    """
    override = os.environ.get("CHIP_CLAUDE_BIN")
    if override and os.path.exists(override):
        return override
    import shutil
    found = shutil.which("claude")
    if found:
        return found
    for c in (os.path.expanduser(os.path.join("~", ".local", "bin", "claude.exe")),
              os.path.join("C:", os.sep, "nvm4w", "nodejs", "claude.cmd")):
        if os.path.exists(c):
            return c
    raise SystemExit("cannot find the claude binary; set CHIP_CLAUDE_BIN")


CLAUDE = _claude_bin()
TIMEOUT = 300
TOL = 3


def prop_path(y):
    return os.path.join(PROTO, f"prop_{y}.json")


def mmss(t):
    t = int(t or 0)
    return f"{t//60}:{t%60:02d}"


def build_prompt(ytid, sig, cand, dance):
    dur = sig.get("dur") or 0
    segs = (sig.get("asr") or {}).get("segments") or []

    # Condense: one line per utterance, timecoded. Long videos get thinned so the
    # prompt stays a readable transcript rather than a wall.
    step = 1 if len(segs) <= 260 else max(1, len(segs) // 260)
    lines = [f"[{mmss(s['start'])}] {s['text']}" for s in segs[::step] if s.get("text")]
    transcript = "\n".join(lines) or "(no speech detected)"

    rows = []
    for c in cand["candidates"]:
        note = (c["notes"][0] if c.get("notes") else "")[:60]
        rows.append(f"{c['id']:>4} | {mmss(c['t']):>7} | {c['score']:>4.1f} | "
                    f"{','.join(c['sources'])[:28]:<28} | {note}")
    table = "\n".join(rows)

    want = cand.get("suggested_sections", 6)
    return f"""You are labelling the sections of a dance tutorial so a learner can jump straight to the part they want.

VIDEO
  dance: {dance or "unknown"}
  length: {mmss(dur)}
  aim for roughly {want} sections (between 3 and 14).

TRANSCRIPT
{transcript}

CANDIDATE BOUNDARIES
Every place a section could start, found from speech, pauses, scene cuts and
music changes. Columns: id | time | strength | signals | nearby text.
{table}

TASK
Choose the ids where a new section genuinely begins, and name each one.

RULES
- Return ONLY candidate ids from the table. Never invent a time.
- The first section starts at the earliest candidate at or near 0:00.
- A boundary is where WHAT IS BEING TAUGHT changes - a new move, a drill, a
  run-through with music, the outro. Not every pause or camera cut.
- Labels name what a dancer would look for: "Add the heel & toe", "Practice with
  music", "The Jack (the groove)". 2-5 words, under 34 characters.
- Never use: "Tutorial", "Part 1", "Section 2", "Untitled", or the dance name on
  its own. Those carry no information and are what this is replacing.
- Every label must be distinct.
- Keep Intro and Outro when they exist - they are useful to skip past.
- Sections should be at least ~15s apart.

OUTPUT
A single JSON array, nothing else - no prose, no code fence:
[{{"candidate_id": 0, "label": "Intro", "evidence": "quote from the transcript", "confidence": 0.9}}]
"""


class QuotaExhausted(RuntimeError):
    """The subscription window is used up. Distinct from a normal failure because
    the right response is to STOP, not to try the next video.

    The 06:00 sweep did not have this: it hit the limit partway through the first
    variant, then made ~150 more calls that failed instantly, and reported "exit
    code 0" having produced nothing for four of five variants."""


LIMIT_MARKERS = ("session limit", "usage limit", "rate limit",
                 "quota", "resets ", "limit reached")


def call_claude(prompt):
    p = subprocess.run(
        [CLAUDE, "-p", "--dangerously-skip-permissions"],
        input=prompt, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=TIMEOUT,
    )
    blob = ((p.stderr or "") + " " + (p.stdout or "")).lower()
    if any(m in blob for m in LIMIT_MARKERS):
        raise QuotaExhausted(((p.stderr or p.stdout or "")[-200:]).strip())
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "claude failed")[-300:])
    return p.stdout


def parse_sections(raw, cand):
    """Pull the JSON array out and keep only rows that name a real candidate."""
    txt = raw.strip()
    m = re.search(r"\[[\s\S]*\]", txt)
    if not m:
        raise ValueError("no JSON array in model output")
    data = json.loads(m.group(0))
    by_id = {c["id"]: c for c in cand["candidates"]}

    out, seen = [], set()
    for row in data:
        if not isinstance(row, dict):
            continue
        cid = row.get("candidate_id")
        if cid not in by_id or cid in seen:
            continue  # invented or duplicated id - dropped, not repaired
        seen.add(cid)
        label = (row.get("label") or "").strip()[:60]
        if not label:
            continue
        out.append({
            "candidate_id": cid,
            "start": int(round(by_id[cid]["t"])),
            "label": label,
            "evidence": (row.get("evidence") or "")[:200],
            "confidence": row.get("confidence"),
        })
    out.sort(key=lambda s: s["start"])
    for i, s in enumerate(out):
        s["end"] = out[i + 1]["start"] if i + 1 < len(out) else cand.get("dur")
    return out


def agreement(a, b):
    """Boundary IoU at +/-TOL between two samples, ignoring the trivial 0."""
    pa = {s["start"] for s in a if s["start"] > TOL}
    pb = {s["start"] for s in b if s["start"] > TOL}
    if not pa and not pb:
        return 1.0
    inter = sum(1 for x in pa if any(abs(x - y) <= TOL for y in pb))
    union = len(pa) + len(pb) - inter
    return round(inter / union, 3) if union else 0.0


def dance_names():
    """vid/ytid -> dance name, from the health snapshot (no DB round trip)."""
    h = rs._read(os.path.join(PROTO, "chip_health.json"), {})
    return {r["ytid"]: r.get("dance") for r in h.get("videos", []) if r.get("ytid")}


def process(ytid, names, samples, force):
    if os.path.exists(prop_path(ytid)) and not force:
        return "cached", None
    sig = rs._read(cd.sig_path(ytid), None)
    cand = rs._read(cd.cand_path(ytid), None)
    if not sig or not cand:
        return "no-inputs", None
    if not cand.get("candidates"):
        return "no-candidates", None

    prompt = build_prompt(ytid, sig, cand, names.get(ytid))
    runs, errs = [], []
    for i in range(samples):
        try:
            runs.append(parse_sections(call_claude(prompt), cand))
        except Exception as e:  # noqa: BLE001 - recorded, batch continues
            errs.append(f"{type(e).__name__}: {str(e)[:160]}")
    if not runs:
        return "failed", {"errors": errs}

    best = max(runs, key=len)
    doc = {
        "ytid": ytid, "dur": cand.get("dur"), "holdout": cand.get("holdout"),
        "samples": len(runs), "errors": errs,
        "agreement": agreement(runs[0], runs[1]) if len(runs) > 1 else None,
        "sections": best,
        "all_samples": runs if len(runs) > 1 else None,
    }
    json.dump(doc, open(prop_path(ytid), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return "ok", doc


def cmd_eval():
    """Score every proposal we have against gold. Closes the loop: this is the
    number that has to beat the prod baseline for any of this to be worth it."""
    import chip_gold as cg
    gold = cd.gold_entries()
    cand = {}
    for y, e in gold.items():
        d = rs._read(prop_path(y), None)
        if d and d.get("sections") and e.get("sections"):
            cand[e["vid"]] = d["sections"]
    if not cand:
        print("no proposals to score yet")
        return
    scored = {v: g for v, g in cg.load_gold().items() if v in cand}
    cg.evaluate(cand, scored, "PROPOSED - stage 03 vs gold (held out)")
    print()
    print("Compare against: python scripts/chip_gold.py baseline")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ytids", nargs="*")
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--gold", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--samples", type=int, default=1, choices=(1, 2))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.eval:
        cmd_eval()
        return

    gold = cd.gold_entries()
    ids = list(args.ytids)
    if args.gold:
        ids += [y for y in sorted(gold) if os.path.exists(cd.cand_path(y))]
    ids = list(dict.fromkeys(ids))
    if not args.force:
        ids = [y for y in ids if not os.path.exists(prop_path(y))]
    if args.limit:
        ids = ids[:args.limit]
    if not ids:
        print("nothing to do")
        return

    calls = len(ids) * args.samples
    print(f"{len(ids)} video(s) x {args.samples} sample(s) = {calls} claude -p calls")
    rs.start_run("propose", total=len(ids))
    counts = {}
    for ytid in ids:
        if not rs.wait_if_paused():
            break
        rs.begin(ytid=ytid, stage="propose")
        t0 = time.time()
        try:
            status, doc = process(ytid, dance_names(), args.samples, args.force)
        except Exception as e:  # noqa: BLE001
            status, doc = f"error:{type(e).__name__}", None
            rs.log(f"{ytid}: {type(e).__name__}: {str(e)[:150]}")
        counts[status] = counts.get(status, 0) + 1
        el = time.time() - t0
        extra = ""
        if doc and doc.get("sections"):
            extra = f"  {len(doc['sections'])} sections"
            if doc.get("agreement") is not None:
                extra += f"  agreement {doc['agreement']:.2f}"
        rs.done_one(ok=status == "ok", msg=f"{ytid} {status}{extra}")
        print(f"  {ytid:<14} {status:<14} {el:>5.0f}s{extra}")
    rs.finish()
    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
