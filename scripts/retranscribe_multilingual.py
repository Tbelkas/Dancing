"""
retranscribe_multilingual.py [--limit N] [--dry-run] [apply]

Re-transcribe the non-English videos with a model that can actually hear them.

    python scripts/retranscribe_multilingual.py            what would be redone
    python scripts/retranscribe_multilingual.py apply      redo it

THE PROBLEM
-----------
signals.py runs distil-large-v3, and Distil-Whisper is English-only. It does not fail on
other languages - it hallucinates plausible English and reports language "en" with high
confidence anyway. Every one of the 334 transcripts cached before this script existed
claims English, for a catalogue carrying Afro, K-pop, Latin and Indian classical content.

A Korean tap lesson came back as "No! Now! All right right Right Right Who Me TapDens".

That is not merely a bad transcript. Everything downstream treats it as a real one:
chip labels get inferred from words nobody said, and any rule scoring dance vocabulary
is really scoring "is this English".

WHY TARGETED AND NOT WHOLESALE
------------------------------
The obvious response is to switch CHIP_ASR_MODEL to large-v3 and re-transcribe the lot.
Measured first instead: of 849 videos with cached metadata, 635 declare English, 169
declare nothing, and 57 declare a non-English language. So this is a 7% problem, not a
50% one, and re-running 800 videos through a slower multilingual model to fix 57 would
cost hours to change almost nothing.

The declared language is noisy in both directions - it is the uploader's channel
setting, not the audio, so a Bachata tutorial taught in English can be marked "nl". That
is fine here: a multilingual model transcribes English correctly too, so a false
positive costs one re-run and nothing else. False negatives (a non-English video
declaring "en") are the ones this cannot catch, and they stay on the known-limitation
list rather than being guessed at.

Writes sig_<ytid>.json exactly as signals.py does, so everything downstream is unchanged
and simply reads better data. The old English-only transcript is kept alongside as
sig_<ytid>.en-only.json rather than deleted, because the two disagreeing is the evidence
that this ran.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO = os.path.join(ROOT, "_proto")
LIST = os.path.join(PROTO, "nonenglish.txt")

MULTILINGUAL = "large-v3"


def targets():
    if not os.path.exists(LIST):
        print(f"no {LIST} - nothing to do")
        return []
    return [l.strip() for l in open(LIST, encoding="utf-8") if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apply", nargs="?")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--batch", type=int, default=4)
    args = ap.parse_args()

    ids = targets()
    if args.limit:
        ids = ids[:args.limit]
    if not ids:
        return

    existing = [i for i in ids
                if os.path.exists(os.path.join(PROTO, f"sig_{i}.json"))]
    print(f"{len(ids)} declared non-English video(s); {len(existing)} already have an "
          f"English-only transcript that would be replaced")
    print(f"model: {MULTILINGUAL} (slower than distil-large-v3, and multilingual)")
    if not args.apply:
        print("\ndry run - pass 'apply' to re-transcribe")
        return

    # Copy the old transcript aside; do NOT remove it yet. The first version of this
    # moved every file out of the way before running, then the run timed out - and two
    # videos were left with no current transcript at all. Preserve first, overwrite with
    # --force, and put the original back if nothing new arrived.
    for i in existing:
        dst = os.path.join(PROTO, f"sig_{i}.en-only.json")
        if not os.path.exists(dst):
            shutil.copy2(os.path.join(PROTO, f"sig_{i}.json"), dst)

    env = dict(os.environ)
    env["CHIP_ASR_MODEL"] = MULTILINGUAL

    # Fetch the model once, outside the per-video budget. large-v3 is ~3GB and on a cold
    # cache the download ran into the transcription timeout, which then read as "this
    # video is too slow" - it was not, it was the first-run download.
    print("warming the model (first run downloads ~3GB)...", flush=True)
    warm = subprocess.run(
        [sys.executable, "-c",
         "from faster_whisper import WhisperModel;"
         f"WhisperModel('{MULTILINGUAL}', device='cuda', compute_type='int8_float16')"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT, env=env, timeout=3600)
    print("  model ready" if warm.returncode == 0
          else f"  warm failed: {(warm.stderr or '')[-200:]}", flush=True)

    t0, done, langs = time.monotonic(), 0, {}
    for i in range(0, len(ids), args.batch):
        chunk = ids[i:i + args.batch]
        try:
            p = subprocess.run([sys.executable,
                                os.path.join(ROOT, "scripts", "signals.py"),
                                "--force", "--"] + chunk,
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", cwd=ROOT, env=env,
                               timeout=900 * len(chunk))
            sys.stdout.write(p.stdout or "")
        except subprocess.TimeoutExpired:
            print(f"  batch timed out - restoring originals for {' '.join(chunk)}",
                  flush=True)
        # Anything that did not get a fresh transcript keeps the one it had.
        for ytid in chunk:
            sp = os.path.join(PROTO, f"sig_{ytid}.json")
            bak = os.path.join(PROTO, f"sig_{ytid}.en-only.json")
            if not os.path.exists(sp) and os.path.exists(bak):
                shutil.copy2(bak, sp)
                print(f"  {ytid:<14} restored the English-only transcript", flush=True)
        for ytid in chunk:
            sp = os.path.join(PROTO, f"sig_{ytid}.json")
            if not os.path.exists(sp):
                continue
            try:
                lang = (json.load(open(sp, encoding="utf-8")).get("asr")
                        or {}).get("language") or "?"
            except (OSError, ValueError):
                lang = "?"
            langs[lang] = langs.get(lang, 0) + 1
        done += len(chunk)
        print(f"[{done}/{len(ids)}]  {(time.monotonic()-t0)/60:.0f}m working  "
              f"languages so far: "
              + "  ".join(f"{k}={v}" for k, v in sorted(langs.items())), flush=True)

    print("\nlanguages detected:", "  ".join(f"{k}={v}" for k, v in sorted(langs.items())))
    print("If these are still all 'en', the model did not change - check CHIP_ASR_MODEL.")
    print("Re-run scripts/verify_intake.py over anything affected.")


if __name__ == "__main__":
    main()
