"""
signals.py [ytid ...] [--gold] [--queue N] [--force] [--no-scenes] [--keep-media]

Stage 01 of the Chip Refinery: extract every boundary signal a video can offer,
once, and cache it. Everything downstream reads _proto/sig_<ytid>.json and never
touches the network again.

    python scripts/signals.py --gold          the eval set
    python scripts/signals.py --queue 20      top of the priority queue
    python scripts/signals.py FaLYQUa1PDg     one video

Signals collected:
  asr       faster-whisper with word timestamps + VAD. This is the point of the
            stage: YouTube auto-captions are unpunctuated, lossy, and simply absent
            for the TikTok/Instagram rows and most non-English tutorials.
  silence   ffmpeg silencedetect - the beat before "okay, next".
  scenes    ffmpeg scene detection on a 240p stream. A dance tutorial cuts when the
            teaching frame changes, and those cuts are real boundaries.
  density   speech-over-wall-time in a rolling window. A sustained drop is almost
            always the practice-with-music phase, the chip viewers want most.
  chapters  the creator's own markers, from cached metadata.

MEDIA IS TRANSIENT. These are not our videos - we only link to them. Audio and the
240p proxy are written to _proto/media/, used, and deleted. Only derived JSON stays.
Pass --keep-media to debug, never in a batch.

HOLD-OUT: chapters are recorded here but the candidate stage MUST NOT use them for
a video in the gold set (entries carry "holdout": true), or the eval scores itself.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import chip_runstate as rs  # noqa: E402

ROOT = rs.ROOT
PROTO = rs.PROTO
MEDIA = os.path.join(PROTO, "media")
GOLD_AUTO = os.path.join(PROTO, "gold_auto")
GOLD = os.path.join(PROTO, "gold")
HEALTH = os.path.join(PROTO, "chip_health.json")

# Append-only history of every extraction attempt. The run-state log is a 200-entry
# ring buffer, so without this a failure scrolls away and leaves no trace of which
# video died or why - exactly what you need when a chip set comes out wrong.
EXTRACT_LOG = os.path.join(PROTO, "extract_log.jsonl")

MODEL = os.environ.get("CHIP_ASR_MODEL", "distil-large-v3")
DEVICE = os.environ.get("CHIP_ASR_DEVICE", "cuda")
COMPUTE = os.environ.get("CHIP_ASR_COMPUTE", "int8_float16")

SCENE_THRESHOLD = 0.35
DENSITY_WINDOW = 15  # seconds

_model = None


def sig_path(ytid):
    return os.path.join(PROTO, f"sig_{ytid}.json")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(cmd, timeout=1800):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


# ------------------------------------------------------------------- fetching

def fetch_meta(ytid):
    """Cached yt-dlp metadata. Reused from the existing _proto/<ytid>.json cache."""
    path = os.path.join(PROTO, f"{ytid}.json")
    if os.path.exists(path):
        try:
            d = json.load(open(path, encoding="utf-8"))
            if isinstance(d, dict):
                return d
        except (OSError, ValueError):
            pass
    p = run(["yt-dlp", "--skip-download", "--no-warnings", "-J",
             f"https://www.youtube.com/watch?v={ytid}"], timeout=180)
    if p.returncode:
        return {}
    try:
        d = json.loads(p.stdout)
    except ValueError:
        return {}
    open(path, "w", encoding="utf-8").write(p.stdout)
    return d


def fetch_audio(ytid):
    """16 kHz mono wav. Deleted by the caller once signals are extracted."""
    os.makedirs(MEDIA, exist_ok=True)
    out = os.path.join(MEDIA, f"{ytid}.wav")
    if os.path.exists(out):
        return out
    p = run(["yt-dlp", "-x", "--audio-format", "wav",
             "--postprocessor-args", "-ar 16000 -ac 1",
             "--no-warnings", "-q", "-o", os.path.join(MEDIA, f"{ytid}.%(ext)s"),
             f"https://www.youtube.com/watch?v={ytid}"], timeout=1800)
    return out if os.path.exists(out) else None


def fetch_video_proxy(ytid):
    """Smallest usable video stream, for scene cuts only."""
    os.makedirs(MEDIA, exist_ok=True)
    for pat in (f"{ytid}.mp4", f"{ytid}.webm", f"{ytid}.mkv"):
        if os.path.exists(os.path.join(MEDIA, pat)):
            return os.path.join(MEDIA, pat)
    p = run(["yt-dlp", "-f", "worstvideo[height<=240]/worstvideo/worst",
             "--no-warnings", "-q", "-o", os.path.join(MEDIA, f"{ytid}.%(ext)s"),
             f"https://www.youtube.com/watch?v={ytid}"], timeout=1800)
    for pat in (f"{ytid}.mp4", f"{ytid}.webm", f"{ytid}.mkv"):
        cand = os.path.join(MEDIA, pat)
        if os.path.exists(cand):
            return cand
    return None


# ------------------------------------------------------------------- signals

def _add_cuda_dll_dirs():
    """Put the pip-shipped cuBLAS/cuDNN where CTranslate2 will actually find them.

    nvidia-cublas-cu12 / nvidia-cudnn-cu12 ship the DLLs but do not register them,
    so CTranslate2 reports a CUDA device, loads the model happily, and only then
    dies at encode with "cublas64_12.dll is not found".

    It has to be PATH, and it has to happen before ctranslate2 is imported:
    CTranslate2's CUDA DLLs are delay-loaded through the standard Windows search
    order, which consults PATH and ignores os.add_dll_directory(). Getting this
    wrong is the difference between 60x realtime on the GPU and ~2x on the CPU.
    """
    if os.name != "nt":
        return
    import glob
    import site
    dirs = []
    for r in set(site.getsitepackages() + [site.getusersitepackages()]):
        for d in glob.glob(os.path.join(r, "nvidia", "*", "bin")):
            if glob.glob(os.path.join(d, "*.dll")):
                dirs.append(d)
    if dirs:
        os.environ["PATH"] = os.pathsep.join(dirs) + os.pathsep + os.environ.get("PATH", "")


def asr(path):
    """Transcribe with word timestamps. The heavy step; everything else is cheap."""
    global _model, DEVICE, COMPUTE
    _add_cuda_dll_dirs()
    from faster_whisper import WhisperModel
    if _model is None:
        try:
            _model = WhisperModel(MODEL, device=DEVICE, compute_type=COMPUTE)
            # Loading is not proof the GPU works - encode is where CUDA actually
            # gets used, so force one before committing the whole batch to it.
            _model.transcribe(path, without_timestamps=True)[1]
        except Exception as e:  # noqa: BLE001
            if DEVICE == "cpu":
                raise
            rs.log(f"GPU path unavailable ({type(e).__name__}); falling back to CPU")
            print(f"  ! GPU unavailable: {str(e)[:120]}\n  ! falling back to CPU")
            DEVICE, COMPUTE = "cpu", "int8"
            _model = WhisperModel(MODEL, device=DEVICE, compute_type=COMPUTE)
    segs, info = _model.transcribe(
        path, word_timestamps=True, vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    out_segs, out_words = [], []
    for s in segs:
        out_segs.append({"start": round(s.start, 2), "end": round(s.end, 2),
                         "text": s.text.strip()})
        for w in (s.words or []):
            out_words.append([round(w.start, 2), w.word.strip()])
    return {
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "model": MODEL, "device": DEVICE,
        "segments": out_segs, "words": out_words,
    }


def silences(path):
    """Gaps quiet enough to be a deliberate pause between sections."""
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
             "-af", "silencedetect=n=-30dB:d=0.6", "-f", "null", "-"], timeout=900)
    txt = p.stderr or ""
    out, start = [], None
    for m in re.finditer(r"silence_(start|end):\s*(-?[\d.]+)", txt):
        kind, val = m.group(1), float(m.group(2))
        if kind == "start":
            start = val
        elif start is not None:
            out.append({"start": round(max(0.0, start), 2), "end": round(val, 2)})
            start = None
    return out


def scenes(path):
    """Frame-change cuts. Best-effort: a failure here must not lose the ASR."""
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
             "-filter:v", f"select='gt(scene,{SCENE_THRESHOLD})',showinfo",
             "-f", "null", "-"], timeout=1800)
    return sorted({round(float(m.group(1)), 2)
                   for m in re.finditer(r"pts_time:([\d.]+)", p.stderr or "")})


def speech_density(segments, dur):
    """Fraction of each window that is speech. Sustained lows = music/practice."""
    if not dur:
        return []
    out = []
    for w0 in range(0, int(dur), DENSITY_WINDOW):
        w1 = w0 + DENSITY_WINDOW
        spoken = sum(max(0.0, min(s["end"], w1) - max(s["start"], w0))
                     for s in segments if s["end"] > w0 and s["start"] < w1)
        out.append({"t": w0, "v": round(spoken / DENSITY_WINDOW, 3)})
    return out


def desc_timestamps(meta):
    """Timestamp lists people put in descriptions, e.g. '1:23 The basic step'."""
    out = []
    for line in (meta.get("description") or "").splitlines():
        m = re.match(r"\s*(?:(\d+):)?(\d+):(\d{2})\s*[-–—:.)\]]*\s*(.+)", line)
        if m:
            h, mm, ss, label = m.groups()
            t = int(h or 0) * 3600 + int(mm) * 60 + int(ss)
            label = label.strip()[:80]
            if label:
                out.append({"start": t, "label": label})
    return out


# --------------------------------------------------------------------- driver

def write_extract_log(rec):
    os.makedirs(PROTO, exist_ok=True)
    with open(EXTRACT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def summarise(sig, **extra):
    """The one-line record of what a video actually yielded."""
    a = sig.get("asr") or {}
    rec = {
        "ts": _now(), "ytid": sig.get("ytid"), "dur": sig.get("dur"),
        "language": a.get("language"), "lang_prob": a.get("language_probability"),
        "model": a.get("model"), "device": a.get("device"),
        "asr_seconds": sig.get("asr_seconds"),
        "counts": {
            "segments": len(a.get("segments") or []),
            "words": len(a.get("words") or []),
            "silence": len(sig.get("silence") or []),
            "scenes": len(sig.get("scenes") or []),
            "density": len(sig.get("density") or []),
            "chapters": len(sig.get("chapters") or []),
            "desc_ts": len(sig.get("desc_timestamps") or []),
        },
    }
    rec.update(extra)
    return rec


def process(ytid, want_scenes=True, keep_media=False, force=False):
    """Returns (status, record). The record is appended to the extraction log so
    there is a durable answer to 'what did we get out of this video, and when'."""
    out = sig_path(ytid)
    if os.path.exists(out) and not force:
        return "cached", None

    meta = fetch_meta(ytid)
    dur = int(meta.get("duration") or 0)
    made = []
    stages = {}

    rs.stage("audio")
    t0 = time.time()
    wav = fetch_audio(ytid)
    stages["audio"] = round(time.time() - t0, 1)
    if not wav:
        return "no-audio", {"ts": _now(), "ytid": ytid, "status": "no-audio",
                            "dur": dur, "stages": stages,
                            "error": "yt-dlp returned no audio stream"}

    try:
        rs.stage("asr")
        t0 = time.time()
        a = asr(wav)
        asr_secs = round(time.time() - t0, 1)
        stages["asr"] = asr_secs

        rs.stage("silence")
        t0 = time.time()
        sil = silences(wav)
        stages["silence"] = round(time.time() - t0, 1)

        sc = []
        if want_scenes:
            rs.stage("scenes")
            t0 = time.time()
            vid = fetch_video_proxy(ytid)
            if vid:
                made.append(vid)
                try:
                    sc = scenes(vid)
                except subprocess.TimeoutExpired:
                    sc = []
            stages["scenes"] = round(time.time() - t0, 1)

        sig = {
            "ytid": ytid,
            "dur": dur or (int(a["segments"][-1]["end"]) if a["segments"] else 0),
            "generated": _now(),
            "asr_seconds": asr_secs,
            "asr": a,
            "silence": sil,
            "scenes": sc,
            "density": speech_density(a["segments"], dur),
            # Recorded for completeness. HELD OUT for gold-set videos - the
            # candidate stage must not read this when the video is being scored.
            "chapters": [{"start": int(c.get("start_time") or 0),
                          "label": (c.get("title") or "").strip()}
                         for c in (meta.get("chapters") or []) if isinstance(c, dict)],
            "desc_timestamps": desc_timestamps(meta),
        }
        json.dump(sig, open(out, "w", encoding="utf-8"), ensure_ascii=False)
        return "ok", summarise(sig, status="ok", stages=stages,
                               bytes=os.path.getsize(out))
    finally:
        if not keep_media:
            for f in [wav] + made:
                try:
                    os.remove(f)
                except OSError:
                    pass


# ------------------------------------------------------------------ selection

def gold_ytids():
    out = []
    for d in (GOLD_AUTO, GOLD):
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".json") or name.startswith("_"):
                continue
            e = rs._read(os.path.join(d, name), {})
            if e.get("ytid") and e.get("platform") == "youtube":
                out.append(e["ytid"])
    return list(dict.fromkeys(out))


def queue_ytids(n):
    h = rs._read(HEALTH, {})
    out = []
    for r in h.get("videos", []):
        if r.get("platform") == "youtube" and r.get("ytid"):
            out.append(r["ytid"])
        if len(out) >= n:
            break
    return list(dict.fromkeys(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ytids", nargs="*")
    ap.add_argument("--gold", action="store_true")
    ap.add_argument("--queue", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-scenes", action="store_true")
    ap.add_argument("--keep-media", action="store_true")
    ap.add_argument("--reindex", action="store_true",
                    help="rebuild the extraction log from cached sig_*.json files")
    args = ap.parse_args()

    if args.reindex:
        import glob
        have = set()
        if os.path.exists(EXTRACT_LOG):
            for line in open(EXTRACT_LOG, encoding="utf-8"):
                try:
                    have.add(json.loads(line).get("ytid"))
                except ValueError:
                    pass
        added = 0
        for p in sorted(glob.glob(os.path.join(PROTO, "sig_*.json"))):
            ytid = os.path.basename(p)[4:-5]
            if ytid in have:
                continue
            try:
                sig = json.load(open(p, encoding="utf-8"))
            except (OSError, ValueError):
                continue
            # No stage timings to recover - the record is honest about that.
            write_extract_log(summarise(sig, status="ok", reindexed=True,
                                        bytes=os.path.getsize(p),
                                        ts=sig.get("generated") or _now()))
            added += 1
        print(f"reindexed {added} extraction(s) into {EXTRACT_LOG}")
        return

    ids = list(args.ytids)
    if args.gold:
        ids += gold_ytids()
    if args.queue:
        ids += queue_ytids(args.queue)
    ids = [i for i in dict.fromkeys(ids)]
    if not ids:
        ap.error("nothing to do: pass ytids, --gold, or --queue N")

    if not args.force:
        todo = [i for i in ids if not os.path.exists(sig_path(i))]
        print(f"{len(ids)} requested, {len(ids)-len(todo)} already cached, {len(todo)} to do")
        ids = todo
    if not ids:
        print("nothing to extract")
        return

    rs.start_run("signals", total=len(ids))
    counts = {}
    for ytid in ids:
        if not rs.wait_if_paused():
            break
        rs.begin(ytid=ytid, stage="start")
        t0 = time.time()
        rec = None
        try:
            status, rec = process(ytid, want_scenes=not args.no_scenes,
                                  keep_media=args.keep_media, force=args.force)
        except Exception as e:  # noqa: BLE001 - one bad video must not kill the batch
            status = f"error:{type(e).__name__}"
            rec = {"ts": _now(), "ytid": ytid, "status": status,
                   "error": f"{type(e).__name__}: {str(e)[:300]}"}
            rs.log(f"{ytid} failed: {type(e).__name__}: {str(e)[:160]}")
        elapsed = round(time.time() - t0, 1)
        if rec is not None:
            rec.setdefault("status", status)
            rec["elapsed"] = elapsed
            write_extract_log(rec)
        counts[status] = counts.get(status, 0) + 1
        ok = status in ("ok", "cached")
        rs.done_one(ok=ok, msg=f"{ytid} {status} ({elapsed:.0f}s)")
        extra = ""
        if rec and rec.get("counts"):
            c = rec["counts"]
            extra = (f"  {c['segments']:>3} seg  {c['words']:>5} words  "
                     f"{c['silence']:>3} sil  {c['scenes']:>3} cuts")
        print(f"  {ytid:<14} {status:<18} {elapsed:>6.0f}s{extra}")
    rs.finish()

    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if os.path.isdir(MEDIA) and not args.keep_media:
        left = os.listdir(MEDIA)
        if left:
            print(f"warning: {len(left)} media file(s) left in {MEDIA}")
        else:
            shutil.rmtree(MEDIA, ignore_errors=True)


if __name__ == "__main__":
    main()
