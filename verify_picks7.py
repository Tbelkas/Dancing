"""verify_picks7.py — round 7 STRETCHING embeddability. Cols: name, styleId(23), difficulty, ytid, title.
Writes _proto/picks_verified7.tsv as: name<TAB>sid<TAB>diff<TAB>vid<TAB>dur<TAB>title (no music)."""
import subprocess, sys, json
sys.stdout.reconfigure(encoding="utf-8")
PICKS = [
 ("Front Splits", 23, 2, "LsiGCC5Q-QM", "How to Get Your Front Splits Fast | 15 Minute Front Split Routine (Follow Along)"),
 ("Middle Splits", 23, 2, "hsNvqUmCAAo", "The Only Middle Split Video You'll Ever Need"),
 ("Oversplits", 23, 3, "EWExxHIy5I4", "IMPROVE YOUR OVERSPLITS: FOLLOW-ALONG TUTORIAL"),
 ("Backbend", 23, 2, "dVhfW_PqzrQ", "How to do a Backbend Fast! Back Flexibility Stretches for Beginners"),
 ("Bridge Pose", 23, 1, "tSvmWU-0Zo0", "How To BACK BRIDGE For Beginners (FLEXIBLE & STRONG)"),
 ("Back Flexibility", 23, 2, "xsO5uFkqoLg", "BACK FLEXIBILITY | Follow along stretching routine | Based on SCIENCE"),
 ("Hamstring Stretch", 23, 1, "Qp3Vl7b_y6o", "Unlock Your Hamstrings! (FOLLOW ALONG)"),
 ("Hip Openers", 23, 1, "jj2AAH6jbHk", "12 Minute Hip Mobility Routine (FOLLOW ALONG)"),
 ("Pancake Stretch", 23, 2, "CHRUb43S6RM", "How to Pancake Stretch (Beginner to Advanced)"),
 ("Needle Scale", 23, 3, "delJW9_dXJw", "How to do a Needle / Scorpion! Stretches for Flexibility"),
 ("Shoulder Mobility", 23, 1, "_3FoSnnLRuU", "12 min Shoulder Mobility Stretches & Exercises (Follow Along)"),
 ("Ankle & Foot Mobility", 23, 1, "xS80ZhaDrzA", "Dance Foot Exercises & Stretches For Strength, Flexibility & Ballet Pointe"),
 ("Dynamic Warm-Up", 23, 1, "xQRnnYYSBF0", "Best Warm Up & Stretch before Dance (Hiphop Basics + Jazz stretch routine)"),
 ("Cool-Down Stretch", 23, 1, "VQzWOcS0XKI", "Stretching for AFTER you dance (cool down stretch)"),
 ("Spine Mobility", 23, 1, "GMKt9cDPVO8", "Unlock Your Spine! Complete Stretching Routine [Follow Along]"),
]
out = open("_proto/picks_verified7.tsv", "w", encoding="utf-8")
good = bad = 0
for name, sid, diff, vid, title in PICKS:
    try:
        r = subprocess.run(["yt-dlp","--no-warnings","--skip-download","-J",f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout); emb = d.get("playable_in_embed"); dur = d.get("duration") or 0
        print(f"  [{'OK' if emb else 'BAD-EMBED'}] {name:24} {vid}  emb={emb} dur={dur}s")
        if emb:
            good += 1; out.write(f"{name}\t{sid}\t{diff}\t{vid}\t{dur}\t{title}\n")
        else: bad += 1
    except Exception as e:
        bad += 1; print(f"  [ERR ] {name:24} {vid}  {e}")
out.close()
print(f"\nOK={good} BAD={bad} -> _proto/picks_verified7.tsv")
