"""verify_picks8.py — round 8 STRETCHING embeddability. Cols: name, styleId(23), difficulty, ytid, title.
Writes _proto/picks_verified8.tsv as: name<TAB>sid<TAB>diff<TAB>vid<TAB>dur<TAB>title (no music)."""
import subprocess, sys, json
sys.stdout.reconfigure(encoding="utf-8")
PICKS = [
 ("Deep Splits Stretch", 23, 2, "GFuhJQloXu8", "15 Minute Deep Stretch for Splits"),
 ("Full Body Mobility Flow", 23, 1, "F4oF_vXjIV8", "15 Min Full Body Mobility Flow Routine (FOLLOW ALONG)"),
 ("Hip Flexor Stretch", 23, 1, "Z04ldN6WnRY", "20 Minute Hip Flexor Flexibility Routine (FOLLOW ALONG)"),
 ("Frog Stretch", 23, 2, "BVVCAZrIjXY", "How To Do Frog Pose | Benefits, Breakdown, Mobility Exercises"),
 ("Pigeon Pose", 23, 1, "46phRH_09yM", "How to do PIGEON Pose for beginners (Hip External Rotation)"),
 ("Lizard Pose", 23, 1, "14rq7Gfm4aM", "Lizard Pose: Achieve Optimal Hip Mobility"),
 ("Couch Stretch", 23, 1, "WKo4APrwfXQ", "Couch Stretch Progressions: Beginner To Advanced (Hip Flexors & Quads)"),
 ("Calf Stretch", 23, 1, "uQohpNbzyUg", "10 min CALF STRETCHES for Flexibility (Easy Follow Along)"),
 ("IT Band & Glute Stretch", 23, 1, "WbDS4XE5SKs", "Yoga for IT Band - 10 min Stretches for Iliotibial Band"),
 ("Lower Back Relief", 23, 1, "7V-EbW-DmN0", "12 Min Lower Back Pain Stretches - Exercises for Pain Relief"),
 ("Neck & Traps Release", 23, 1, "4bRmTmd9lmM", "15 min Tight Neck, Traps & Shoulders Follow Along"),
 ("Wrist & Forearm Mobility", 23, 1, "7xY-JrvtnC0", "Wrist Mobility Follow Along Routine: 6 Simple Wrist Exercises"),
 ("Thoracic Rotation", 23, 1, "w-6awp5LT6k", "12 Minute T-Spine Mobility Workout (Follow Along)"),
 ("Morning Mobility", 23, 1, "t2jel6q1GRk", "Quick Morning Stretching Routine For Flexibility & Mobility"),
 ("Flexibility for High Kicks", 23, 2, "EiRLRiqsQJk", "Follow Along Kick Exercises for Dance [Improve in 5 Minutes]"),
 ("Jefferson Curl", 23, 2, "y_APeWo643w", "Jefferson Curl | Do It Right!"),
]
out = open("_proto/picks_verified8.tsv", "w", encoding="utf-8")
good = bad = 0
for name, sid, diff, vid, title in PICKS:
    try:
        r = subprocess.run(["yt-dlp","--no-warnings","--skip-download","-J",f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout); emb = d.get("playable_in_embed"); dur = d.get("duration") or 0
        print(f"  [{'OK' if emb else 'BAD-EMBED'}] {name:26} {vid}  emb={emb} dur={dur}s")
        if emb:
            good += 1; out.write(f"{name}\t{sid}\t{diff}\t{vid}\t{dur}\t{title}\n")
        else: bad += 1
    except Exception as e:
        bad += 1; print(f"  [ERR ] {name:26} {vid}  {e}")
out.close()
print(f"\nOK={good} BAD={bad} -> _proto/picks_verified8.tsv")
