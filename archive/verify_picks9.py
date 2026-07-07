"""verify_picks9.py — round 9 STRETCHING embeddability. Cols: name, styleId(23), difficulty, ytid, title.
Writes _proto/picks_verified9.tsv as: name<TAB>sid<TAB>diff<TAB>vid<TAB>dur<TAB>title (no music)."""
import subprocess, sys, json
sys.stdout.reconfigure(encoding="utf-8")
PICKS = [
 ("Ballet Flexibility Workout", 23, 1, "qsrBmwqNmnk", "Full Body Strength and Flexibility Ballet Workout - Follow-Along"),
 ("Bedtime Stretch", 23, 1, "_9JZuOO9E_w", "10 Minute Evening Stretch for Beginners | Better Sleep & Relaxation"),
 ("Cobra Stretch", 23, 1, "jwoTJNgh8BY", "Cobra Pose For Beginners - Effective stretch for low back pain"),
 ("Camel Pose", 23, 2, "lVmESFGCdYo", "Camel Pose Yoga Tutorial - Yoga Backbends For Beginners!"),
 ("Wheel Pose", 23, 3, "aXpRAJC8ylM", "How To: Wheel Pose for Beginners - Improve Your Backbend"),
 ("Inner Thigh Stretch", 23, 1, "nsHxDciEuOk", "10 Minute Adductor Mobility Routine | Follow Along, With Coaching"),
 ("Deep Squat Mobility", 23, 1, "BTfEFDXp-cw", "Improve Your Squat Mobility Forever (FULL WORKOUT)"),
 ("Chest Opener", 23, 1, "ufrzM7apn1o", "15 Minute Chest and Shoulder Mobility Workout | Follow Along"),
 ("Leg Extension Hold", 23, 2, "JZ7QVHNmAG4", "GET better extensions for ballet and dance"),
 ("Hip CARs", 23, 1, "MO1BPuabR44", "Tabletop Hip CARs - Controlled Articular Rotations Tutorial"),
 ("Daily Full Body Stretch", 23, 1, "COO2S7lPBzA", "10 Minute Total Body Stretch! [Daily Flexibility Routine]"),
 ("PNF Stretching", 23, 2, "ISD7xLUrNJ4", "PNF Stretching Routine & Techniques - How To Contract Hold Relax"),
 ("Cossack Squat", 23, 1, "CXiLxTpF_nA", "Improve Your Cossack Squats for Flexibility & Strength in Hips and Legs"),
 ("Resistance Band Stretch", 23, 1, "JR3Dtyj4Ik4", "12 Min. Resistance Band Mobility Routine | Full Body Flow"),
]
out = open("_proto/picks_verified9.tsv", "w", encoding="utf-8")
good = bad = 0
for name, sid, diff, vid, title in PICKS:
    try:
        r = subprocess.run(["yt-dlp","--no-warnings","--skip-download","-J",f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout); emb = d.get("playable_in_embed"); dur = d.get("duration") or 0
        print(f"  [{'OK' if emb else 'BAD-EMBED'}] {name:28} {vid}  emb={emb} dur={dur}s")
        if emb:
            good += 1; out.write(f"{name}\t{sid}\t{diff}\t{vid}\t{dur}\t{title}\n")
        else: bad += 1
    except Exception as e:
        bad += 1; print(f"  [ERR ] {name:28} {vid}  {e}")
out.close()
print(f"\nOK={good} BAD={bad} -> _proto/picks_verified9.tsv")
