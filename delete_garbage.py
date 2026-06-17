"""
Delete non-dance entries from the database:
- Tutorial chapter titles ("How to enroll", "Practice with music", etc.)
- Numbered/lettered sequence steps ("G Slide", "15 Step", "Sec 1 Breakdown")
- Instructor names ("Gaby Cook & Aj Howard")
- Instructional prompts ("start with our feet hip width")
- Duplicate ALL-CAPS entries already covered by lowercase versions
"""
import re, json, time
import urllib.request, urllib.error

API_BASE = "https://dance-api.takelord.com/api"

def api(method, path, body=None, token=None):
    url = API_BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token: req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            try: return json.loads(r.read()), r.status
            except: return None, r.status
    except urllib.error.HTTPError as e:
        return None, e.code

def login():
    body, _ = api("POST", "/auth/login", {"username":"justas","password":"Dance@Admin2026"})
    return body["token"]

# Patterns that identify garbage entries (not real dance moves)
BAD_PATTERNS = [
    # Lettered/numbered salsa sequence steps
    r"^[A-Z] (Slide|Step|Turn) \d*$",
    r"^[A-Z] (Slide|Step|Turn)$",
    r"^\d+ Step( \d+)?$",         # "5 Step", "15 Step", "6 Step 2"
    r"^[A-Z] (Slide|Turn) 2$",    # "G Slide 2", "B Turn"
    r"^[A-Z] Turn$",

    # Tutorial meta / section headers
    r"^(Sec |Section |LEVEL |Part |Level )\d",
    r"^Move \d+ Tutorial$",
    r"^(Tip #|No\.\d+|MOVE \d+)",
    r"^(chapter \d+|Chapter \d+)",

    # Video structure entries
    r"^(First Half|Second Half|Full Piece|From the Top|Combining All|Actual speed|Last 8|Second 8|2nd Half|1st Half)",
    r"^(Intro\.|Outro|Outro/|Alignment$|Spotting$|Ending$|Opening$|Demo$|Recap$|Breakdown$|Counting$|Slo-Mo$|Groove \d$|Groove \d+$)",
    r"^(T I M E S T A M P S|DEMO TO MUSIC|LEADER STEPS|FOLLOWER STEPS|DEMO WITH COUNTS|KEY POINTS|ADVANCED WARNING|RECAP OF FULL|START OF ROUTINE|2ND HALF OF COMBO)$",

    # Instructional how-to phrases
    r"^(Benefits of |How to Enroll|How to Tie |What is a |When is it |Is it part |Learn the step$|Practice with |Outro$|Find out more$)",
    r"^(What is Contemporary|What Clothes|How Much Space|How to Choose Music|How to Warm Up|Where You Can Learn|Super Secret|What is Paso)",
    r"^(A history of ballet|The most famous ballets|Main ballet cities|Pantomimes$|Some advice$|Bravo to all|Bonus Tip$|#WATCHMEJIG)",
    r"^(Lesson Preview|What is a Reverse|Leader.s Footwork|Practice Without|Connection: How|Common Mistake|Important Tip$|Practice with Counts|Practice with Music|Great job)",
    r"^(Flexibility Workshop|Benefits of Workshop|Private Lessons|Group Classes|Social Dance|Salsa team|Solo Practice|Salsa Congress|Affordability|Incorporate Salsa)",

    # Instructor/performer names
    r"^(Gaby Cook|Moe Sakan|Nadiya Keagy|Irina Amzashvili|Theresa Manney|Kelly Young|Bianca Locatelli|Grace Babbes|1-2-3-4-5-6$)",
    r"^All dance$",

    # Ballet lesson structure (not moves)
    r"^(LEARN |learn |LEARNING HOW TO |HOW TO TOP ROCK|HOW TO SIDE ROCK|HOW TO PIN DROP|HOW TO 3 STEP|HOW TO KNEE POSE|DANCE MOVES WITH THE MUSIC)",
    r"^(VERY QUICK RECAP|FINAL THOUGHTS$|POSTURE$|STEPS \+ FOOTWORK|TIMING$|MUSICALITY$|TECHNIQUES$|STAND UP, LETS GO)",
    r"^(LEARNING COMBO|RECAP ALL COMBOS|COMBOS WITH MUSIC)",
    r"^(BOUNCE \|.+|KNOCK \|.+|SNAP KICK \|.+|KNEE UP \|.+|TWIST \|.+|TOE TWIST |HEEL TWIST )",
    r"^(BATTEMENT FONDU|BATTEMENT FRAPPÉ|BATTEMENT CLOCHE|BATTEMENT FRAPPE|STANDING/ SUPPORTING|WORKING LEG$|PORT DE BRAS$|ARABESQUE A TERRE$|ARABESQUE EN L|ATTITUDE ARABESQUE$|PIROUETTE EN DEDANS$|CHANGEMENT$|ST ARABESQUE$|ND ARABESQUE$|RD ARABESQUE$)",
    r"^(Vaganova Barre|Balanchine Barre|Vaganova Center|Balanchine Center|Vaganova Turns|Balanchine Turns)",
    r"^(Warm-up - |Plies - |First Tendu - |Tendu from the|Slow Jete - |Pique- |Rond de Jambe - |Fondu - |Frappe - |Adage - |Grand Battement - |Rises to finish)",
    r"^(Review of the Positions|1st Position$|2nd Position$|3rd Position$|4th Position$|5th Position$|6th Position$)",
    r"^(ADAGE$|STANDING/ SUPPORTING LEG$)",
    r"^(élevé exercise|turn exercise|ron de jambe exercise|kick exercise|développé exercise|fan kick exercise)",
    r"^(Degagé 1st$|Degagé 5th$)",  # duplicates of proper spellings

    # Raw movement instructions (from a floor work / contemporary video)
    r"^(start with our feet|roll both of your|brush and frame|thread it through|left foot crosses|push into a chair|step on your left|cross your right foot|release your right arm|turn it over your|roll to the front|sitting up by pushing|rolling over your|open the curtain|tuck your left|left switch right|bring my right)",

    # Breakdance "mistake" series (numbered tutorial chapters)
    r"^\d+ .+ Mistake$",

    # Other clearly bad entries
    r"^(DEMO TO MUSIC$|RECAP OF MOVES$|RECAP OF ALL MOVES$|MOVES WITH MUSIC$|HOW TO HEEL TOE VARIATION|HOW TO SKATE VARIATION|HOW TO SHUFFLE VARIATION|HOW TO PAS DE BOURREE VARIATION|HOW TO STOMP VARIATION)",
    r"^(Muscleman$|Luck$|Uncle Sam$|Punch$|Clap$|Game$|Counting$|Slo-Mo$)",
    r"^(Group Classes$|Private Lessons$|Social Dance!$|Incorporate Salsa Into Travel$|Affordability & Pricing$|Salsa Congresses$|Solo Practice Options$|Salsa team$)",
    r"^(EX Dance University$)",
    r"^(Tip #\d|tip #\d)",
    r"^(STAND UP, LETS GO!$|HOW TO TOP ROCK$|HOW TO SIDE ROCK$|HOW TO PIN DROP$|HOW TO 3 STEP$|HOW TO KNEE POSE$|DANCE MOVES WITH THE MUSIC$)",
    r"^\d+-\d+ .+ Mistake$",
    r"^(Flexibility Workshop Info$|Flexibility Workshop Promo$)",
    r"^(Part \d+ with music|Part \d+ - |Sec \d+ Breakdown$)",
    r"^(LEARNING HOW TO SWIPE|LEARNING HOW TO BACKSPIN|LEARNING HOW TO FLARE|VERY QUICK RECAP OF POWERMOVES|Toprocks$|Footworks$|Freezes$|Powermoves$)",
    r"^(POSTURE$|STEPS \+ FOOTWORK$|TIMING$|MUSICALITY$|TECHNIQUES$)",
    r"^(first song focusing|second song focusing|third song focusing)",
    r"^(HOW TO WAACK$|ARM ROLL$|QUICK ARMS$|PUT IT ALL TOGETHER$)",
    r"^(Full Waacking Combo|Full Combo on Music|Time for the Surprise|2 Days Live Workshop|Benefits of Workshop|How to Enroll\?)",
    r"^(Combining two 8 counts|Last 8 . counts|Second 8 . counts|Combining all three|Full Combo on|Actual speed of)",
    r"^(Combining All Breakdown$|Combining All Practice$|Bonus Tip$|Demo of all patterns$)",
    r"^(LEVEL \d+$)",
    r"^chapter \d+",
    r"^(Inset$|Galatea$|Normal$|Overview$|Start$|Lift$|Drop$|Twist$|Dip$|Slide$|Bounce$|Shimmy$|Sway$|Glide$|Walk$|Step$|Rock$|Arms$|Close$|Replace$|Brush$|Tap$|Lockstep$|Heel Lead$|Toe Lead$|Heel Toe$|Toe Heel$)",
    r"^(The Bounce Breakdown$|The Bounce Practice$|The Bounce With Arms|The Lean Breakdown$|The Lean Practice$|Bounce & Lean$|Move Around Breakdown$|Move Around Practice$|Move Around Front|Bonus Tip$|Happy Day.s Side Step)",
    r"^(Mensurability$)",
    r"^(Sec 1 Breakdown$|Sec 2 Breakdown$|Sec 3 Breakdown$|Sec 4 Breakdown$|Sec 5 Breakdown$|Whole Song Demo to Music$)",
    r"^(<Untitled Chapter)",
    r"^(LEARNING HOW TO CRIP|LEARNING HOW TO HOP|LEARNING HOW TO DOUBLE|LEARNING HOW TO BONUS|QUICK RECAP OF PAS|PAS DE BOURREE VARIATIONS WITH MUSIC)",
    r"^(The right leg$|The left leg$|The hop$|The sevens$|On your toes$|Lead round$|First step$|Second step$|The full dance$|warm-up$|élevé exercise explanation$|élevé exercise$|turn exercise \d|ron de jambe exercise|kick exercise$|développé exercise|fan kick exercise)",
    r"^(Warm Up$)",
    r"^(Play(ing)? with rhythm$|Sweeps and Fades$|Playing with hesitation$|Tuck Turn styling$|Follow styling Pump The Brakes$|Mirroring$)",
    r"^(An .old Frankie favorite|Leads picking up|Tuck Turn styling)",
    r"^(Part 1$|Part 2$|Part 1 with music$)",
    r"^(Technique Drill with music$|Introduction / Meet Karen$)",
    r"^(Rotating Basic$)",  # keep this? it's actually a swing move... let's not
    r"^(Lesson Preview for the|What is a Reverse Cross Body|Leader.s Footwork for the|Practice Without Connecting|Connection: How to Lead|Common Mistakes #|Common Mistake #|Important Tip$|Practice with Counts$|Practice with Music$|Great job! You did it!$)",
    r"^(How do you do the Lindy\?$)",
    r"^(Demo of all patterns$|Basic step \| 4 Parts$|One more time, from the start!$)",
    r"^(Swing Dance Hold$|Section \d+$|Turn to the Left|Degree of Turn$|Left Turn$|Right Turn$)",
    r"^(See the remate$|Learn the feet first$|Adding in direction|Adding in the arms$|Run through from the top$|Practice with solo|Practice with a letra|Dance to the music!$|Teacher.s chat)",
    r"^(START OF ROUTINE$|2ND HALF OF COMBO$|RECAP OF FULL ROUTINE$|ADVANCED WARNING$|ROUTINE WITH MUSIC$)",
    r"^(Start$|Group Classes$|Salsa team$|Private Lessons$|Solo Practice Options$|Salsa Congresses$|Social Dance!$|Incorporate Salsa Into Travel$|Affordability & Pricing$)",
    r"^(Muscleman$|Max$|Luck$|Uncle Sam$|Punch$|Clap$|Game$|Counting$|Demo$|Groove \d+$|Basic Running Man$|Groove \d$|Recap$|Slo-Mo$)",
    r"^(TUTORIAL: |I attempt move)",
    r"^(Attempting the )",
    r"^(Inversion Flip-Over$|Z-Sit Pike Throw$|Chug Knee Spin$|Shoulder-Up$|Combo With All Moves$)",
    r"^(T I M E S T A M P S$|DEMO TO MUSIC$|LEADER STEPS$|FOLLOWER STEPS$|DEMO WITH COUNTS$|KEY POINTS$)",
    r"^(Tip #\d+: |tip #\d+)",
    r"^(Tip #\d+$)",
    r"^(STAND UP, LETS GO!$)",
    r"^(Flexibility Workshop Info$|Flexibility Workshop Promo$|2 Days Live Workshop$|Benefits of Workshop$|How to Enroll\?$)",
    r"^(HOW TO HEEL TOE VARIATION$|HOW TO SKATE VARIATION$|HOW TO SHUFFLE VARIATION$|HOW TO PAS DE BOURREE VARIATION$|HOW TO STOMP VARIATION$|RECAP OF MOVES$|MOVES WITH MUSIC$|RECAP OF ALL MOVES$)",
    r"^(What is Paso de Bul|When is it used|Is it part of the|Learn the step$|Practice with solo comp|How to use the step|Practice with a letra|Outro/Find out more$)",
    r"^(Basic Movement$|Extensions$|Jumps and Connecting Steps$)",
    r"^(LEARN Warm Up$|LEARN Tendu|LEARN Plie|LEARN Coupé|LEARN Sous Sous|LEARN Relevé|LEARN Échappé|LEARN Developpé|LEARN Developpé)",
    r"^(Tendu 5th Faster$|Turnout Exercise$)",
    r"^(STEP \d+: |LEVEL \d+ STEP \d+: |JUMP TOGETHER|Jumps$|Leg Work$|Turns$|Floor Work$|Balance$|Travel$)",
    r"^(Plies$|Stretch$|Dégage 1st$|Dégage 5th$|First Half$|Second Half$|From the Top$|Full Piece w/Music$)",
    r"^(What is Paso de Bulerias\?$|When is it used\?$|Is it part of the structure\?$)",
    r"^(Degagé 1st$|Degagé 5th$)",
    r"^(Warm-up - Intro.Exercise$|Plies - Intro.Exercise$|First Tendu - Intro.Exercise$|Tendu from the Fifth - Intro.Exercise$|Slow Jete - Intro.Exercise$|Pique- Intro.Exercise$|Rond de Jambe - Intro.Exercise$|Fondu - Intro.Exercise$|Frappe - Intro.Exercise$|Adage - Intro.Exercise$|Grand Battement - Intro.Exercise$|Rises to finish$)",
    r"^(The \d+ Steps$)",
    r"^(Lets Hug$|The Balance$|The Routine$|The 15 Steps$)",
    r"^(Slo-Mo$|Groove 1$|Groove 2$|Recap$|599$|Slo.Mo$)",
]

def is_garbage(name):
    for pat in BAD_PATTERNS:
        if re.match(pat, name, re.IGNORECASE):
            return True
    return False

def main():
    print("Logging in...")
    token = login()
    print("Fetching dances...")
    dances, _ = api("GET", "/dances", token=token)
    print(f"Total: {len(dances)}")

    to_delete = [(d["id"], d["name"]) for d in dances if is_garbage(d["name"])]
    print(f"\nFound {len(to_delete)} garbage entries:\n")
    for did, name in to_delete:
        print(f"  [{did}] {name}")

    print(f"\nProceeding to delete {len(to_delete)} entries...")
    deleted = failed = 0
    for did, name in to_delete:
        _, code = api("DELETE", f"/dances/{did}", token=token)
        if code in (200, 204, 404):
            print(f"  DEL [{did}] {name}")
            deleted += 1
        else:
            print(f"  FAIL {code} [{did}] {name}")
            failed += 1
        time.sleep(0.05)

    print(f"\nDone -- deleted={deleted}, failed={failed}")

if __name__ == "__main__":
    main()
