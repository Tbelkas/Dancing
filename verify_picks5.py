"""verify_picks5.py — embeddability + duration for round-5 picks. Writes _proto/picks_verified5.tsv."""
import subprocess, sys, json
sys.stdout.reconfigure(encoding="utf-8")

PICKS = [
 ("Bachata Basic", 36, 17, "DmNeYqTD_pM", "How To Dance Bachata For Beginners - The Basic Steps"),
 ("Bachata Side Step", 36, 17, "ujxWTERpdXw", "Bachata Footwork Tutorial - Side Step + Combos | Marius&Elena"),
 ("Bachata Turn", 36, 17, "Wpyw-TQ3voI", "3 Awesome Arm Styling Moves | Bachata Lady Styling Tutorial"),
 ("Soca Wine", 37, 18, "G3Tg9568VUA", "How to Wine (Easy to Learn Steps) | Jenny JC"),
 ("Soca Wave", 37, 18, "Rqgt1ja9g98", "How To Dance Soca | 5 Ways To Wave Your Rag"),
 ("Soca Bumper", 37, 18, "uaer2MzDXK8", "Bumper Murderer Tutorial - Kerwin Du Bois | Choreography by GeishaRene"),
 ("Passinho", 38, 6, "ih9s_gNKGwA", "How to Brazilian Funk Dance Tutorial"),
 ("Rebolation", 38, 6, "psqA5m39e6U", "Tutorial Rebolation"),
 ("Beat Drop", 38, 6, "kgrQuQg0i1U", "How To Make Powerful Drops In Brazilian Funk With WYKO"),
 ("Spicy (aespa)", 31, 3, "P7wB8YnxT_I", "aespa 'Spicy' Dance Tutorial | Explanation + Mirrored"),
 ("Hype Boy (NewJeans)", 31, 3, "kZjn3T-bAKM", "NewJeans 'Hype Boy' Dance Tutorial | Explained + Mirrored"),
 ("Ditto (NewJeans)", 31, 3, "SLdlz6yYObE", "NewJeans 'Ditto' Lisa Rhee Dance Tutorial"),
 ("Kitsch (IVE)", 31, 3, "sOqjShHNMmY", "IVE 'Kitsch' Lisa Rhee Dance Tutorial"),
 ("Antifragile (LE SSERAFIM)", 31, 3, "IZxVv1iYKjA", "LE SSERAFIM 'Antifragile' Full Dance Tutorial - Slow Music + Mirror"),
 ("One Leg Get Back", 35, 6, "DhLjVey4N_g", "One Leg Get Back Tutorial | JerseyClub Dance"),
 ("KB Bounce", 35, 6, "2b9Qm109jRE", "How To KB Bounce | Tutorial Saturday | JerseyClub"),
 ("Sharp Bounce", 35, 6, "h7Deco13cmI", "2 Easy Sharp Bounce Combos | JerseyClub | Tutorial Saturday"),
 ("Heels Strut", 32, 3, "t2j9W546v_w", "How to Strut - 3 Ways to Walk Like Beyonce"),
 ("Heels Chair Dance", 32, 3, "j8OAVjymZNM", "Burlesque Chair Dance Tutorial | Chair Dance Choreography"),
 ("Heel Twerk", 34, 3, "Ih1mgTbEeQc", "Twerk in Heels | Beginner Tutorial"),
 ("Ke Star", 28, 16, "u9icE491yV4", "Amapiano Hit Ke Star Dance | Katlehong Kids"),
 ("Phuze", 28, 16, "ybG3Wkwx_p8", "Phuze Dance Cover | Amapiano Concept | Hope Ramafalo"),
 ("Calm Down", 13, 11, "U6oiHC8iPZ4", "Rema - Calm Down Dance Tutorial"),
 ("Unavailable", 13, 11, "ffPohPMWvUs", "Davido - Unavailable ft Musa Keys | TikTok Dance Tutorial Step by Step"),
 ("Buffalo", 19, 4, "kPMiv_srRwg", "Learn To Tap Dance | Buffalo | Easy Tap Step for Beginners"),
 ("Jab", 15, 3, "8zv76-Mj7Cc", "How To Krump Jabs"),
 ("Cumbia", 1, 1, "6ncfaU4RiSQ", "How to Dance Cumbia | Beginner's Tutorial"),
 ("Attitude Turn", 7, 2, "Ge35LjHfLOY", "Attitude Turn Tutorial"),
 ("Salsa Cross Body Lead", 1, 1, "hl-S_ovXl0c", "Salsa Beginners - Cross Body Lead for the Absolute Beginner"),
 ("Bachata Dip", 36, 17, "gsNsvL7J8Y8", "Bachata Dip - The Bachata Move Everyone Wants To Do"),
 ("Krump Chest Pop", 15, 3, "dXa1MoiLV1E", "Krump Drills (Chest Pops) | by Tighteyex"),
 ("Soca Footwork", 37, 18, "EUIPhTlOZ9Q", "5 Soca Dance Moves | Tutorial"),
 ("Wing", 19, 4, "0BkFwdca9vU", "Tap Dance TAP-torial: Learn Wings"),
]
out = open("_proto/picks_verified5.tsv", "w", encoding="utf-8")
good = bad = 0
for name, sid, mid, vid, title in PICKS:
    try:
        r = subprocess.run(["yt-dlp", "--no-warnings", "--skip-download", "-J",
                            f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout)
        emb = d.get("playable_in_embed"); dur = d.get("duration") or 0
        print(f"  [{'OK' if emb else 'BAD-EMBED'}] {name:26} {vid}  emb={emb} dur={dur}s")
        if emb:
            good += 1
            out.write(f"{name}\t{sid}\t{mid}\t{vid}\t{dur}\t{title}\n")
        else:
            bad += 1
    except Exception as e:
        bad += 1
        print(f"  [ERR ] {name:26} {vid}  {e}")
out.close()
print(f"\nOK={good} BAD={bad} -> _proto/picks_verified5.tsv")
