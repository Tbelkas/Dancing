"""verify_picks11.py — round 11 embeddability. Cols: name, sid, mid, diff, vid, title. Writes _proto/picks_verified11.tsv."""
import subprocess, sys, json
sys.stdout.reconfigure(encoding="utf-8")
PICKS = [
 ("Haka", 5, 2, 2, "H2deYzImsT0", "AIS | How to do the Haka"),
 ("Sirtaki", 5, 2, 1, "ZR8_A9i5gck", "Learn how to perform Sirtaki (Greek Dance)"),
 ("Tarantella", 5, 2, 2, "5R2flKPaBns", "Italian Tarantella | Dance Lesson with Rosie & Posie"),
 ("Kalbeliya", 5, 2, 2, "SypNK7RtMg8", "Kalbelia dance tutorial: 3 beginner hand movements"),
 ("Mexican Folklorico", 5, 2, 2, "0b8MX4atrRo", "Folklorico Tutorial: Basic Steps Part 1"),
 ("Jarabe Tapatio", 5, 2, 2, "aGnQJLK9lWQ", "EASY Mexican Hat Dance for Kids | El Jarabe Tapatio"),
 ("Dandiya Raas", 17, 13, 1, "l8btRbzpNu4", "Learn 5 Basic Dandiya Steps For Beginners | MGS Dance Studio"),
 ("Bharatanatyam Adavu", 5, 2, 2, "vmwZ9R03bXs", "Bharatanatyam Lesson 1 - Learn adavus - Thattadavu 1 to 8"),
 ("Adowa", 5, 2, 1, "0uWdm5mJmwM", "Adowa Lesson 4"),
 ("Kpanlogo", 13, 11, 2, "41XK66HezWc", "Kpanlogo!"),
 ("Soukous", 13, 11, 2, "RZLJxxdlkHA", "How To Dance Ndombolo Part 2 (Congolese Soukous Tutorial)"),
 ("Kuduro", 13, 11, 2, "oun94VXBvUY", "African dance tutorial from Angola | Manuel Kanza"),
 ("Salsa Enchufla", 1, 1, 2, "3tUcawE0Bhs", "Learn Cuban Salsa: Enchufla"),
 ("Cuban Dile Que No", 1, 1, 1, "Jexcy9LGKjo", "Learn Cuban Salsa: Dile Que No!"),
 ("Tango Boleo", 1, 5, 3, "tfTvgX_vVFA", "Argentine Tango Boleo: Learn How to Do a Boleo (Guide + Exercises)"),
 ("Tango Sacada", 1, 5, 3, "ONC06TWPmOQ", "3 Simple Sacadas For Tango Dancing (Leaders & Followers)"),
 ("Milonga Basics", 1, 5, 2, "BqDj9Kp0nRg", "The 5 Most Common Milonga Steps (Argentine Tango)"),
 ("Cha Cha New York", 1, 1, 2, "cHeTjxD6ddY", "Cha Cha New Yorkers Lesson For Beginners"),
 ("Rumba Walks", 1, 1, 1, "_6As0zdyj0A", "International Rumba Walks Technique with Amanda Besyedin"),
 ("Samba Voltas", 1, 1, 2, "S9Q1WWVVOxE", "How to dance SAMBA VOLTAS | Latin Dance Tutorial"),
 ("Salsa Setenta", 1, 1, 2, "itL9fcP4Q6M", "Salsa Cuban Setenta | Salsa Tutorial for Beginner"),
 ("Bachata Turn", 36, 17, 1, "fSvr8GThrnU", "8 Bachata Turns For The Party! | Beginner Bachata Tutorial"),
 ("Foxtrot Feather Step", 2, 4, 2, "FlgobWrEoUE", "Slow Foxtrot for Beginners Lesson 1 | Feather Step, Three Step"),
 ("Quickstep Lock Step", 2, 4, 2, "fnrvjdtS0rM", "Quickstep Basic Figure - Lock Step | Ballroom Dance"),
 ("Tango Corte", 2, 5, 2, "IVC-ZqZZxuo", "The Corte Check: Tips for Dancing a Back Corte (in Tango)"),
 ("Jive Kicks", 2, 4, 2, "0S-yMpfzurY", "Jive Tutorial: Kicks and Flicks"),
 ("Jitterbug", 6, 4, 1, "0NTa1CXQS6w", "Easy Swing Dance Steps for Beginners - The Jitterbug"),
 ("Collegiate Shag", 6, 4, 2, "dUarTZW1s9M", "Collegiate Shag | Lesson 1 Basic Footwork"),
 ("Boogie Woogie", 6, 4, 2, "hCYSITp-qhg", "SWING DANCE CLASS - Boogie Woogie 1"),
 ("Grand Jete", 4, 2, 3, "qkihwqYWKKE", "How to Do & Improve a Split Leap / Grand Jete"),
 ("Tap Riff", 19, 4, 2, "G-MxzasXGcw", "Beginning Tap Tutorial Series | Learn To Tap | RIFFS"),
 ("Tap Flaps", 19, 4, 2, "FtDDZD5GuL4", "Beginner Tap Dance Steps - FLAPS"),
 ("Tap Scuff", 19, 4, 1, "npglZ4ssbVY", "Beginner Tap Dancing - How to perform a Scuff Step"),
 ("Vogue Spins and Dips", 16, 6, 3, "nCsIqNFfOZw", "Learn to Vogue with NYC Parks: Spins and Dips"),
 ("Chipping", 37, 18, 1, "EUIPhTlOZ9Q", "5 SOCA DANCE MOVES | Tutorial"),
 ("Belly Dance Undulation", 5, 2, 2, "3k2XqPxmJDU", "10-Min Belly Dance TUTORIAL: Undulations"),
 ("Belly Dance Maya", 5, 2, 2, "f1cO5qBHYl4", "Maya and Hip Drop Belly Dance Combinations for Beginners"),
 ("Highland Fling", 5, 2, 2, "GAJQ9jMkNHE", "Learn the Highland Fling"),
 ("Clogging", 5, 2, 1, "eQFNvhxdPXo", "Learn to clog in 5 minutes!!!"),
 ("Hopak", 5, 2, 2, "9l3IMZ20j2k", "Ukrainian Hopak | Dance Lesson with Rosie & Posie"),
]
out = open("_proto/picks_verified11.tsv", "w", encoding="utf-8")
good = bad = 0
for name, sid, mid, diff, vid, title in PICKS:
    try:
        r = subprocess.run(["yt-dlp","--no-warnings","--skip-download","-J",f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout); emb = d.get("playable_in_embed"); dur = d.get("duration") or 0
        print(f"  [{'OK' if emb else 'BAD-EMBED'}] {name:24} {vid}  emb={emb} dur={dur}s")
        if emb:
            good += 1; out.write(f"{name}\t{sid}\t{mid}\t{diff}\t{vid}\t{dur}\t{title}\n")
        else: bad += 1
    except Exception as e:
        bad += 1; print(f"  [ERR ] {name:24} {vid}  {e}")
out.close()
print(f"\nOK={good} BAD={bad} -> _proto/picks_verified11.tsv")
