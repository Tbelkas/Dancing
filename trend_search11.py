"""trend_search11.py — round 11, GENERAL broad #2 (fresh niche/world). Cols: name, styleId, musicId, difficulty.
Writes _proto/trend_cand11.tsv."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("_proto", exist_ok=True)
C = [
 ("Haka", 5, 2, 2, "maori haka dance tutorial how to"),
 ("Sirtaki", 5, 2, 1, "sirtaki greek dance tutorial zorba"),
 ("Tarantella", 5, 2, 2, "tarantella italian dance tutorial steps"),
 ("Kalbeliya", 5, 2, 2, "kalbeliya rajasthani dance tutorial"),
 ("Mexican Folklorico", 5, 2, 2, "ballet folklorico mexican dance tutorial basic steps"),
 ("Jarabe Tapatio", 5, 2, 2, "jarabe tapatio mexican hat dance tutorial"),
 ("Dandiya Raas", 17, 13, 1, "dandiya raas sticks tutorial steps"),
 ("Bharatanatyam Adavu", 5, 2, 2, "bharatanatyam adavu basic steps tutorial"),
 ("Flamenco Buleria", 18, 10, 3, "flamenco buleria tutorial beginners"),
 ("Adowa", 5, 2, 1, "adowa ghanaian dance tutorial"),
 ("Kpanlogo", 13, 11, 2, "kpanlogo ghana dance tutorial"),
 ("Soukous", 13, 11, 2, "soukous congolese dance tutorial"),
 ("Kuduro", 13, 11, 2, "kuduro dance tutorial angola"),
 ("Salsa Enchufla", 1, 1, 2, "salsa cubana enchufla tutorial"),
 ("Cuban Dile Que No", 1, 1, 1, "casino salsa dile que no tutorial"),
 ("Tango Boleo", 1, 5, 3, "argentine tango boleo tutorial"),
 ("Tango Sacada", 1, 5, 3, "argentine tango sacada tutorial"),
 ("Milonga Basics", 1, 5, 2, "milonga argentine tango tutorial basics"),
 ("Cha Cha New York", 1, 1, 2, "cha cha new york step tutorial"),
 ("Rumba Walks", 1, 1, 1, "rumba walks tutorial latin ballroom"),
 ("Samba Voltas", 1, 1, 2, "samba voltas tutorial latin"),
 ("Salsa Setenta", 1, 1, 2, "salsa cubana setenta tutorial"),
 ("Bachata Turn", 36, 17, 1, "bachata ladies turn tutorial"),
 ("Foxtrot Feather Step", 2, 4, 2, "foxtrot feather step tutorial"),
 ("Quickstep Lock Step", 2, 4, 2, "quickstep lock step tutorial"),
 ("Tango Corte", 2, 5, 2, "ballroom tango corte tutorial"),
 ("Jive Kicks", 2, 4, 2, "jive kicks and flicks tutorial"),
 ("Jitterbug", 6, 4, 1, "jitterbug basic step tutorial beginners"),
 ("Collegiate Shag", 6, 4, 2, "collegiate shag tutorial beginners"),
 ("Boogie Woogie", 6, 4, 2, "boogie woogie dance tutorial basic"),
 ("Grand Jete", 4, 2, 3, "grand jete tutorial ballet leap"),
 ("Tap Riff", 19, 4, 2, "tap dance riff tutorial"),
 ("Falap", 19, 4, 2, "flap tap dance tutorial beginners"),
 ("Tap Scuff", 19, 4, 1, "tap scuff step tutorial"),
 ("Dime Stop", 10, 3, 2, "dime stop popping tutorial"),
 ("Fresno", 10, 3, 1, "fresno popping tutorial beginners"),
 ("Boogaloo", 10, 3, 2, "boogaloo dance tutorial popping"),
 ("Strobing", 10, 3, 2, "strobing dance tutorial"),
 ("Animation", 10, 3, 3, "animation dance style tutorial"),
 ("Chicago Footwork", 10, 3, 2, "chicago footwork dance tutorial"),
 ("Krump Buck", 15, 3, 2, "krump buck tutorial beginners"),
 ("Vogue Spins and Dips", 16, 6, 3, "vogue spins and dips tutorial"),
 ("Palance", 37, 18, 1, "palance soca dance tutorial"),
 ("Chipping", 37, 18, 1, "soca chipping tutorial dance"),
 ("Belly Dance Undulation", 5, 2, 2, "belly dance undulation tutorial"),
 ("Belly Dance Maya", 5, 2, 2, "belly dance maya hip tutorial"),
 ("Highland Fling", 5, 2, 2, "highland fling scottish dance tutorial"),
 ("Clogging", 5, 2, 1, "clogging dance basic steps tutorial"),
 ("Hopak", 5, 2, 2, "hopak ukrainian dance tutorial"),
]
out = open("_proto/trend_cand11.tsv", "w", encoding="utf-8")
for name, sid, mid, diff, q in C:
    try:
        r = subprocess.run(["yt-dlp", "--no-warnings", "--flat-playlist", "--print",
                            "%(id)s||%(title)s||%(duration)ss", f"ytsearch5:{q}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        lines = [l for l in r.stdout.splitlines() if l][:5]
    except Exception as e:
        lines = [f"ERR||{e}||"]
    print(f"### {name}  [style {sid} music {mid} diff {diff}]")
    for l in lines:
        print("   " + l)
    out.write(f"{name}\t{sid}\t{mid}\t{diff}\t" + " ;; ".join(lines) + "\n")
out.close()
print("\nwrote _proto/trend_cand11.tsv")
