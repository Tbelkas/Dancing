"""
chip_ui.py [--port 8787] [--no-open]

Local dashboard for the chip pipeline: what the catalog's chip health looks like,
what the queue is, what a run is doing right now, and a pause button.

    python scripts/chip_ui.py     ->  http://127.0.0.1:8787

Deliberately local and stdlib-only. The pipeline runs on this PC, so its control
plane lives here too — putting it in the Angular admin would mean API endpoints,
a deploy, and needless load on the Pi, none of which buys anything.

Binds to 127.0.0.1 only. It reads the prod connection string (via chip_health)
and can trigger a read-only rescan, but it never writes to the database.

Reads  _proto/chip_health.json  (catalog health + queue, from chip_health.py)
       _proto/chip_run.json     (live run state, from chip_runstate)
Writes _proto/chip_control.json (pause/resume/stop, read by workers)
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chip_runstate as rs  # noqa: E402

ROOT = rs.ROOT
HEALTH = os.path.join(rs.PROTO, "chip_health.json")

_rescan = {"running": False, "error": None}


# ------------------------------------------------------------------ rescan

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
                "scorer": health.get("scorer"),
                "total_videos": len(vids),
                "total_segments": sum(v.get("n", 0) for v in vids),
                "queue": vids[:200],
                "run": rs._read(rs.STATE, {}),
                "control": rs.control(),
                "rescan": dict(_rescan),
            }))
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
.wrap{max-width:1280px;margin:0 auto;padding:0 22px 70px}
a{color:var(--amber);text-decoration:none}
a:hover{text-decoration:underline}
.lbl{font-family:var(--ui);text-transform:uppercase;letter-spacing:.13em;font-size:12px;color:var(--dim)}

header{display:flex;align-items:center;gap:18px;flex-wrap:wrap;
  padding:22px 0 18px;border-bottom:1px solid var(--border);margin-bottom:24px}
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
button.danger:hover:not(:disabled){border-color:var(--verm);color:var(--verm)}
:focus-visible{outline:2px solid var(--amber);outline-offset:2px}

.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:1px;
  background:var(--border);border:1px solid var(--border);margin-bottom:22px}
.tile{background:var(--surface);padding:13px 15px;cursor:pointer;transition:.14s}
.tile:hover{background:var(--surface2)}
.tile.on{background:var(--surface2);box-shadow:inset 2px 0 0 var(--amber)}
.tile b{display:block;font-family:var(--mono);font-size:25px;font-variant-numeric:tabular-nums;line-height:1.2}
.tile.none b{color:var(--verm)} .tile.poor b{color:var(--verm)}
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
.src.generic{color:var(--verm);border-color:rgba(232,80,58,.4)}
.src.none{color:var(--verm);border-color:rgba(232,80,58,.4)}
.src.slice{color:var(--violet);border-color:rgba(139,123,240,.4)}
.src.legacy{color:var(--muted)}
.src.manual{color:var(--green);border-color:rgba(94,207,168,.4)}
.iss{font-family:var(--mono);font-size:11.5px;color:var(--dim);white-space:normal;max-width:250px}

#log{font-family:var(--mono);font-size:12.5px;max-height:230px;overflow-y:auto;
  background:var(--bg);border:1px solid var(--border);padding:11px 13px}
#log div{color:var(--muted);margin-bottom:3px}
#log div b{color:var(--dim);font-weight:400;margin-right:9px}
.empty{color:var(--dim);font-style:italic}
.err{color:var(--verm);font-family:var(--mono);font-size:12.5px;margin-top:9px}
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
</header>

<div class="tiles" id="tiles"></div>

<div class="panel">
  <h2>Current run</h2>
  <div class="body" id="run"></div>
</div>

<div class="panel">
  <h2>Queue &mdash; ranked by reach &times; deficit</h2>
  <div class="tw"><table>
    <thead><tr>
      <th>#</th><th>Video</th><th>Title</th><th>Score</th><th>Chips</th>
      <th>Length</th><th>Views</th><th>Source</th><th>Issues</th>
    </tr></thead>
    <tbody id="rows"></tbody>
  </table></div>
</div>

<div class="panel">
  <h2>Log</h2>
  <div class="body"><div id="log"></div></div>
</div>

</div>
<script>
const $ = s => document.querySelector(s);
let filter = null, state = null;

const fmt = n => (n||0).toLocaleString();
const dur = s => s ? Math.floor(s/60) + ':' + String(s%60).padStart(2,'0') : '—';
const scColor = v => v < 0.35 ? 'var(--verm)' : v < 0.65 ? 'var(--amber)' : 'var(--green)';

async function post(path, body){
  await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                     body: JSON.stringify(body||{})});
  refresh();
}
$('#btn-pause').onclick  = () => post('/api/control', {action:'pause'});
$('#btn-resume').onclick = () => post('/api/control', {action:'run'});
$('#btn-stop').onclick   = () => post('/api/control', {action:'stop'});
$('#btn-rescan').onclick = () => post('/api/rescan');

function drawTiles(s){
  const order = [['none','No chips'],['poor','Poor'],['weak','Weak'],['ok','Adequate']];
  $('#tiles').innerHTML = order.map(([k,label]) => `
    <div class="tile ${k} ${filter===k?'on':''}" data-k="${k}">
      <b>${fmt(s.summary[k])}</b><span class="lbl">${label}</span></div>`).join('')
    + `<div class="tile ${filter===null?'on':''}" data-k="">
         <b>${fmt(s.total_videos)}</b><span class="lbl">All videos</span></div>
       <div class="tile"><b>${fmt(s.total_segments)}</b><span class="lbl">Chips total</span></div>`;
  document.querySelectorAll('.tile[data-k]').forEach(t => t.onclick = () => {
    filter = t.dataset.k || null; draw();
  });
}

function bucket(r){
  if(!r.n) return 'none';
  if(r.score < 0.35) return 'poor';
  if(r.score < 0.65) return 'weak';
  return 'ok';
}

function drawRun(s){
  const r = s.run || {};
  const el = $('#run');
  if(!r.run){
    el.innerHTML = `<div class="empty">No run recorded yet. Workers report here as soon as
      a pipeline stage starts &mdash; the Pause button already takes effect for the next one.</div>`;
    return;
  }
  const pct = r.total ? Math.round(100*(r.done+r.failed)/r.total) : 0;
  const cur = r.current;
  el.innerHTML = `
    <div class="runline">
      <span><span class="k">run</span> ${r.run}</span>
      <span><span class="k">progress</span> ${r.done||0} ok${r.failed?` / ${r.failed} failed`:''} of ${r.total||0}</span>
      <span><span class="k">updated</span> ${(r.updated||'').replace('T',' ').replace('+00:00','Z')}</span>
    </div>
    <div class="bar"><i style="width:${pct}%"></i></div>
    <div class="runline" style="margin-top:11px">
      ${cur ? `<span><span class="k">now</span> #${cur.vid} ${cur.ytid||''}</span>
               <span><span class="k">stage</span> ${cur.stage||'—'}</span>
               ${cur.title?`<span class="k">${cur.title}</span>`:''}`
            : `<span class="empty">idle between videos</span>`}
    </div>`;
}

function drawRows(s){
  let q = s.queue;
  if(filter) q = q.filter(r => bucket(r) === filter);
  $('#rows').innerHTML = q.slice(0,200).map((r,i) => `
    <tr>
      <td class="n" style="color:var(--dim)">${i+1}</td>
      <td class="n">${r.ytid && r.platform==='youtube'
          ? `<a href="https://youtu.be/${r.ytid}" target="_blank" rel="noreferrer">#${r.vid}</a>`
          : `#${r.vid}`}</td>
      <td class="t">${(r.title||r.dance||'').replace(/</g,'&lt;')}</td>
      <td class="n"><span class="sc"><i><s style="width:${Math.round(r.score*100)}%;
          background:${scColor(r.score)}"></s></i>${r.score.toFixed(2)}</span></td>
      <td class="n">${r.n}</td>
      <td class="n">${dur(r.dur)}</td>
      <td class="n">${fmt(r.views)}</td>
      <td><span class="src ${r.source}">${r.source}</span></td>
      <td class="iss">${r.issues.join(' · ')}</td>
    </tr>`).join('')
    || `<tr><td colspan="9" class="empty" style="padding:16px 12px">Nothing in this bucket.</td></tr>`;
}

function drawLog(s){
  const entries = (s.run && s.run.log) || [];
  $('#log').innerHTML = entries.length
    ? entries.slice().reverse().map(e =>
        `<div><b>${(e.t||'').slice(11,19)}</b>${String(e.msg).replace(/</g,'&lt;')}</div>`).join('')
    : `<div class="empty">Nothing logged yet.</div>`;
}

function draw(){
  const s = state; if(!s) return;
  const r = s.run || {};
  const ctl = s.control;
  const st = ctl === 'pause' ? 'paused' : ctl === 'stop' ? 'stopped' : (r.status || 'idle');
  $('#status').textContent = s.rescan.running ? 'rescanning' : st;
  $('#status').className = 'pill ' + st;
  $('#btn-pause').disabled  = ctl === 'pause';
  $('#btn-resume').disabled = ctl === 'run';
  $('#btn-rescan').disabled = s.rescan.running;
  drawTiles(s); drawRun(s); drawRows(s); drawLog(s);
  const old = document.querySelector('.err'); if(old) old.remove();
  if(s.rescan.error){
    const d = document.createElement('div');
    d.className = 'err'; d.textContent = 'Rescan failed: ' + s.rescan.error;
    $('#run').appendChild(d);
  }
}

async function refresh(){
  try{ state = await (await fetch('/api/state')).json(); draw(); }
  catch(e){ $('#status').textContent = 'disconnected'; $('#status').className = 'pill stopped'; }
}
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
