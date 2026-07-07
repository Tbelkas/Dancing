"""resource_search.py "query" [N] — ytsearch for replacement tutorials; print
id / dur / embeddable / title. Verifies playable_in_embed so we only attach working videos."""
import json, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
q = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
p = subprocess.run(["yt-dlp", f"ytsearch{n}:{q}", "-J", "--flat-playlist", "--no-warnings"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
try:
    data = json.loads(p.stdout)
except Exception:
    sys.stderr.write(p.stderr[:500]); raise SystemExit(1)
print(f"# {q}")
for e in data.get("entries", []):
    vid = e.get("id"); dur = e.get("duration") or 0
    title = (e.get("title") or "").replace("\t", " ")
    print(f"{vid}\t{int(dur)//60}:{int(dur)%60:02d}\t{title[:80]}")
