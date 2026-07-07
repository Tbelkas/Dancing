"""trend_search10.py — round 10, GENERAL broad batch (survivors + fresh niche). Cols: name, styleId, musicId, difficulty.
Writes _proto/trend_cand10.tsv."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("_proto", exist_ok=True)
C = [
 # --- survivors from dedup (no existing dance) ---
 ("Viennese Waltz", 2, 2, 2, "viennese waltz basic tutorial beginners"),
 ("Argentine Tango Gancho", 1, 5, 3, "argentine tango gancho tutorial"),
 ("Lindy Hop Swingout", 6, 4, 2, "lindy hop swingout tutorial beginners"),
 ("Balboa Basic", 6, 4, 2, "balboa swing dance tutorial beginners"),
 ("Contemporary Floor Work", 7, 2, 2, "contemporary dance floor work tutorial"),
 ("Lyrical Dance Basics", 7, 2, 1, "lyrical dance for beginners tutorial"),
 ("Jazz Funk Basics", 20, 3, 1, "jazz funk dance tutorial beginners"),
 ("Shuffle Off to Buffalo", 19, 4, 2, "shuffle off to buffalo tap tutorial"),
 ("Tap Wings", 19, 4, 3, "tap dance wings tutorial"),
 ("Belly Dance Hip Drop", 5, 2, 1, "belly dance hip drop tutorial beginners"),
 ("Belly Dance Shimmy", 5, 2, 1, "belly dance shimmy tutorial beginners"),
 ("Bollywood Basics", 17, 13, 1, "bollywood dance basic steps tutorial beginners"),
 ("Irish Jig", 5, 2, 2, "irish dance jig tutorial beginners"),
 ("Hula Basics", 5, 2, 1, "hula dance basic steps tutorial beginners"),
 ("Reggaeton Perreo", 33, 8, 2, "reggaeton perreo basic tutorial"),
 ("Dancehall Gallis", 14, 12, 2, "dancehall gallis dance tutorial"),
 ("Bachata Sensual", 36, 17, 2, "bachata sensual basic tutorial beginners"),
 ("Bachata Footwork", 36, 17, 2, "bachata footwork combination tutorial"),
 ("Heels Choreography", 32, 3, 2, "heels dance choreography tutorial beginner"),
 # --- fresh niche additions ---
 ("Belly Dance Figure 8", 5, 2, 1, "belly dance figure 8 hips tutorial"),
 ("Belly Dance Snake Arms", 5, 2, 1, "belly dance snake arms tutorial"),
 ("Dabke Basics", 5, 2, 1, "dabke dance basic steps tutorial"),
 ("Tahitian Otea", 5, 2, 2, "tahitian dance otea tamure tutorial"),
 ("Capoeira Ginga", 5, 2, 1, "capoeira ginga basic tutorial beginners"),
 ("Tinikling", 5, 2, 1, "tinikling dance steps tutorial"),
 ("Kathak Spins", 5, 2, 2, "kathak dance chakkar spins tutorial"),
 ("Garba", 17, 13, 1, "garba dance steps tutorial beginners"),
 ("Sevillanas", 18, 10, 2, "sevillanas flamenco tutorial beginners"),
 ("Contemporary Leaps", 7, 2, 2, "contemporary dance leaps tutorial"),
 ("Contemporary Tilt", 7, 2, 2, "contemporary tilt jump dance tutorial"),
 ("Roll Down", 7, 2, 1, "contemporary roll down spine tutorial dance"),
 ("Heels Hair Flip", 32, 3, 1, "heels dance hair flip tutorial"),
 ("Heels Hip Sway", 32, 3, 1, "heels dance hip sway tutorial"),
 ("West Coast Swing", 6, 4, 2, "west coast swing basic tutorial beginners"),
 ("Hustle Basics", 6, 6, 1, "hustle dance basic steps tutorial"),
 ("Country Two-Step", 5, 2, 1, "country two step dance tutorial"),
 ("Salsa Suzy Q", 1, 1, 2, "salsa suzy q shine tutorial"),
 ("Bachata Dip", 36, 17, 2, "bachata dip tutorial"),
 ("Kizomba Virgula", 39, 19, 2, "kizomba virgula tutorial"),
 ("Ndombolo", 13, 11, 2, "ndombolo dance tutorial"),
 ("Coupe-Decale", 13, 11, 2, "coupe decale dance tutorial"),
 ("Logobi", 13, 11, 2, "logobi dance tutorial"),
 ("Reggaeton Dura", 33, 8, 2, "reggaeton dura dembow steps tutorial"),
 ("Dancehall Wine", 14, 12, 1, "dancehall wine dance tutorial beginners"),
 ("Shim Sham", 19, 4, 2, "shim sham tap dance tutorial"),
 ("Maxie Ford", 19, 4, 3, "maxie ford tap dance tutorial"),
 ("Paddle and Roll", 19, 4, 2, "paddle and roll tap tutorial"),
 ("Pas de Bourree", 20, 4, 1, "pas de bourree jazz dance tutorial"),
 ("Stag Leap", 20, 4, 3, "stag leap jazz dance tutorial"),
 ("Waltz Natural Turn", 2, 2, 2, "waltz natural turn tutorial ballroom"),
 ("Tango Promenade", 2, 5, 2, "ballroom tango promenade tutorial"),
 ("Samba Whisk", 1, 1, 2, "samba whisk tutorial ballroom"),
 ("Bolero Basics", 1, 1, 1, "bolero dance basic steps tutorial"),
]
out = open("_proto/trend_cand10.tsv", "w", encoding="utf-8")
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
print("\nwrote _proto/trend_cand10.tsv")
