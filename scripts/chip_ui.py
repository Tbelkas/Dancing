"""
chip_ui.py [--port 8787] [--no-open]

Local dashboard for the chip pipeline. Two tabs:

  Queue  catalog chip health, the queue ranked by reach x deficit, live run
         progress and stage, a log, and Pause / Resume / Stop.
  Compare what is live vs what each pipeline variant proposed, side by side,
          so a person can say which is better. Built because neither automatic
          metric can: creator-agreement says the proposals lose, and the quality
          rubric cannot tell prod, the proposals and the creators' own chapters
          apart. Answers go to _proto/judgments.json.
  Intake  videos held back by the quality gate, and live ones the rubric would
          not have admitted. Approve/Reject here is the ONE database write this
          tool makes, scoped to the three review columns on a single row.
  Signals what stage 01 extracted from each video, and what failed. Reads the
         append-only extraction log, so a failure does not scroll away.
  Gold   the optional half of the eval set. Most ground truth comes free from
         creators' own chapter markers (chip_gold.py auto); this tab is only for
         the videos that have no chapters and no free truth. Play, press S at each
         boundary, name it, save.

    python scripts/chip_ui.py     ->  http://127.0.0.1:8787

Deliberately local and stdlib-only. The pipeline runs on this PC, so its control
plane lives here too — putting it in the Angular admin would mean API endpoints,
a deploy, and needless load on the Pi, none of which buys anything.

Binds to 127.0.0.1 only. It reads the prod connection string (via chip_health) and
can trigger a read-only rescan, but it never writes to the database. The only
things it writes are _proto/chip_control.json and _proto/gold/*.json - plus, in
the Intake tab only, a video's ReviewState/ReviewedAt/ReviewNote when you approve
or reject it. That one write is deliberate: reviewing is a decision a person makes
here, so it is applied here.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chip_runstate as rs  # noqa: E402

ROOT = rs.ROOT
HEALTH = os.path.join(rs.PROTO, "chip_health.json")
GOLD = os.path.join(rs.PROTO, "gold")
GOLD_AUTO = os.path.join(rs.PROTO, "gold_auto")
EXTRACT_LOG = os.path.join(rs.PROTO, "extract_log.jsonl")
SWEEP = os.path.join(rs.PROTO, "sweep")
JUDGMENTS = os.path.join(rs.PROTO, "judgments.json")

_intake_cache = {"at": 0.0, "rows": None}

_rescan = {"running": False, "error": None}


# ------------------------------------------------------------------- rescan

def _do_rescan():
    _rescan["running"], _rescan["error"] = True, None
    try:
        p = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "chip_health.py")],
            capture_output=True, text=True, cwd=ROOT, encoding="utf-8", timeout=600,
        )
        if p.returncode:
            _rescan["error"] = (p.stderr or p.stdout or "rescan failed")[-400:]
    except Exception as e:  # noqa: BLE001 - surfaced in the UI, not swallowed
        _rescan["error"] = str(e)
    finally:
        _rescan["running"] = False


# --------------------------------------------------------------------- gold

def gold_list():
    out = []
    if not os.path.isdir(GOLD):
        return out
    for name in sorted(os.listdir(GOLD)):
        if not name.endswith(".json") or name.startswith("_"):
            continue
        d = rs._read(os.path.join(GOLD, name), None)
        if not d:
            continue
        out.append({k: d.get(k) for k in
                    ("vid", "ytid", "platform", "title", "dance", "dur",
                     "views", "bucket", "signal", "reviewed")}
                   | {"n": len(d.get("sections") or [])})
    order = {"none": 0, "poor": 1, "weak": 2, "ok": 3}
    out.sort(key=lambda r: (order.get(r["bucket"], 9), -(r["views"] or 0)))
    return out


def gold_path(vid):
    """Resolve a gold file, refusing anything that isn't a plain integer id."""
    if not re.fullmatch(r"\d+", str(vid)):
        return None
    return os.path.join(GOLD, f"{int(vid)}.json")


def gold_save(vid, body):
    path = gold_path(vid)
    if not path or not os.path.exists(path):
        return None
    d = rs._read(path, {})
    secs = []
    for s in body.get("sections") or []:
        try:
            start = max(0, int(s.get("start") or 0))
        except (TypeError, ValueError):
            continue
        end = s.get("end")
        try:
            end = int(end) if end not in (None, "") else None
        except (TypeError, ValueError):
            end = None
        label = (s.get("label") or "").strip()[:80]
        secs.append({"start": start, "end": end, "label": label})
    secs.sort(key=lambda s: s["start"])
    d["sections"] = secs
    d["reviewed"] = bool(body.get("reviewed"))
    d["note"] = (body.get("note") or "")[:500]
    if d["reviewed"]:
        d["prefilled_from"] = "human"
    rs._write_atomic(path, d)
    return d


# ------------------------------------------------------------------- compare

def _chipsets(ytid):
    """Every chip set we have for one video: what is live, what each variant
    proposed, and the creator's own chapters."""
    out = {}
    for d in (SWEEP, None):
        pass
    if os.path.isdir(SWEEP):
        for variant in sorted(os.listdir(SWEEP)):
            f = os.path.join(SWEEP, variant, "prop_" + ytid + ".json")
            d = rs._read(f, None)
            if d and d.get("sections"):
                out[variant] = d["sections"]
    d = rs._read(os.path.join(rs.PROTO, "prop_" + ytid + ".json"), None)
    if d and d.get("sections"):
        out.setdefault("stage03", d["sections"])
    return out


def compare_list():
    """Videos where a proposal exists to weigh against what is live."""
    import video_gate as vg
    raw = json.loads(vg.ch.psql(vg.ch.FETCH).strip() or "[]")
    by_yt = {}
    for r in raw:
        if r["platform"] == "youtube" and r["clipstart"] is None:
            by_yt.setdefault(r["ytid"], r)
    judged = rs._read(JUDGMENTS, {})
    rows = []
    for ytid, r in by_yt.items():
        sets = _chipsets(ytid)
        if not sets:
            continue
        rows.append({"ytid": ytid, "vid": r["vid"], "title": r["title"],
                     "dance": r["dance"], "dur": r["dur"], "views": r["views"],
                     "prod_n": len(r["segs"]), "variants": sorted(sets),
                     "judged": judged.get(ytid, {}).get("winner")})
    rows.sort(key=lambda x: (x["judged"] is not None, -(x["views"] or 0)))
    return rows


def compare_detail(ytid):
    import video_gate as vg
    raw = json.loads(vg.ch.psql(vg.ch.FETCH).strip() or "[]")
    row = next((r for r in raw if r["ytid"] == ytid and r["clipstart"] is None), None)
    if not row:
        return None
    sets = {"prod (live now)": [{"label": x["label"], "start": x["start"]}
                                for x in row["segs"]]}
    gold = rs._read(os.path.join(rs.PROTO, "gold_auto", str(row["vid"]) + ".json"), None)
    if gold and gold.get("sections"):
        sets["creator chapters"] = [{"label": x["label"], "start": x["start"]}
                                    for x in gold["sections"]]
    for k, v in _chipsets(ytid).items():
        sets[k] = [{"label": x["label"], "start": x["start"]} for x in v]
    judged = rs._read(JUDGMENTS, {}).get(ytid, {})
    return {"ytid": ytid, "vid": row["vid"], "title": row["title"],
            "dance": row["dance"], "dur": row["dur"], "sets": sets,
            "judged": judged}


def compare_judge(ytid, winner, note):
    """Record which chip set a human thinks is best.

    This exists because neither automatic metric can settle it: creator-agreement
    says the proposals lose, and our own rubric scores prod, the proposals and the
    creator's chapters all within 0.01 of each other. Only a person looking at two
    lists can say which one they would rather have on the page.
    """
    j = rs._read(JUDGMENTS, {})
    j[ytid] = {"winner": winner, "note": (note or "")[:300], "at": rs._now()}
    rs._write_atomic(JUDGMENTS, j)
    return j[ytid]


# -------------------------------------------------------------------- intake

def intake_rows(force=False):
    """Videos awaiting review, plus admitted ones the rubric flagged.

    Cached briefly: the dashboard polls every 2s and the database is over the LAN.
    """
    now = time.time()
    if not force and _intake_cache["rows"] is not None and now - _intake_cache["at"] < 15:
        return _intake_cache["rows"]
    import video_gate as vg
    raw = json.loads(vg.ch.psql(vg.FETCH).strip() or "[]")
    rows = []
    for r in raw:
        if r["state"] == "approved" and not r.get("otherdances"):
            pass
        meta = vg.load_meta(r["ytid"]) if r["platform"] == "youtube" else None
        sig = vg.load_sig(r["ytid"]) if r["platform"] == "youtube" else None
        score, verdict, flags, tier = vg.grade(r, meta, sig)
        # Show what needs a decision: anything held back, plus anything live that
        # the rubric would not have admitted on its own.
        if r["state"] != "approved" or verdict != "admit":
            rows.append({
                "vid": r["vid"], "ytid": r["ytid"], "platform": r["platform"],
                "title": r["title"], "dance": r["dance"], "dur": r["dur"],
                "views": r["views"], "state": r["state"], "vtype": r["vtype"],
                "score": score, "verdict": verdict, "flags": flags, "tier": tier,
            })
    rows.sort(key=lambda x: (x["state"] == "approved", x["score"]))
    _intake_cache.update(at=now, rows=rows)
    return rows


def intake_decide(vid, action, note):
    """The ONLY database write this dashboard performs.

    Scoped to the three review columns on one row by id - it never touches video
    content, chips, or anything else. Reviewing is a decision a person makes here,
    so it is made here; everything else in this tool stays read-only.
    """
    if action not in ("approve", "reject", "pending"):
        return None
    import video_gate as vg
    state = {"approve": "approved", "reject": "rejected", "pending": "pending"}[action]
    safe = (note or "")[:300].replace("'", "''")
    vg.ch.psql(f'''update "Videos"
                      set "ReviewState" = \'{state}\',
                          "ReviewedAt" = now(),
                          "ReviewNote" = {"null" if not safe else "'" + safe + "'"}
                    where "Id" = {int(vid)};''')
    _intake_cache["rows"] = None
    return state


# ------------------------------------------------------------------ signals

def extract_records():
    """Latest extraction record per video, newest first. Reads the append-only
    log so failures survive; the run-state ring buffer would have dropped them."""
    latest = {}
    if os.path.exists(EXTRACT_LOG):
        for line in open(EXTRACT_LOG, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("ytid"):
                latest[r["ytid"]] = r
    # Anything extracted before the log existed still deserves a row.
    for name in os.listdir(rs.PROTO):
        if name.startswith("sig_") and name.endswith(".json"):
            yt = name[4:-5]
            latest.setdefault(yt, {"ytid": yt, "status": "ok", "unlogged": True})
    rows = list(latest.values())
    rows.sort(key=lambda r: r.get("ts") or "", reverse=True)
    return rows


def signal_detail(ytid):
    """The extracted content itself, trimmed to what is worth eyeballing."""
    path = os.path.join(rs.PROTO, "sig_" + ytid + ".json")
    d = rs._read(path, None)
    if d is None:
        return None
    a = d.get("asr") or {}
    return {
        "ytid": ytid, "dur": d.get("dur"), "generated": d.get("generated"),
        "language": a.get("language"), "lang_prob": a.get("language_probability"),
        "model": a.get("model"), "device": a.get("device"),
        "asr_seconds": d.get("asr_seconds"),
        "segments": (a.get("segments") or [])[:400],
        "segment_total": len(a.get("segments") or []),
        "word_total": len(a.get("words") or []),
        "silence": (d.get("silence") or [])[:200],
        "scenes": (d.get("scenes") or [])[:200],
        "density": d.get("density") or [],
        "chapters": d.get("chapters") or [],
        "desc_timestamps": d.get("desc_timestamps") or [],
    }


# ------------------------------------------------------------------ handler

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # the dashboard polls twice a second; don't spam the console

    def _send(self, code, body, ctype="application/json"):
        raw = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/":
            return self._send(200, PAGE, "text/html")

        if self.path == "/api/state":
            health = rs._read(HEALTH, {})
            vids = health.get("videos", [])
            return self._send(200, json.dumps({
                "summary": health.get("summary", {}),
                "by_source": health.get("by_source", {}),
                "total_videos": len(vids),
                "total_segments": sum(v.get("n", 0) for v in vids),
                "queue": vids[:200],
                "run": rs._read(rs.STATE, {}),
                "control": rs.control(),
                "rescan": dict(_rescan),
            }))

        if self.path == "/api/gold":
            g = gold_list()
            auto = len([f for f in os.listdir(GOLD_AUTO)
                        if f.endswith(".json")]) if os.path.isdir(GOLD_AUTO) else 0
            return self._send(200, json.dumps({
                "entries": g,
                "reviewed": sum(1 for r in g if r["reviewed"]),
                "total": len(g),
                "auto": auto,
            }))

        if self.path == "/api/compare":
            try:
                rows = compare_list()
            except SystemExit as e:
                return self._send(500, json.dumps({"error": str(e)}))
            return self._send(200, json.dumps({
                "rows": rows[:200],
                "judged": len([r for r in rows if r["judged"]]),
                "total": len(rows)}))

        m = re.fullmatch(r"/api/compare/([A-Za-z0-9_-]{5,20})", self.path)
        if m:
            d = compare_detail(m.group(1))
            if d is None:
                return self._send(404, json.dumps({"error": "no such video"}))
            return self._send(200, json.dumps(d))

        if self.path == "/api/intake":
            try:
                rows = intake_rows()
            except SystemExit as e:
                return self._send(500, json.dumps({"error": str(e)}))
            return self._send(200, json.dumps({
                "rows": rows,
                "pending": len([r for r in rows if r["state"] == "pending"]),
                "rejected": len([r for r in rows if r["state"] == "rejected"]),
                "flagged_live": len([r for r in rows if r["state"] == "approved"]),
            }))

        if self.path == "/api/signals":
            rows = extract_records()
            ok = [r for r in rows if r.get("status") == "ok"]
            return self._send(200, json.dumps({
                "rows": rows[:400],
                "total": len(rows),
                "ok": len(ok),
                "failed": len([r for r in rows if r.get("status") != "ok"]),
                "asr_seconds": round(sum(r.get("asr_seconds") or 0 for r in ok), 1),
                "footage": sum(r.get("dur") or 0 for r in ok),
            }))

        m = re.fullmatch(r"/api/signals/([A-Za-z0-9_-]{5,20})", self.path)
        if m:
            d = signal_detail(m.group(1))
            if d is None:
                return self._send(404, json.dumps({"error": "no signals for that video"}))
            return self._send(200, json.dumps(d))

        m = re.fullmatch(r"/api/gold/(\d+)", self.path)
        if m:
            path = gold_path(m.group(1))
            d = rs._read(path, None) if path else None
            if d is None:
                return self._send(404, json.dumps({"error": "no such gold entry"}))
            return self._send(200, json.dumps(d))

        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, json.dumps({"error": "bad json"}))

        if self.path == "/api/control":
            action = body.get("action")
            try:
                rs.set_control(action)
            except ValueError:
                return self._send(400, json.dumps({"error": f"bad action: {action}"}))
            return self._send(200, json.dumps({"control": action}))

        if self.path == "/api/rescan":
            if _rescan["running"]:
                return self._send(409, json.dumps({"error": "already running"}))
            threading.Thread(target=_do_rescan, daemon=True).start()
            return self._send(200, json.dumps({"started": True}))

        m = re.fullmatch(r"/api/compare/([A-Za-z0-9_-]{5,20})", self.path)
        if m:
            w = body.get("winner")
            if not w or len(str(w)) > 40:
                return self._send(400, json.dumps({"error": "bad winner"}))
            return self._send(200, json.dumps(
                compare_judge(m.group(1), str(w), body.get("note"))))

        m = re.fullmatch(r"/api/intake/(\d+)", self.path)
        if m:
            state = intake_decide(m.group(1), body.get("action"), body.get("note"))
            if state is None:
                return self._send(400, json.dumps({"error": "bad action"}))
            return self._send(200, json.dumps({"state": state}))

        m = re.fullmatch(r"/api/gold/(\d+)", self.path)
        if m:
            d = gold_save(m.group(1), body)
            if d is None:
                return self._send(404, json.dumps({"error": "no such gold entry"}))
            return self._send(200, json.dumps(d))

        return self._send(404, json.dumps({"error": "not found"}))


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Chip Refinery</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600&family=Barlow:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap">
<style>
:root{
  --bg:#07070D; --surface:#0D0D1A; --surface2:#141422; --border:#262642; --border-lt:#353558;
  --text:#EDE8FF; --muted:#9490B8; --dim:#6E6A90;
  --amber:#F5C842; --verm:#E8503A; --teal:#62C4B0; --green:#5ECFA8; --violet:#8B7BF0;
  --mono:'DM Mono','Courier New',monospace; --ui:'Barlow Condensed',sans-serif;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 'Barlow',system-ui,sans-serif}
.wrap{max-width:1320px;margin:0 auto;padding:0 22px 70px}
a{color:var(--amber);text-decoration:none} a:hover{text-decoration:underline}
.lbl{font-family:var(--ui);text-transform:uppercase;letter-spacing:.13em;font-size:12px;color:var(--dim)}
.hide{display:none !important}

header{display:flex;align-items:center;gap:16px;flex-wrap:wrap;
  padding:22px 0 0;border-bottom:1px solid var(--border);margin-bottom:24px}
h1{font-family:var(--ui);font-size:23px;letter-spacing:.05em;text-transform:uppercase;margin:0;font-weight:600}
h1 span{color:var(--amber)}
.pill{font-family:var(--ui);text-transform:uppercase;letter-spacing:.12em;font-size:12px;
  padding:4px 11px;border:1px solid var(--border-lt);color:var(--muted)}
.pill.running{color:var(--green);border-color:rgba(94,207,168,.5)}
.pill.paused{color:var(--amber);border-color:rgba(245,200,66,.5)}
.pill.stopped,.pill.failed{color:var(--verm);border-color:rgba(232,80,58,.5)}
.spacer{flex:1}
button{font-family:var(--ui);text-transform:uppercase;letter-spacing:.12em;font-size:12.5px;
  background:var(--surface2);color:var(--text);border:1px solid var(--border-lt);
  padding:7px 15px;cursor:pointer;transition:.14s}
button:hover:not(:disabled){border-color:var(--amber);color:var(--amber)}
button:disabled{opacity:.32;cursor:not-allowed}
button.primary{border-color:rgba(245,200,66,.55);color:var(--amber)}
button.go{border-color:rgba(94,207,168,.55);color:var(--green)}
button.danger:hover:not(:disabled){border-color:var(--verm);color:var(--verm)}
button.sm{padding:3px 9px;font-size:11.5px}
:focus-visible{outline:2px solid var(--amber);outline-offset:2px}

nav{display:flex;gap:0;width:100%;margin-top:16px}
nav b{font-family:var(--ui);text-transform:uppercase;letter-spacing:.13em;font-size:13px;
  padding:9px 18px;cursor:pointer;color:var(--dim);border-bottom:2px solid transparent;font-weight:600}
nav b.on{color:var(--amber);border-bottom-color:var(--amber)}
nav b:hover{color:var(--text)}

.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:1px;
  background:var(--border);border:1px solid var(--border);margin-bottom:22px}
.tile{background:var(--surface);padding:13px 15px;cursor:pointer;transition:.14s}
.tile:hover{background:var(--surface2)}
.tile.on{background:var(--surface2);box-shadow:inset 2px 0 0 var(--amber)}
.tile b{display:block;font-family:var(--mono);font-size:25px;font-variant-numeric:tabular-nums;line-height:1.2}
.tile.none b,.tile.poor b{color:var(--verm)}
.tile.weak b{color:var(--amber)} .tile.ok b{color:var(--green)}

.panel{background:var(--surface);border:1px solid var(--border);margin-bottom:22px}
.panel h2{font-family:var(--ui);text-transform:uppercase;letter-spacing:.13em;font-size:13px;
  color:var(--muted);margin:0;padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600}
.panel .body{padding:15px 16px}

.bar{height:6px;background:var(--surface2);border:1px solid var(--border);overflow:hidden}
.bar i{display:block;height:100%;background:var(--amber);transition:width .3s}
.runline{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;margin-bottom:11px;font-family:var(--mono);font-size:13px}
.runline .k{color:var(--dim)}

.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th{font-family:var(--ui);text-transform:uppercase;letter-spacing:.11em;font-size:11.5px;color:var(--dim);
  text-align:left;font-weight:600;padding:9px 12px;border-bottom:1px solid var(--border);white-space:nowrap;
  position:sticky;top:0;background:var(--surface)}
td{padding:8px 12px;border-bottom:1px solid var(--surface2);vertical-align:middle;white-space:nowrap}
tr:hover td{background:var(--surface2)}
td.n{font-family:var(--mono);font-variant-numeric:tabular-nums}
td.t{white-space:normal;max-width:330px;color:var(--muted)}
.sc{display:inline-flex;align-items:center;gap:7px}
.sc i{display:block;width:42px;height:4px;background:var(--surface2);position:relative}
.sc i s{position:absolute;inset:0 auto 0 0;display:block;text-decoration:none}
.src{font-family:var(--ui);text-transform:uppercase;letter-spacing:.1em;font-size:11px;
  padding:2px 7px;border:1px solid var(--border-lt);color:var(--muted)}
.src.generic,.src.none{color:var(--verm);border-color:rgba(232,80,58,.4)}
.src.slice{color:var(--violet);border-color:rgba(139,123,240,.4)}
.src.manual{color:var(--green);border-color:rgba(94,207,168,.4)}
.iss{font-family:var(--mono);font-size:11.5px;color:var(--dim);white-space:normal;max-width:250px}

#log{font-family:var(--mono);font-size:12.5px;max-height:230px;overflow-y:auto;
  background:var(--bg);border:1px solid var(--border);padding:11px 13px}
#log div{color:var(--muted);margin-bottom:3px}
#log div b{color:var(--dim);font-weight:400;margin-right:9px}
#tx{font-family:var(--mono);font-size:12.5px;max-height:300px;overflow-y:auto;background:var(--bg);border:1px solid var(--border);padding:11px 13px}
#tx div{color:var(--muted);margin-bottom:3px}
#tx div b{color:var(--amber);font-weight:400;margin-right:9px;font-variant-numeric:tabular-nums}
.empty{color:var(--dim);font-style:italic}
.err{color:var(--verm);font-family:var(--mono);font-size:12.5px;margin-top:9px}

/* ---- gold ---- */
.gwrap{display:grid;grid-template-columns:330px 1fr;gap:22px;align-items:start}
@media(max-width:1000px){.gwrap{grid-template-columns:1fr}}
.glist{background:var(--surface);border:1px solid var(--border);max-height:78vh;overflow-y:auto}
.gitem{padding:9px 13px;border-bottom:1px solid var(--surface2);cursor:pointer;display:flex;gap:9px;align-items:center}
.gitem:hover{background:var(--surface2)}
.gitem.on{background:var(--surface2);box-shadow:inset 2px 0 0 var(--amber)}
.gitem .tick{font-family:var(--mono);font-size:13px;color:var(--dim);width:13px;flex:none}
.gitem.done .tick{color:var(--green)}
.gitem .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13.5px}
.gitem .bk{font-family:var(--ui);text-transform:uppercase;letter-spacing:.1em;font-size:10.5px;color:var(--dim)}

.vid{position:relative;width:100%;aspect-ratio:16/9;background:#000;border:1px solid var(--border)}
.vid iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.ctl{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:13px 0}
.clock{font-family:var(--mono);font-size:22px;font-variant-numeric:tabular-nums;color:var(--amber);min-width:74px}

.secs{width:100%;border-collapse:collapse}
.secs td{padding:4px 6px;border-bottom:1px solid var(--surface2);white-space:nowrap}
.secs input{background:var(--bg);border:1px solid var(--border);color:var(--text);
  font-family:var(--mono);font-size:13.5px;padding:5px 8px}
.secs input.tm{width:74px;text-align:center;font-variant-numeric:tabular-nums}
.secs input.tm:hover{border-color:var(--amber);cursor:pointer}
.secs input.lb{width:100%;font-family:'Barlow',sans-serif}
.secs td.grow{width:100%}
.hint{font-family:var(--mono);font-size:12px;color:var(--dim);margin-top:9px}
.saved{color:var(--green);font-family:var(--ui);letter-spacing:.12em;text-transform:uppercase;font-size:12px}
</style></head><body>
<div class="wrap">

<header>
  <h1>Chip <span>Refinery</span></h1>
  <span class="pill" id="status">loading</span>
  <span class="spacer"></span>
  <button id="btn-pause">Pause</button>
  <button id="btn-resume" class="primary">Resume</button>
  <button id="btn-stop" class="danger">Stop</button>
  <button id="btn-rescan">Rescan</button>
  <nav>
    <b data-tab="queue" class="on">Queue</b>
    <b data-tab="gold">Gold set <span id="gcount" class="lbl"></span></b>
    <b data-tab="signals">Signals <span id="scount" class="lbl"></span></b>
    <b data-tab="intake">Intake <span id="icount" class="lbl"></span></b>
    <b data-tab="compare">Compare <span id="ccount" class="lbl"></span></b>
  </nav>
</header>

<div id="tab-queue">
  <div class="tiles" id="tiles"></div>
  <div class="panel"><h2>Current run</h2><div class="body" id="run"></div></div>
  <div class="panel">
    <h2>Queue &mdash; ranked by reach &times; deficit</h2>
    <div class="tw"><table>
      <thead><tr><th>#</th><th>Video</th><th>Title</th><th>Score</th><th>Chips</th>
        <th>Length</th><th>Views</th><th>Source</th><th>Issues</th></tr></thead>
      <tbody id="rows"></tbody>
    </table></div>
  </div>
  <div class="panel"><h2>Log</h2><div class="body"><div id="log"></div></div></div>
</div>

<div id="tab-compare" class="hide">
  <div class="panel"><div class="body" id="cnote" style="color:var(--muted);font-size:14px"></div></div>
  <div class="gwrap">
    <div class="glist" id="clist"></div>
    <div class="panel">
      <h2 id="ctitle">Pick a video</h2>
      <div class="body" id="cbody">
        <div class="empty">Choose a video to compare what is live against what the pipeline proposed.</div>
      </div>
    </div>
  </div>
</div>

<div id="tab-intake" class="hide">
  <div class="tiles" id="itiles"></div>
  <div class="panel">
    <h2>Awaiting review &mdash; and live videos the rubric would not have admitted</h2>
    <div class="tw"><table>
      <thead><tr><th>State</th><th>Video</th><th>Dance</th><th>Title</th><th>Score</th>
        <th>Len</th><th>Views</th><th>Why</th><th></th></tr></thead>
      <tbody id="irows"></tbody>
    </table></div>
  </div>
</div>

<div id="tab-signals" class="hide">
  <div class="tiles" id="stiles"></div>
  <div class="gwrap">
    <div class="glist" id="slist"></div>
    <div class="panel">
      <h2 id="stitle">Pick a video</h2>
      <div class="body" id="sbody">
        <div class="empty">Choose a video to see exactly what was extracted from it.</div>
      </div>
    </div>
  </div>
</div>

<div id="tab-gold" class="hide">
  <div class="panel"><div class="body" id="gnote" style="color:var(--muted);font-size:14px"></div></div>
  <div class="gwrap">
    <div class="glist" id="glist"></div>
    <div>
      <div class="panel" id="gpanel">
        <h2 id="gtitle">Pick a video</h2>
        <div class="body" id="gbody">
          <div class="empty">Choose a video on the left to start marking sections.</div>
        </div>
      </div>
    </div>
  </div>
</div>

</div>
<script src="https://www.youtube.com/iframe_api"></script>
<script>
const $ = s => document.querySelector(s);
let filter=null, state=null, tab='queue', gold=[], cur=null, player=null, tick=null;

const fmt = n => (n||0).toLocaleString();
const mmss = s => { s=Math.max(0,Math.round(s||0));
  return Math.floor(s/60)+':'+String(s%60).padStart(2,'0'); };
const parseT = v => { v=String(v||'').trim();
  if(v.includes(':')){ const p=v.split(':').map(Number);
    return p.length===3 ? p[0]*3600+p[1]*60+p[2] : (p[0]*60+p[1])||0; }
  return parseInt(v,10)||0; };
const esc = t => String(t==null?'':t).replace(/[<>&"]/g, c =>
  ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
const scColor = v => v<0.35 ? 'var(--verm)' : v<0.65 ? 'var(--amber)' : 'var(--green)';

async function api(path, body){
  const o = body ? {method:'POST', headers:{'Content-Type':'application/json'},
                    body:JSON.stringify(body)} : {};
  const r = await fetch(path, o);
  return r.json();
}

/* ---------------- tabs ---------------- */
document.querySelectorAll('nav b').forEach(b => b.onclick = () => {
  tab = b.dataset.tab;
  document.querySelectorAll('nav b').forEach(x => x.classList.toggle('on', x===b));
  $('#tab-queue').classList.toggle('hide', tab!=='queue');
  $('#tab-gold').classList.toggle('hide', tab!=='gold');
  $('#tab-signals').classList.toggle('hide', tab!=='signals');
  $('#tab-intake').classList.toggle('hide', tab!=='intake');
  $('#tab-compare').classList.toggle('hide', tab!=='compare');
  if(tab==='intake') loadIntake();
  if(tab==='compare') loadCompare();
  if(tab==='gold') loadGold();
  if(tab==='signals') loadSignals();
});

$('#btn-pause').onclick  = () => api('/api/control',{action:'pause'}).then(refresh);
$('#btn-resume').onclick = () => api('/api/control',{action:'run'}).then(refresh);
$('#btn-stop').onclick   = () => api('/api/control',{action:'stop'}).then(refresh);
$('#btn-rescan').onclick = () => api('/api/rescan',{}).then(refresh);

/* ---------------- queue tab ---------------- */
function bucket(r){ return !r.n ? 'none' : r.score<0.35 ? 'poor' : r.score<0.65 ? 'weak' : 'ok'; }

function drawTiles(s){
  const order=[['none','No chips'],['poor','Poor'],['weak','Weak'],['ok','Adequate']];
  $('#tiles').innerHTML = order.map(([k,l])=>`
    <div class="tile ${k} ${filter===k?'on':''}" data-k="${k}">
      <b>${fmt(s.summary[k])}</b><span class="lbl">${l}</span></div>`).join('')
    + `<div class="tile ${filter===null?'on':''}" data-k=""><b>${fmt(s.total_videos)}</b>
         <span class="lbl">All videos</span></div>
       <div class="tile"><b>${fmt(s.total_segments)}</b><span class="lbl">Chips total</span></div>`;
  document.querySelectorAll('.tile[data-k]').forEach(t=>t.onclick=()=>{
    filter=t.dataset.k||null; drawQueue(); });
}

function drawRun(s){
  const r=s.run||{}, el=$('#run');
  if(!r.run){ el.innerHTML=`<div class="empty">No run recorded yet. Workers report here as
    soon as a pipeline stage starts &mdash; Pause already holds the nightly drain.</div>`; return; }
  const pct = r.total ? Math.round(100*(r.done+r.failed)/r.total) : 0, c=r.current;
  el.innerHTML = `
    <div class="runline">
      <span><span class="k">run</span> ${esc(r.run)}</span>
      <span><span class="k">progress</span> ${r.done||0} ok${r.failed?` / ${r.failed} failed`:''} of ${r.total||0}</span>
      <span><span class="k">updated</span> ${(r.updated||'').replace('T',' ').replace('+00:00','Z')}</span>
    </div>
    <div class="bar"><i style="width:${pct}%"></i></div>
    <div class="runline" style="margin-top:11px">
      ${c ? `<span><span class="k">now</span> #${c.vid} ${esc(c.ytid||'')}</span>
             <span><span class="k">stage</span> ${esc(c.stage||'-')}</span>`
          : `<span class="empty">idle between videos</span>`}
    </div>`;
}

function drawQueue(){
  const s=state; if(!s) return;
  let q=s.queue; if(filter) q=q.filter(r=>bucket(r)===filter);
  $('#rows').innerHTML = q.slice(0,200).map((r,i)=>`
    <tr><td class="n" style="color:var(--dim)">${i+1}</td>
      <td class="n">${r.ytid&&r.platform==='youtube'
        ? `<a href="https://youtu.be/${esc(r.ytid)}" target="_blank" rel="noreferrer">#${r.vid}</a>`
        : `#${r.vid}`}</td>
      <td class="t">${esc(r.title||r.dance)}</td>
      <td class="n"><span class="sc"><i><s style="width:${Math.round(r.score*100)}%;
        background:${scColor(r.score)}"></s></i>${r.score.toFixed(2)}</span></td>
      <td class="n">${r.n}</td><td class="n">${r.dur?mmss(r.dur):'-'}</td>
      <td class="n">${fmt(r.views)}</td>
      <td><span class="src ${esc(r.source)}">${esc(r.source)}</span></td>
      <td class="iss">${esc(r.issues.join(' · '))}</td></tr>`).join('')
    || `<tr><td colspan="9" class="empty" style="padding:16px 12px">Nothing in this bucket.</td></tr>`;
}

function drawLog(s){
  const e=(s.run&&s.run.log)||[];
  $('#log').innerHTML = e.length
    ? e.slice().reverse().map(x=>`<div><b>${(x.t||'').slice(11,19)}</b>${esc(x.msg)}</div>`).join('')
    : `<div class="empty">Nothing logged yet.</div>`;
}

function draw(){
  const s=state; if(!s) return;
  const r=s.run||{}, ctl=s.control;
  const st = ctl==='pause'?'paused' : ctl==='stop'?'stopped' : (r.status||'idle');
  $('#status').textContent = s.rescan.running ? 'rescanning' : st;
  $('#status').className='pill '+st;
  $('#btn-pause').disabled  = ctl==='pause';
  $('#btn-resume').disabled = ctl==='run';
  $('#btn-rescan').disabled = s.rescan.running;
  drawTiles(s); drawRun(s); drawQueue(); drawLog(s);
  const old=document.querySelector('.err'); if(old) old.remove();
  if(s.rescan.error){ const d=document.createElement('div');
    d.className='err'; d.textContent='Rescan failed: '+s.rescan.error; $('#run').appendChild(d); }
}

async function refresh(){
  try{ state = await api('/api/state');
       if(tab==='signals' && (state.run||{}).run==='signals') loadSignals();
       if(tab==='queue') draw(); else {
        const s=state, ctl=s.control;
        const st = ctl==='pause'?'paused':ctl==='stop'?'stopped':((s.run||{}).status||'idle');
        $('#status').textContent=st; $('#status').className='pill '+st; } }
  catch(e){ $('#status').textContent='disconnected'; $('#status').className='pill stopped'; }
}

/* ---------------- gold tab ---------------- */
async function loadGold(){
  const d = await api('/api/gold');
  gold = d.entries;
  $('#gcount').textContent = `${d.auto} auto${d.total?` + ${d.reviewed}/${d.total}`:''}`;
  const note = $('#gnote');
  if(note) note.innerHTML = `<b>${d.auto}</b> videos are already scored against their
    creators' own chapter markers — no work needed. The <b>${d.total}</b> below have no
    chapters and no free ground truth, so they are the only ones a human could add
    anything to. <b>Entirely optional</b>: the eval works without them.`;
  $('#glist').innerHTML = gold.map(g=>`
    <div class="gitem ${g.reviewed?'done':''} ${cur&&cur.vid===g.vid?'on':''}" data-vid="${g.vid}">
      <span class="tick">${g.reviewed?'✓':'○'}</span>
      <span class="nm">${esc(g.title||g.dance)}</span>
      <span class="bk">${esc(g.bucket)}</span></div>`).join('')
    || `<div class="empty" style="padding:14px">No gold set yet. Run:
        <br><code>python scripts/chip_gold.py select</code></div>`;
  document.querySelectorAll('.gitem').forEach(el=>el.onclick=()=>openGold(+el.dataset.vid));
}

async function openGold(vid){
  cur = await api('/api/gold/'+vid);
  cur.sections = cur.sections || [];
  loadGold();
  $('#gtitle').textContent = `#${cur.vid}  ${cur.title||cur.dance}`;
  const yt = cur.platform==='youtube' && cur.ytid;
  $('#gbody').innerHTML = `
    ${yt ? `<div class="vid"><div id="ytplayer"></div></div>`
         : `<div class="empty">${esc(cur.platform)} clip — no embedded player here.
            <a href="#" id="openext">Open it externally</a> and type the times in.</div>`}
    <div class="ctl">
      <span class="clock" id="clock">0:00</span>
      <button class="go" id="add">+ Section at playhead</button>
      <button class="sm" id="back5">&laquo; 5s</button>
      <button class="sm" id="fwd5">5s &raquo;</button>
      <span class="spacer"></span>
      <label class="lbl" style="display:flex;gap:7px;align-items:center;cursor:pointer">
        <input type="checkbox" id="rev" ${cur.reviewed?'checked':''}> Reviewed</label>
      <button class="primary" id="save">Save</button>
      <span id="savedmsg"></span>
    </div>
    <table class="secs"><tbody id="secrows"></tbody></table>
    <div class="hint">Press <b>S</b> to drop a section at the playhead ·
      click a timecode to seek · tier ${esc(cur.bucket)} · signal ${esc(cur.signal)} ·
      ${cur.dur?mmss(cur.dur):'unknown'} long · prefilled from ${esc(cur.prefilled_from||'-')}</div>`;
  if(!yt) $('#openext').href = cur.platform==='tiktok'
    ? 'https://www.tiktok.com/' : 'https://www.instagram.com/';
  drawSecs();
  $('#add').onclick   = () => { addSec(now()); };
  $('#back5').onclick = () => seek(now()-5);
  $('#fwd5').onclick  = () => seek(now()+5);
  $('#save').onclick  = saveGold;
  if(yt) mountPlayer(cur.ytid);
}

function now(){ try{ return player&&player.getCurrentTime?player.getCurrentTime():0; }catch(e){ return 0; } }
function seek(t){ try{ player&&player.seekTo(Math.max(0,t),true); }catch(e){} }

function mountPlayer(ytid){
  const build = () => {
    if(player&&player.destroy){ try{player.destroy();}catch(e){} player=null; }
    player = new YT.Player('ytplayer', {videoId:ytid,
      playerVars:{rel:0, modestbranding:1}});
    if(tick) clearInterval(tick);
    tick = setInterval(()=>{ const c=$('#clock'); if(c) c.textContent = mmss(now()); }, 250);
  };
  if(window.YT && YT.Player) build(); else window.onYouTubeIframeAPIReady = build;
}

function addSec(t){
  t = Math.max(0, Math.round(t));
  if(!cur) return;
  if(cur.sections.some(s=>Math.abs(s.start-t)<2)) return;   // don't stack duplicates
  cur.sections.push({start:t, end:null, label:''});
  cur.sections.sort((a,b)=>a.start-b.start);
  drawSecs();
  const rows=document.querySelectorAll('#secrows input.lb');
  const i=cur.sections.findIndex(s=>s.start===t);
  if(rows[i]) rows[i].focus();
}

function drawSecs(){
  $('#secrows').innerHTML = cur.sections.map((s,i)=>`
    <tr>
      <td><input class="tm" data-i="${i}" data-f="start" value="${mmss(s.start)}"></td>
      <td class="grow"><input class="lb" data-i="${i}" data-f="label"
          value="${esc(s.label)}" placeholder="what is taught here"></td>
      <td><button class="sm danger" data-del="${i}">&times;</button></td>
    </tr>`).join('')
    || `<tr><td class="empty" style="padding:10px 6px">No sections yet — play the video and
        press S (or the button) where each new thing starts.</td></tr>`;

  document.querySelectorAll('#secrows input').forEach(el=>{
    el.onchange = () => {
      const i=+el.dataset.i;
      if(el.dataset.f==='start'){ cur.sections[i].start=parseT(el.value);
        cur.sections.sort((a,b)=>a.start-b.start); drawSecs(); }
      else cur.sections[i].label = el.value;
    };
    if(el.classList.contains('tm')) el.onclick = () => seek(parseT(el.value));
  });
  document.querySelectorAll('#secrows button[data-del]').forEach(b=>b.onclick=()=>{
    cur.sections.splice(+b.dataset.del,1); drawSecs(); });
}

async function saveGold(){
  if(!cur) return;
  const body = {sections:cur.sections, reviewed:$('#rev').checked, note:cur.note||''};
  cur = await api('/api/gold/'+cur.vid, body);
  $('#savedmsg').innerHTML = '<span class="saved">saved</span>';
  setTimeout(()=>{ const m=$('#savedmsg'); if(m) m.innerHTML=''; }, 1800);
  loadGold();
}

/* ---------------- compare tab ---------------- */
let ccur = null;

async function loadCompare(){
  const d = await api('/api/compare');
  if(d.error){ $('#clist').innerHTML = `<div class="err">${esc(d.error)}</div>`; return; }
  $('#ccount').textContent = `${d.judged}/${d.total}`;
  const n = $('#cnote');
  if(n) n.innerHTML = `Neither automatic metric settles this. Creator-agreement says the
    proposals lose (F1 0.26 vs 0.45); our own rubric scores prod, the proposals and the
    creators' own chapters all within 0.01. <b>Pick whichever list you would rather see
    on the dance page.</b> Your answers land in <code>_proto/judgments.json</code>.`;
  $('#clist').innerHTML = d.rows.map(r=>`
    <div class="gitem ${r.judged?'done':''} ${ccur===r.ytid?'on':''}" data-yt="${esc(r.ytid)}">
      <span class="tick">${r.judged?'\u2713':'\u25cb'}</span>
      <span class="nm">${esc(r.title||r.dance)}</span>
      <span class="bk">${r.variants.length}</span></div>`).join('')
    || `<div class="empty" style="padding:14px">No proposals yet.</div>`;
  document.querySelectorAll('#clist .gitem').forEach(el=>
    el.onclick=()=>openCompare(el.dataset.yt));
}

async function openCompare(ytid){
  ccur = ytid;
  const d = await api('/api/compare/'+ytid);
  loadCompare();
  if(d.error){ $('#cbody').innerHTML=`<div class="err">${esc(d.error)}</div>`; return; }
  $('#ctitle').textContent = `#${d.vid}  ${d.title||d.dance}`;
  const names = Object.keys(d.sets);
  const cols = names.map(nm=>`
    <div style="min-width:210px;flex:1">
      <div class="lbl" style="margin-bottom:6px;color:${nm.startsWith('prod')?'var(--teal)':
        nm.startsWith('creator')?'var(--violet)':'var(--amber)'}">${esc(nm)}
        &middot; ${d.sets[nm].length}</div>
      <div style="font-family:var(--mono);font-size:12.5px;line-height:1.7">
        ${d.sets[nm].map(s=>`<div><b style="color:var(--dim);font-weight:400">${mmss(s.start)}</b>
           ${esc(s.label)}</div>`).join('') || '<span class="empty">none</span>'}
      </div>
      <button class="sm ${d.judged.winner===nm?'go':''}" style="margin-top:10px"
        data-win="${esc(nm)}">${d.judged.winner===nm?'\u2713 chosen':'This one'}</button>
    </div>`).join('');
  $('#cbody').innerHTML = `
    <div class="runline">
      <span><span class="k">length</span> ${d.dur?mmss(d.dur):'?'}</span>
      <span><span class="k">dance</span> ${esc(d.dance||'')}</span>
      <a href="https://youtu.be/${esc(ytid)}" target="_blank" rel="noreferrer">open on YouTube</a>
      ${d.judged.winner?`<span class="saved">judged: ${esc(d.judged.winner)}</span>`:''}
    </div>
    <div style="display:flex;gap:22px;overflow-x:auto;padding-top:6px">${cols}</div>`;
  document.querySelectorAll('#cbody button[data-win]').forEach(b=>b.onclick=async()=>{
    await api('/api/compare/'+ytid, {winner:b.dataset.win});
    openCompare(ytid);
  });
}

/* ---------------- intake tab ---------------- */
async function loadIntake(){
  const d = await api('/api/intake');
  if(d.error){ $('#irows').innerHTML =
    `<tr><td colspan="9" class="err">${esc(d.error)}</td></tr>`; return; }
  $('#icount').textContent = d.pending ? `${d.pending} pending` : `${d.flagged_live} flagged`;
  $('#itiles').innerHTML = `
    <div class="tile ${d.pending?'weak':''}"><b>${fmt(d.pending)}</b><span class="lbl">Pending</span></div>
    <div class="tile ${d.rejected?'poor':''}"><b>${fmt(d.rejected)}</b><span class="lbl">Rejected</span></div>
    <div class="tile"><b>${fmt(d.flagged_live)}</b><span class="lbl">Live but flagged</span></div>`;
  $('#irows').innerHTML = d.rows.map(r=>`
    <tr>
      <td><span class="src ${r.state==='pending'?'generic':r.state==='rejected'?'none':'legacy'}">${esc(r.state)}</span></td>
      <td class="n">${r.platform==='youtube'
        ? `<a href="https://youtu.be/${esc(r.ytid)}" target="_blank" rel="noreferrer">#${r.vid}</a>`
        : `#${r.vid}`}</td>
      <td class="t">${esc(r.dance)}</td>
      <td class="t">${esc(r.title)}</td>
      <td class="n"><span class="sc"><i><s style="width:${Math.round(r.score*100)}%;
        background:${scColor(r.score)}"></s></i>${r.score.toFixed(2)}</span></td>
      <td class="n">${r.dur?mmss(r.dur):'—'}</td>
      <td class="n">${fmt(r.views)}</td>
      <td class="iss">${esc(r.flags.join(' · ')) || '—'}</td>
      <td style="white-space:nowrap">
        ${r.state!=='approved'?`<button class="sm go" data-a="approve" data-v="${r.vid}">Approve</button>`:''}
        ${r.state!=='rejected'?`<button class="sm danger" data-a="reject" data-v="${r.vid}">Reject</button>`:''}
      </td>
    </tr>`).join('')
    || `<tr><td colspan="9" class="empty" style="padding:16px 12px">
        Nothing awaiting review, and nothing live that the rubric would have held back.</td></tr>`;
  document.querySelectorAll('#irows button[data-a]').forEach(b=>b.onclick=async()=>{
    b.disabled = true;
    await api('/api/intake/'+b.dataset.v, {action:b.dataset.a});
    loadIntake();
  });
}

/* ---------------- signals tab ---------------- */
let sigrows=[], sigcur=null;

async function loadSignals(){
  const d = await api('/api/signals');
  sigrows = d.rows;
  $('#scount').textContent = `${d.ok}${d.failed?` +${d.failed} failed`:''}`;
  $('#stiles').innerHTML = `
    <div class="tile ok"><b>${fmt(d.ok)}</b><span class="lbl">Extracted</span></div>
    <div class="tile ${d.failed?'poor':''}"><b>${fmt(d.failed)}</b><span class="lbl">Failed</span></div>
    <div class="tile"><b>${Math.round(d.footage/3600)}h</b><span class="lbl">Footage read</span></div>
    <div class="tile"><b>${Math.round(d.asr_seconds/60)}m</b><span class="lbl">GPU time</span></div>
    <div class="tile"><b>${d.asr_seconds?Math.round(d.footage/d.asr_seconds):0}x</b><span class="lbl">Realtime</span></div>`;
  $('#slist').innerHTML = sigrows.map(r=>{
    const c = r.counts||{};
    const bad = r.status!=='ok';
    return `<div class="gitem ${bad?'':'done'} ${sigcur===r.ytid?'on':''}" data-yt="${esc(r.ytid)}">
      <span class="tick">${bad?'\u00d7':'\u2713'}</span>
      <span class="nm">${esc(r.ytid)}${bad?` &mdash; ${esc(r.status)}`:
        ` <span class="bk">${c.segments||0} seg &middot; ${c.silence||0} sil &middot; ${c.scenes||0} cuts</span>`}</span>
      <span class="bk">${r.dur?mmss(r.dur):''}</span></div>`;
  }).join('') || `<div class="empty" style="padding:14px">Nothing extracted yet. Run:
      <br><code>python scripts/signals.py --gold</code></div>`;
  document.querySelectorAll('#slist .gitem').forEach(el=>
    el.onclick=()=>openSignal(el.dataset.yt));
}

async function openSignal(ytid){
  sigcur = ytid;
  const rec = sigrows.find(r=>r.ytid===ytid) || {};
  loadSignals();
  if(rec.status && rec.status!=='ok'){
    $('#stitle').textContent = ytid;
    $('#sbody').innerHTML = `<div class="err">${esc(rec.status)}${
      rec.error?`<br>${esc(rec.error)}`:''}</div>`;
    return;
  }
  const d = await api('/api/signals/'+ytid);
  if(d.error){ $('#sbody').innerHTML=`<div class="err">${esc(d.error)}</div>`; return; }
  $('#stitle').textContent = `${ytid} — what was extracted`;

  const dens = (d.density||[]).map(x=>x.v);
  const spark = dens.length ? `<svg viewBox="0 0 ${dens.length*4} 34" preserveAspectRatio="none"
      style="width:100%;height:34px;display:block">
      ${dens.map((v,i)=>`<rect x="${i*4}" y="${34-v*34}" width="3" height="${Math.max(1,v*34)}"
        fill="${v<0.2?'var(--teal)':'var(--border-lt)'}"></rect>`).join('')}
    </svg>` : '<div class="empty">no density data</div>';

  $('#sbody').innerHTML = `
    <div class="runline">
      <span><span class="k">length</span> ${d.dur?mmss(d.dur):'?'}</span>
      <span><span class="k">language</span> ${esc(d.language||'?')} ${d.lang_prob??''}</span>
      <span><span class="k">model</span> ${esc(d.model||'?')} / ${esc(d.device||'?')}</span>
      <span><span class="k">asr</span> ${d.asr_seconds??'?'}s</span>
      <span><span class="k">at</span> ${(d.generated||'').replace('T',' ').replace('+00:00','Z')}</span>
    </div>
    <div class="tiles" style="margin:6px 0 16px">
      <div class="tile"><b>${d.segment_total}</b><span class="lbl">Speech segments</span></div>
      <div class="tile"><b>${d.word_total}</b><span class="lbl">Words</span></div>
      <div class="tile"><b>${d.silence.length}</b><span class="lbl">Silences</span></div>
      <div class="tile"><b>${d.scenes.length}</b><span class="lbl">Scene cuts</span></div>
      <div class="tile"><b>${d.chapters.length}</b><span class="lbl">Chapters</span></div>
      <div class="tile"><b>${d.desc_timestamps.length}</b><span class="lbl">Desc stamps</span></div>
    </div>

    <div class="lbl" style="margin-bottom:5px">Speech density &mdash; teal = likely music / practice</div>
    ${spark}

    ${d.chapters.length?`<div class="lbl" style="margin:18px 0 5px">Creator chapters
      <span style="color:var(--verm)">&mdash; held out, the pipeline must not read these</span></div>
      <div class="hint">${d.chapters.map(c=>`${mmss(c.start)} ${esc(c.label)}`).join(' &middot; ')}</div>`:''}

    <div class="lbl" style="margin:18px 0 5px">Transcript (${d.segment_total} segments)</div>
    <div id="tx">${d.segments.map(x=>
      `<div><b>${mmss(x.start)}</b>${esc(x.text)}</div>`).join('')
      || '<div class="empty">no speech detected</div>'}</div>

    <div class="lbl" style="margin:18px 0 5px">Silences &amp; scene cuts</div>
    <div class="hint">${d.silence.slice(0,40).map(x=>mmss(x.start)+'-'+mmss(x.end)).join(' · ')
      || 'none'}<br>cuts: ${d.scenes.slice(0,40).map(mmss).join(' · ') || 'none'}</div>`;
}

document.addEventListener('keydown', e=>{
  if(tab!=='gold' || !cur) return;
  if(e.target.tagName==='INPUT') return;
  if(e.key==='s'||e.key==='S'){ e.preventDefault(); addSec(now()); }
});

refresh(); setInterval(refresh, 2000);
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(HEALTH):
        print("no _proto/chip_health.json yet — run: python scripts/chip_health.py")
    if not os.path.isdir(GOLD):
        print("no gold set yet — run: python scripts/chip_gold.py select")

    url = f"http://127.0.0.1:{args.port}"
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Chip Refinery dashboard  ->  {url}    (ctrl-c to stop)")
    if not args.no_open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
