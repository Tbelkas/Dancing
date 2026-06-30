"""verify_picks4.py — embeddability + duration for round-4 picks. Writes _proto/picks_verified4.tsv."""
import subprocess, sys, json
sys.stdout.reconfigure(encoding="utf-8")

PICKS = [
 ("Basic Twerk", 34, 3, "kCjZ6zUFFiU", "How To Twerk For Beginners | 6 Basic Twerk Moves Step-By-Step"),
 ("Twerk Bounce", 34, 3, "wi-eGzxTIjA", "How To Bounce Like The Queen Of New Orleans | Big Freedia's Bounce Etiquette"),
 ("Booty Pop", 34, 3, "UvXu6zGl4VM", "How To Safely Pop Your Booty | Dance Tutorial"),
 ("Jersey Club Bounce", 35, 6, "gO-DLg8AvpY", "How To Bounce | Tutorial Saturday | JerseyClub"),
 ("Jersey Club Top Rock", 35, 6, "ZKL-G-tmPzk", "How To Top Rock 3 in 1 Tutorial | JerseyClub"),
 ("Jersey Club Footwork", 35, 6, "Mlgz1Y_2U1c", "Easy Footwork Combo | JerseyClub Dance | Tutorial Saturday"),
 ("Armageddon (aespa)", 31, 3, "_sYUnFeCpLo", "aespa 'Armageddon' Lisa Rhee Dance Tutorial"),
 ("Super Shy (NewJeans)", 31, 3, "j3a-f9HOAt0", "NewJeans 'Super Shy' Dance Tutorial (Slow Music + Mirrored)"),
 ("Queencard (G-IDLE)", 31, 3, "evITrT-rYd0", "(G)I-DLE 'Queencard' Lisa Rhee Dance Tutorial"),
 ("Love Dive (IVE)", 31, 3, "mOsxB2hjPcU", "IVE 'Love Dive' Lisa Rhee Dance Tutorial"),
 ("OMG (NewJeans)", 31, 3, "tII6apyao80", "NewJeans 'OMG' Lisa Rhee Dance Tutorial"),
 ("Heels Spin", 32, 3, "MuTty4w9yVs", "How to do Basic Turns in Heels | High Heels Dance Beginners"),
 ("Heels Knee Spin", 32, 3, "f2l5YsF31BE", "How to Knee Spin | Mihran Kirakosian"),
 ("Reggaeton Shoulders", 33, 8, "LUmHG_7W7u8", "Reggaeton Upper Body | Chest Isolations"),
 ("Sandungueo", 33, 8, "__GIg_gbTrg", "How To Dance Reggaeton & Perreo! Class 3 - Cuban Reggaeton Choreography"),
 ("Shuffle Spin", 29, 6, "YokxVy9kjAs", "Melbourne Shuffle Spin Tutorial Remade"),
 ("Swiss Drop", 30, 3, "DZmSN6daCUo", "How to do the Swiss Drop - Litefeet Tutorial"),
 ("Hat Trick", 30, 3, "0y4IMbuGnxI", "How to do Hat Tricks - Litefeet Tutorial"),
 ("Sgija", 28, 16, "5dIPmPjLTdw", "Taxi Bounce Step - Sgija Amapiano Dance Challenge"),
 ("Buga", 13, 11, "6brhK6jBVNM", "Buga Dance Tutorial by Idu Dancers"),
 ("Soso", 13, 11, "rwE5ZW-OFnA", "Omah Lay - Soso | Easy TikTok Dance Tutorial"),
 ("Summer Bounce", 14, 12, "aEBAnn8nfyo", "How to Summer Bounce (Step-by-Step Beginner Dancehall) | Jenny JC"),
 ("Gas", 14, 12, "E0jnkqnUqxE", "How to do Gas (Step-by-Step Beginner Dancehall) | Jenny JC"),
 ("Switch Leap", 20, 4, "wiNaZ6UvG5Y", "Jazz Switch Leap (Week 1 Skill Prep)"),
 ("Pique Turn", 20, 4, "1M4pML8H1E4", "Pique & Soutenu Turns Tutorial | natalie danza"),
 ("Cramp Roll", 19, 4, "aOJPYojbZis", "Beginner Tap Dance Steps - Cramp Rolls"),
 ("Death Drop", 16, 6, "PoVzB4JYXSo", "Learn How to Death Drop - Inside Drag"),
 ("Llamada", 18, 10, "lvd8UohuGk0", "How to Dance Bulerias: Llamada Tutorial [Beginners]"),
 ("Contemporary Leap", 7, 2, "rdVe8NTP768", "How To Do A Dance Leap | Beginners"),
 ("Salsa Shines", 1, 1, "C4fsMsgVN0w", "Salsa Shines | Follow Along Solo Footwork Exercises"),
 ("Nae Nae", 10, 3, "eCS_CFcBu5E", "How to Nae Nae ft The Iconic Boyz"),
 ("Two Step", 10, 3, "CSR20afC5mQ", "How to do the Two Step (Hip Hop Dance)"),
 ("Whip", 10, 3, "glIBSSiCM3Y", "Silento 'Watch Me (Whip/Nae Nae)' Dance Tutorial"),
 ("Cat Daddy", 10, 3, "O3I9ww36xF0", "How to Cat Daddy | Dance Tutorial"),
 ("Stanky Legg", 10, 3, "n5zcIYxBHXU", "Hip Hop Dance For Beginners - The Stanky Leg"),
 ("Shuffle Ball Change", 19, 4, "aBNXip8NEhA", "Beginner Tap Dance Steps - Shuffle Ball Change"),
]
out = open("_proto/picks_verified4.tsv", "w", encoding="utf-8")
good = bad = 0
for name, sid, mid, vid, title in PICKS:
    try:
        r = subprocess.run(["yt-dlp", "--no-warnings", "--skip-download", "-J",
                            f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout)
        emb = d.get("playable_in_embed"); dur = d.get("duration") or 0
        print(f"  [{'OK' if emb else 'BAD-EMBED'}] {name:22} {vid}  emb={emb} dur={dur}s")
        if emb:
            good += 1
            out.write(f"{name}\t{sid}\t{mid}\t{vid}\t{dur}\t{title}\n")
        else:
            bad += 1
    except Exception as e:
        bad += 1
        print(f"  [ERR ] {name:22} {vid}  {e}")
out.close()
print(f"\nOK={good} BAD={bad} -> _proto/picks_verified4.tsv")
