"""
chip_runstate.py — shared run state + pause control for the chip pipeline.

Every long-running stage (signals, candidates, propose, visual, gate) imports
this instead of inventing its own progress reporting, so scripts/chip_ui.py has
one file to read and one file to write.

    import chip_runstate as rs

    rs.start_run("signals", total=len(queue))
    for v in queue:
        if not rs.wait_if_paused():      # blocks while paused; False = stop
            break
        rs.begin(vid=v.id, ytid=v.ytid, stage="asr")
        ...
        rs.done_one(ok=True)
    rs.finish()

Two files, both in _proto/ and both disposable:
  chip_run.json      written by the worker, read by the dashboard
  chip_control.json  written by the dashboard, read by the worker

Pause is cooperative and checked between videos rather than mid-transcode —
killing ffmpeg or faster-whisper halfway just means redoing that video, and a
half-written signals cache is worse than a slow stop.
"""
import json
import os
import tempfile
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO = os.path.join(ROOT, "_proto")
STATE = os.path.join(PROTO, "chip_run.json")
CONTROL = os.path.join(PROTO, "chip_control.json")

LOG_KEEP = 200


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_atomic(path, obj):
    """Write via temp + replace so the dashboard never reads a half-written file.

    os.replace is atomic on Windows but not uncontended: if any other process has the
    destination open even for reading, it fails with WinError 5 rather than waiting.
    That happens routinely now - the dashboard polls this file every 2s while two
    pipeline stages write to it - and an unguarded replace turned a progress update
    into a crashed extraction, killing the video that happened to be in flight.

    Progress reporting must never be able to fail the work it is reporting on, so a
    contended write is retried briefly and then given up on. A dropped run-state
    update costs a stale line in the dashboard; a raised one costs a video.
    """
    os.makedirs(PROTO, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=PROTO, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1)
        for attempt in range(6):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == 5:
                    break
                time.sleep(0.05 * (attempt + 1))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    # Gave up: drop the update rather than propagating it into the caller.
    if os.path.exists(tmp):
        os.unlink(tmp)


def _read(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


# ------------------------------------------------------------------- control

def control():
    """'run' | 'pause' | 'stop' — whatever the dashboard last asked for."""
    return _read(CONTROL, {}).get("action", "run")


def set_control(action):
    """Used by the dashboard. Workers should not call this."""
    if action not in ("run", "pause", "stop"):
        raise ValueError(action)
    _write_atomic(CONTROL, {"action": action, "at": _now()})
    return action


def wait_if_paused(poll=2.0):
    """Block while paused. Returns False if a stop was requested."""
    was_paused = False
    while True:
        c = control()
        if c == "stop":
            _patch(status="stopped")
            log("stop requested - halting after the current video")
            return False
        if c != "pause":
            if was_paused:
                _patch(status="running")
                log("resumed")
            return True
        if not was_paused:
            was_paused = True
            _patch(status="paused")
            log("paused")
        time.sleep(poll)


# --------------------------------------------------------------- run reporting

def _state():
    return _read(STATE, {})


def _patch(**fields):
    s = _state()
    s.update(fields)
    s["updated"] = _now()
    _write_atomic(STATE, s)
    return s


def start_run(name, total=0):
    # A fresh run must not inherit a stale pause from the last one.
    set_control("run")
    _write_atomic(STATE, {
        "run": name, "status": "running", "started": _now(), "updated": _now(),
        "total": total, "done": 0, "failed": 0, "current": None, "log": [],
    })
    log(f"started {name} - {total} video(s) queued")


def begin(vid=None, ytid=None, stage=None, title=None):
    _patch(current={"vid": vid, "ytid": ytid, "stage": stage,
                    "title": title, "since": _now()})


def stage(name):
    """Update just the stage of the video already in progress."""
    s = _state()
    cur = s.get("current") or {}
    cur["stage"] = name
    _patch(current=cur)


def done_one(ok=True, msg=None):
    s = _state()
    _patch(done=s.get("done", 0) + (1 if ok else 0),
           failed=s.get("failed", 0) + (0 if ok else 1),
           current=None)
    if msg:
        log(msg)


def log(msg):
    s = _state()
    entries = s.get("log", [])
    entries.append({"t": _now(), "msg": str(msg)})
    _patch(log=entries[-LOG_KEEP:])


def finish(status=None):
    s = _state()
    final = status or ("stopped" if s.get("status") == "stopped" else "done")
    _patch(status=final, current=None)
    log(f"run finished: {final} "
        f"({s.get('done', 0)} ok, {s.get('failed', 0)} failed)")
    set_control("run")
