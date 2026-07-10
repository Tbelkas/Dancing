"""
prep_sections.py <youtube_id>
Fetch + cache metadata and English auto-captions for one video, then write a
condensed timestamped transcript + native chapters to _proto/sec_<id>.txt.
No DB writes. Used to infer topical VideoSegments ("section chips") for tutorials.
"""
import json, os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

vid = sys.argv[1]
os.makedirs("_proto", exist_ok=True)
meta = f"_proto/{vid}.json"
vtt = f"_proto/loose_{vid}.en.vtt" if vid == "1dQxTwiPQkg" else f"_proto/sub_{vid}.en.vtt"

def hhmmss(t):
    return f"{int(t)//60:02d}:{int(t)%60:02d}"

# metadata
if not os.path.exists(meta):
    p = subprocess.run(["yt-dlp", "--skip-download", "--no-warnings", "-J",
                        f"https://www.youtube.com/watch?v={vid}"],
                       capture_output=True, text=True, encoding="utf-8")
    if p.returncode:
        sys.stderr.write((p.stderr or "")[-400:])
        print("FETCH_FAILED")
        raise SystemExit(2)
    open(meta, "w", encoding="utf-8").write(p.stdout)
d = json.load(open(meta, encoding="utf-8"))
title = d.get("title")
dur = d.get("duration") or 0
chapters = [(int(c["start_time"]), c["title"]) for c in (d.get("chapters") or [])]

# captions
if not os.path.exists(vtt):
    subprocess.run(["yt-dlp", "--skip-download", "--no-warnings", "--write-auto-subs",
                    "--sub-langs", "en", "--sub-format", "vtt",
                    "-o", f"_proto/sub_{vid}.%(ext)s",
                    f"https://www.youtube.com/watch?v={vid}"],
                   capture_output=True, text=True, encoding="utf-8")

def parse_vtt(path):
    if not os.path.exists(path):
        return []
    lines = open(path, encoding="utf-8").read().splitlines()
    out, cur, seen = [], None, set()
    def ts(s):
        h, m, rest = s.split(":")
        return int(h) * 3600 + int(m) * 60 + int(float(rest))
    for l in lines:
        m = re.match(r'(\d\d:\d\d:\d\d\.\d\d\d) -->', l)
        if m:
            cur = ts(m.group(1)); continue
        txt = re.sub(r'<[^>]+>', '', l).strip()
        if not txt or '-->' in txt or txt in ('WEBVTT',) or txt.startswith(('Kind:', 'Language:')):
            continue
        if txt in seen:
            continue
        seen.add(txt)
        out.append((cur, txt))
    return out

tr = parse_vtt(vtt)

out = [f"== {vid} ==", f"title : {title}", f"dur   : {hhmmss(dur)} ({dur}s)"]
out.append("native chapters:")
if chapters:
    for st, t in chapters:
        out.append(f"  {hhmmss(st)}  {t}")
else:
    out.append("  (none)")
out.append("")
out.append("transcript:")
if tr:
    for t, txt in tr:
        out.append(f"{hhmmss(t)}  {txt}")
else:
    out.append("  (no captions)")

path = f"_proto/sec_{vid}.txt"
open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
print(f"dur={dur} chapters={len(chapters)} caplines={len(tr)} -> {path}")
