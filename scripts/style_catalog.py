"""
style_catalog.py - the move vocabulary for styles the catalogue lacks or barely has.

Read by seed_style_moves.py. Data only.

WHY THE NAMES ARE WRITTEN BY HAND
---------------------------------
Every bulk run that took move NAMES from YouTube titles or chapters produced hundreds
of entries that had to be deleted ("Practice with Music", "G Slide", instructor names -
see seeding-pitfalls). The search engine is good at finding a video for a name and bad
at telling you what the names are. So the names and descriptions here are authored, one
move at a time, and YouTube is only asked the narrow question "who teaches this?".

Per style:
  id       existing Styles.Id, or None for a style that does not exist yet
  desc     Styles.Description, used when the style is created
  music    MusicalStyles.Name every new dance is tagged with (one, like the rest of
           the catalogue - see tag-video-consolidation-2026-06). Created if missing,
           but only when the style goes live.
  words    tokens that identify the style in a video title; at least one must appear
           in a candidate's title, which is what stops "Camel" finding a yoga pose
  query    how the style is written in a search
  adopt    ids of existing dances filed under another style that belong here. They
           are moved (not copied) when the style goes live, so the catalogue keeps
           exactly one style per dance.
  moves    (name, difficulty 1-3, description[, music override])

A move whose name already exists anywhere in the catalogue is skipped by the seeder,
so re-running after an edit only adds what is new.
"""

STYLES = {
    # ------------------------------------------------------------------ Popping
    "Popping": {
        "id": None,
        "desc": "Funk style from 1970s Fresno and Oakland built on the pop - a sharp "
                "contract-and-release of the muscles on the beat - with illusions "
                "layered on top: waving, gliding, ticking, animation. Codified by "
                "Boogaloo Sam and the Electric Boogaloos.",
        "music": "Hip-Hop",
        "words": ["popping", "poppin", "pop", "boogaloo", "popper"],
        "query": "popping",
        "adopt": [10, 1883, 316, 713],
        "moves": [
            ("Popping Hit", 1,
             "The contraction everything else is built on: tense the forearms, legs, "
             "chest and neck for an instant on the beat, then release. Clean hits "
             "before anything fancy."),
            ("Fresno", 1,
             "The first popping pattern: step side to side and hit on each arrival, "
             "arms swinging through opposite lines. Named after the city the Electric "
             "Boogaloos came from."),
            ("Dime Stop", 2,
             "Travel smoothly, then stop dead - as if on a dime - sealed with a hit. "
             "The effect lives in the contrast between the glide in and the freeze."),
            ("Twist-o-Flex", 2,
             "A chain of twists through the torso and limbs that turns the body to a "
             "new facing on each hit. One of Boogaloo Sam's original sequences."),
            ("Neck-o-Flex", 2,
             "Isolating the head so it slides and rolls on its own track while the "
             "shoulders stay still, the neck acting as a separate joint."),
            ("Boogaloo Roll", 2,
             "Rolling the hips, knees and chest in continuous circles - the smooth, "
             "rolling half of the style, as opposed to the hit."),
            ("Ticking", 2,
             "Popping in small, rapid hits so that one movement advances tick by tick, "
             "like a clock hand."),
            ("Strobing", 3,
             "Moving through a series of tiny stop-start hits so the body looks lit by "
             "a strobe light. Ticking made smoother and faster."),
            ("Animation Dance", 3,
             "Imitating stop-motion film: frame-by-frame movement with the jerks left "
             "in on purpose. The popping sub-style Poppin' Pete made famous."),
            ("Scarecrow", 2,
             "A popping character move: stiff, dangling arms and loose, buckling legs, "
             "as though the dancer were stuffed with straw."),
            ("Popping Walk Out", 2,
             "The popper's way across the floor: stepping out with a hit on each step "
             "and a slight lean back."),
            ("Gliding", 2,
             "Footwork that makes the dancer seem to slide across the floor without "
             "lifting - the family the backslide belongs to."),
        ],
    },

    # ------------------------------------------------------------------ Locking
    "Locking": {
        "id": None,
        "desc": "Funk style created by Don Campbell in late-1960s Los Angeles and spread "
                "by The Lockers on Soul Train: fast arm moves frozen into locks, points "
                "and wrist rolls, with big comic character. Danced to funk.",
        "music": "Disco",
        "words": ["locking", "lock", "locker", "lockers", "lockin"],
        "query": "locking dance",
        "adopt": [899, 298, 1875],
        "moves": [
            ("The Lock", 1,
             "The move the style is named for: stop mid-motion and freeze, hands pulled "
             "back and body hunched, then release. Every locking routine is built from "
             "locks joined together."),
            ("Locking Point", 1,
             "A sharp point across the body or at the audience, held and snapped back - "
             "the most recognisable locking gesture."),
            ("Wrist Roll", 1,
             "Rolling the hands around each other at the wrists, fast and loose, to link "
             "one lock to the next."),
            ("Scooby Doo", 2,
             "A kick-and-hop step with the arms swinging, the first locking step most "
             "people learn - named for its cartoon bounce."),
            ("Scoobot", 2,
             "Scooby Doo danced with a bent, pumping upper body - Scooby plus a robot."),
            ("Stop and Go", 2,
             "Dancing, freezing dead on the beat, and going again. Locking's timing "
             "tool, and a test of whether the freeze is really a freeze."),
            ("Leo Walk", 2,
             "A walking step with a cross-kick and a turn of the hip, named after Leo "
             "Williamson of The Lockers."),
            ("Skeeter Rabbit", 2,
             "A hopping kick-step alternating feet, named after the dancer Skeeter "
             "Rabbit."),
            ("Which-a-Way", 2,
             "Turning the body side to side while the arms swing across, looking one way "
             "and then the other."),
            ("Uncle Sam Point", 2,
             "A big, deliberate point at the audience with the other hand on the hip - "
             "Uncle Sam's 'I want you'."),
            ("Pacing", 2,
             "A strutting walk with swinging arms: the locker's stylish way of getting "
             "across the floor."),
            ("Locking Knee Drop", 3,
             "Dropping to one knee from standing, sharply and under control, as an "
             "accent at the end of a phrase."),
            ("Giving Five", 1,
             "Slapping a partner's hand, or the air, in rhythm - one of the playful "
             "gestures that make locking a social dance."),
            ("Funky Guitar", 2,
             "Miming a guitar along with the funk line: the kind of comic character move "
             "that sets locking apart from popping."),
            ("Up Lock", 2,
             "A lock with the arms raised overhead instead of pulled back."),
            ("Muscle Man", 2,
             "Flexing both arms like a strongman and freezing for a beat - a lock with "
             "attitude."),
        ],
    },

    # ------------------------------------------------------------------ Salsa
    "Salsa": {
        "id": None,
        "desc": "Partner and solo dance from Cuba and New York built on quick-quick-slow "
                "over eight counts. Danced on1 (LA), on2 (New York), or in a circle as "
                "Cuban casino and rueda.",
        "music": "Salsa",
        "words": ["salsa", "casino", "rueda", "on1", "on2", "mambo"],
        "query": "salsa",
        "adopt": [1, 259, 269, 1825, 2023, 2024, 2031, 839, 738, 1700, 1706,
                  1707, 488],
        "moves": [
            ("Salsa Basic Step", 1,
             "Forward and back: step, step, close on 1-2-3, pause on 4, mirrored on "
             "5-6-7. Every other figure is built on this timing."),
            ("Salsa Side Basic", 1,
             "The basic danced side to side instead of forward and back - the usual "
             "place to start with a partner in closed hold."),
            ("Salsa Right Turn", 2,
             "The follower's right turn, led from the basic on counts 5-6-7. The first "
             "turn every salsa class teaches."),
            ("Salsa Left Turn", 2,
             "The follower's left turn, prepped and led on 1-2-3 - harder than the right "
             "turn because the prep is on the other side."),
            ("Salsa Copa", 2,
             "The follower is sent out, stopped and turned back the way she came - a "
             "cross-body lead with a reversal in the middle."),
            ("Salsa Hammerlock", 2,
             "The follower's arm is wrapped behind her back in a turn and unwound in the "
             "next - the classic salsa wrap."),
            ("Salsa Suzie Q", 1,
             "A shine: swivelling toe-heel crossovers that travel sideways, danced "
             "apart from the partner."),
            ("Salsa Spot Turn", 2,
             "Turning on the spot without travelling, used by both partners to change "
             "facing between figures."),
            ("Salsa On2 Basic", 2,
             "New York-style basic, breaking forward on count 2 instead of 1, which "
             "puts the dancer on the conga's slap."),
            ("Rueda de Casino", 2,
             "Cuban salsa danced in a circle of couples, a caller naming figures and "
             "the followers rotating round the wheel."),
            ("Salsa Sombrero", 2,
             "A Cuban casino figure where the leader's arms pass over both heads like "
             "a hat being put on."),
            ("Salsa Arm Styling", 2,
             "What the free arm and the hands do during basics and turns - styling that "
             "makes the same footwork look finished."),
        ],
    },

    # ------------------------------------------------------------------ Argentine Tango
    "Argentine Tango": {
        "id": None,
        "desc": "Improvised close-embrace partner dance from Buenos Aires and Montevideo, "
                "led through the chest. Walks, ochos, turns and embellishments rather "
                "than fixed routines - distinct from ballroom tango.",
        "music": "Tango",
        "words": ["tango", "milonga", "argentine", "argentino"],
        "query": "argentine tango",
        "adopt": [1963, 2025, 2026, 271, 2027],
        "moves": [
            ("Tango Embrace", 1,
             "The abrazo: how the couple holds, from open to close embrace. Everything "
             "in Argentine tango is led through it, so it comes first."),
            ("Argentine Tango Walk", 1,
             "The caminata - walking in the embrace, chest leading, feet brushing past "
             "each other. Tango teachers call it the whole dance."),
            ("Tango Salida", 1,
             "The traditional opening sequence that takes the couple from standing into "
             "the line of dance."),
            ("Tango Cruzada", 1,
             "The follower's cross, left foot over right, usually at count 5 of the "
             "basic eight - the resting point of many figures."),
            ("Tango Rock Step", 1,
             "The cadencia: shifting weight forward and back on the spot, used to wait, "
             "turn or change direction on a crowded floor."),
            ("Tango Molinete", 2,
             "The giro: the follower walks a grapevine around the leader - forward, side, "
             "back, side - while he pivots at the centre."),
            ("Tango Parada", 2,
             "The leader stops the follower mid-step by placing his foot against hers, "
             "a pause that opens into a pasada or adornment."),
            ("Tango Barrida", 2,
             "One partner's foot sweeps the other's along the floor to a new position."),
            ("Tango Ocho Cortado", 2,
             "A 'cut eight': a rebounding figure that suits a crowded milonga floor."),
            ("Tango Colgada", 3,
             "An off-axis figure where the couple lean away from each other, held by the "
             "embrace, and the follower's free leg swings round."),
            ("Tango Volcada", 3,
             "The opposite off-axis to the colgada: the follower tips forward onto the "
             "leader and her free leg draws a line on the floor."),
            ("Tango Adornos", 2,
             "Embellishments - taps, circles and flicks of the free foot the follower adds "
             "inside the lead, without changing it."),
            ("Milonga Traspie", 2,
             "The quick triple step of milonga, tango's faster, bouncier sister dance."),
        ],
    },

    # ------------------------------------------------------------------ Belly Dance
    "Belly Dance": {
        "id": None,
        "desc": "Raqs sharqi: Middle Eastern solo dance of isolated hip, torso and arm "
                "movement - shimmies, undulations, circles and figure eights. Egyptian, "
                "Turkish and American tribal styles share the vocabulary.",
        "music": "Classical / Orchestral",
        "words": ["belly", "bellydance", "bellydancing", "raqs", "oriental",
                  "egyptian", "shimmy", "tribal"],
        "query": "belly dance",
        "adopt": [1971, 1972, 1981, 1982, 2046, 2047],
        "moves": [
            ("Belly Dance Camel", 1,
             "A travelling undulation that rolls down the torso from chest to pelvis, "
             "named for the animal's rocking gait."),
            ("Belly Dance Hip Circle", 1,
             "Drawing a flat circle with the hips while the chest stays still - the "
             "first isolation most teachers begin with."),
            ("Belly Dance Hip Lift", 1,
             "Lifting one hip sharply by straightening the opposite knee, often paired "
             "with the hip drop as a single accent."),
            ("Belly Dance Hip Twist", 1,
             "Twisting the hips forward and back on a horizontal plane, the base of "
             "the traveling twist steps."),
            ("Belly Dance Chest Circle", 2,
             "Circling the ribcage while the hips stay still - the upper-body mirror of "
             "the hip circle."),
            ("Belly Dance Egyptian Basic", 1,
             "The Egyptian basic walk: a stepping pattern with a hip twist on every "
             "step, used to travel through a routine."),
            ("Belly Dance Three-Quarter Shimmy", 2,
             "A layered shimmy with a stress on every third beat, giving it a lilting "
             "rather than steady feel."),
            ("Belly Dance Omi", 2,
             "A small, fast circle of the pelvis - an Egyptian accent, tighter than the "
             "hip circle."),
            ("Belly Dance Taqsim", 2,
             "Slow, sinuous movement danced to an improvised instrumental solo - "
             "undulations and figure eights rather than accents."),
            ("Belly Dance Veil Work", 2,
             "Handling a silk veil in the dance: framing, spinning and wrapping it "
             "without it ever looking like it is in charge."),
            ("Belly Dance Zills", 2,
             "Playing finger cymbals while dancing - rhythm patterns kept in the hands "
             "while the hips do something else."),
            ("Belly Dance Turkish Drop", 3,
             "A dramatic drop from standing to lying flat on the back with one leg "
             "folded underneath. Advanced, and only with a proper warm-up."),
        ],
    },

    # ------------------------------------------------------------------ Irish Dance
    "Irish Dance": {
        "id": None,
        "desc": "Irish step dance: a rigid upper body with fast, precise footwork, "
                "danced in soft shoes (reel, light and slip jig) or hard shoes (treble "
                "jig, hornpipe), plus the social ceili dances.",
        "music": "Classical / Orchestral",
        "words": ["irish", "riverdance", "ceili", "celtic"],
        "query": "irish dance",
        "adopt": [1974, 1294],
        "moves": [
            ("Irish Reel", 1,
             "The first soft-shoe dance learners take: light, fast, in 4/4, with hop-back "
             "and skip steps. The dance most feiseanna open with."),
            ("Irish Slip Jig", 2,
             "A soft-shoe dance in 9/8, the most graceful of the solo dances - "
             "traditionally danced by women."),
            ("Irish Treble Jig", 3,
             "The heavy (hard-shoe) jig, slow and full of trebles and clicks."),
            ("Irish Hornpipe", 3,
             "A hard-shoe dance in 2/4 or 4/4 with a dotted rhythm, heavier and more "
             "syncopated than the treble jig."),
            ("Irish Sevens", 1,
             "The basic travelling side step: seven quick steps to one side, then back. "
             "Nearly every soft-shoe step is built on it."),
            ("Irish Treble", 1,
             "The basic hard-shoe sound: a brush out and back with the ball of the foot, "
             "making two taps."),
            ("Irish Dance Clicks", 2,
             "Jumping and clicking the heels together in the air - on one side, both "
             "sides, or in combination."),
            ("Irish Dance Rocks", 3,
             "A hard-shoe move where the crossed ankles rock over onto their outside "
             "edges. Looks impossible, and done badly it hurts."),
            ("Irish Dance Leaps", 2,
             "Big travelling leaps in soft shoe - the split leap and the 'lead around' "
             "that carry a step across the stage."),
            ("Walls of Limerick", 1,
             "A simple ceili (social) dance for two couples - the usual first group "
             "dance."),
            ("Siege of Ennis", 1,
             "A ceili dance in lines of four facing four, progressing down the hall."),
        ],
    },

    # ------------------------------------------------------------------ Brazilian Zouk
    "Brazilian Zouk": {
        "id": None,
        "desc": "Partner dance from Rio in the 1990s, grown out of lambada: flowing, "
                "elastic movement, body waves, and the follower's signature head "
                "movements, danced to zouk and R&B.",
        "music": "Kizomba",
        "words": ["zouk", "lambazouk"],
        "query": "brazilian zouk",
        "adopt": [],
        "moves": [
            ("Zouk Basic Step", 1,
             "Slow-quick-quick, danced back and forward in a line - the rail the rest of "
             "zouk runs on."),
            ("Zouk Lateral", 1,
             "The basic danced side to side, the step most figures open from."),
            ("Zouk Elastico", 2,
             "The couple separates and snaps back together as if on elastic."),
            ("Zouk Boneca", 2,
             "A turning figure where the follower spins close to the leader like a doll "
             "('boneca'), led through the hips."),
            ("Zouk Body Wave", 2,
             "A wave travelling down the body - chest, waist, hips - the root of the "
             "follower's look in zouk."),
            ("Zouk Soltinho", 2,
             "The follower is released into a free turn and recaught."),
            ("Zouk Chicote", 3,
             "The 'whip': the follower's head and torso are swung round in a fast "
             "circle. Advanced, and it needs a follower who knows the head movements."),
            ("Zouk Head Movements", 3,
             "The follower's hair-swinging head and torso circles, led by the "
             "leader. Taught slowly - they are the reason zouk has a reputation."),
            ("Zouk Cambre", 3,
             "A deep back bend of the follower, led and supported, usually closing a "
             "phrase."),
        ],
    },

    # ------------------------------------------------------------------ Line Dance
    "Line Dance": {
        "id": None,
        "desc": "Choreographed dances performed in rows, everyone facing the same "
                "wall and turning together. The classic country-and-western "
                "catalogue plus the party standards.",
        "music": "Country",
        "words": ["line"],
        "query": "line dance",
        "adopt": [252, 251, 255, 102, 1431, 435],
        "moves": [
            ("Grapevine", 1,
             "Side, behind, side, touch - the step every line dance uses to travel "
             "sideways."),
            ("Jazz Box", 1,
             "Cross, back, side, forward: a square traced with the feet, used to turn a "
             "quarter to the next wall."),
            ("Coaster Step", 1,
             "Back, together, forward on a quick-quick-slow - a stop-and-change-direction "
             "step."),
            ("Sailor Step", 1,
             "Cross behind, side, side: a swaying triple step, the line-dance cousin of "
             "the swing step."),
            ("Boot Scootin' Boogie", 1,
             "The 1990s country line dance to the Brooks & Dunn song, still the one most "
             "honky-tonks start with."),
            ("Tush Push", 2,
             "A long-standing country line dance with hip bumps and a cha-cha section."),
            ("Copperhead Road", 1,
             "A line dance to Steve Earle's song, with heel struts and a hitch turn."),
            ("Achy Breaky Heart", 1,
             "The early-1990s line dance that made the form a craze."),
            ("Watermelon Crawl", 1,
             "A country line dance to the Tracy Byrd song - rolling vines and heel "
             "switches."),
            ("Cowboy Cha Cha", 1,
             "A partner or solo line dance to cha-cha timing, a standard of country "
             "dance halls."),
            ("Cupid Shuffle", 1,
             "The party line dance that is called as it goes: to the right, to the left, "
             "kick, walk it by yourself.", "Hip-Hop"),
            ("Cha Cha Slide", 1,
             "The wedding-floor standard, every step called out in the song.", "Hip-Hop"),
            ("Wobble", 1,
             "A hip-hop line dance to V.I.C.'s song, the wobble the recurring move.",
             "Hip-Hop"),
        ],
    },

    # ================================================================== round 2
    # Existing styles that were thin. "id" is set, so promote() links straight in.

    "Latin": {
        "id": 1,
        "desc": None,
        "music": "Samba",
        "words": ["samba", "latin", "brazilian", "brazil"],
        "query": "samba",
        "adopt": [],
        "moves": [
            ("Samba no Pe", 2,
             "Brazilian carnival samba: fast, tiny steps on the balls of the feet, "
             "three weight changes to every two beats, danced solo."),
            ("Samba Reggae", 2,
             "The Bahian street samba of Salvador's blocos, grounded and driven by big "
             "drum lines - slower and heavier than Rio samba."),
            ("Samba Walks", 1,
             "The basic travelling figure of ballroom samba, with the pelvic tilt that "
             "gives the dance its bounce."),
            ("Samba Bounce Action", 1,
             "The knee-flexing bounce under every samba figure. Without it samba is "
             "just walking in time."),
            ("Samba Botafogo", 2,
             "A crossing, travelling figure of ballroom samba named after a Rio "
             "neighbourhood."),
        ],
    },

    "Bachata": {
        "id": 36,
        "desc": None,
        "music": "Bachata",
        "words": ["bachata"],
        "query": "bachata",
        "adopt": [],
        "moves": [
            ("Bachata Box Step", 1,
             "The basic danced as a square - forward and back halves joined up - the "
             "usual base for turning as a couple."),
            ("Bachata Hip Motion", 1,
             "The hip that lands on the tap of every fourth count, produced by the "
             "knees rather than pushed."),
            ("Bachata Cross Body Lead", 2,
             "The leader opens a path and passes the follower across to his other side "
             "- the salsa figure translated to bachata's timing."),
            ("Bachata Hammerlock", 2,
             "The follower's arm is wrapped behind her back in a turn and unwound in the "
             "next."),
            ("Bachata Shadow Position", 2,
             "Both partners facing the same way, the leader behind - the position a lot "
             "of sensual bachata styling happens in."),
            ("Bachata Body Roll", 2,
             "A wave rolled down the body from chest to hips, the signature of sensual "
             "bachata."),
            ("Bachata Ladies Styling", 2,
             "Arm, hair and hip styling the follower adds over the basic and turns."),
            ("Dominican Bachata", 2,
             "The original bachata of the Dominican Republic: quick, syncopated "
             "footwork and a looser, more playful hold than sensual."),
        ],
    },

    "Flamenco": {
        "id": 18,
        "desc": None,
        "music": "Flamenco",
        "words": ["flamenco", "sevillanas"],
        "query": "flamenco",
        "adopt": [],
        "moves": [
            ("Flamenco Compas", 1,
             "The rhythmic cycle every flamenco form is built on - usually twelve beats "
             "with accents that differ by palo. Counting it comes before any steps."),
            ("Flamenco Palmas", 1,
             "Flamenco hand-clapping, sharp (claras) or muffled (sordas), in compas - "
             "how dancers keep time and how everyone else takes part."),
            ("Flamenco Golpe", 1,
             "A flat-footed stamp with the whole sole, the loudest of the footwork "
             "sounds alongside planta and tacon."),
            ("Flamenco Tangos", 2,
             "The four-beat palo most beginners learn first - earthy, grounded and "
             "festive."),
            ("Flamenco Rumba", 1,
             "Rumba flamenca: a light, four-beat palo close to Latin music, danced "
             "loosely and socially."),
            ("Flamenco Alegrias", 3,
             "The bright, twelve-beat palo from Cadiz, with its own fixed structure of "
             "sections and the escobilla footwork passage."),
            ("Flamenco Bulerias", 3,
             "The fastest, most improvised twelve-beat palo, full of breaks and "
             "desplantes - the one flamencos dance at the end of the night."),
            ("Flamenco Solea", 3,
             "The slow, deep twelve-beat palo often called the mother of flamenco."),
            ("Flamenco Skirt Work", 2,
             "Manejo de falda: using the skirt to frame and extend the movement, "
             "especially in alegrias and with the bata de cola."),
            ("Flamenco Castanets", 2,
             "Playing castanets (palillos) while dancing - more common in classical "
             "Spanish dance and sevillanas than in flamenco puro."),
        ],
    },

    "Bhangra": {
        "id": 17,
        "desc": None,
        "music": "Bhangra",
        "words": ["bhangra", "punjabi", "bollywood", "giddha", "indian"],
        "query": "bhangra",
        "adopt": [],
        "moves": [
            ("Bhangra Basic Step", 1,
             "Hop on one foot with the other kicked forward, arms raised - the step "
             "every Bhangra class opens with."),
            ("Dhamaal", 2,
             "The high-energy Bhangra move of jumping and turning with both arms thrown "
             "up to the dhol beat."),
            ("Jhoomar", 2,
             "A slower, swaying Punjabi folk dance from the west of the region, danced "
             "in a circle."),
            ("Luddi", 1,
             "A victory dance with one hand behind the back and the other in front of "
             "the face, swaying the head and shoulders."),
            ("Mirza", 2,
             "A Bhangra step named after the folk hero Mirza, danced with a rhythmic "
             "shoulder and arm action."),
            ("Giddha", 1,
             "The Punjabi women's folk dance, performed in a circle with clapping and "
             "sung boliyan verses."),
            ("Thumka", 1,
             "The Bollywood hip jerk, landed on the beat with a hand on the hip or "
             "waist - small and sharp, not a hip roll."),
        ],
    },

    "Kizomba": {
        "id": 39,
        "desc": None,
        "music": "Kizomba",
        "words": ["kizomba", "semba", "tarraxo", "kiz", "kizz"],
        "query": "kizomba",
        "adopt": [],
        "moves": [
            ("Kizomba Walk", 1,
             "Walking in the close embrace - the smooth, grounded step the whole dance "
             "is made of."),
            ("Semba", 2,
             "The older Angolan dance kizomba grew out of: faster, more playful, with "
             "tricks and a bouncier walk."),
            ("Urban Kiz", 2,
             "The French-born offshoot of kizomba: straighter lines, sharper stops and "
             "more footwork, danced to electronic ghetto zouk."),
            ("Tarraxo", 2,
             "A slow, minimal style danced to tarraxo music - almost all hip and "
             "connection, very little travel."),
            ("Kizomba Ladies Styling", 2,
             "What the follower adds inside the lead - hip isolations, foot "
             "embellishments - without breaking the connection."),
        ],
    },

    "Krump": {
        "id": 15,
        "desc": None,
        "music": "Hip-Hop",
        "words": ["krump", "krumping"],
        "query": "krump",
        "adopt": [],
        "moves": [
            ("Krump Stomp", 1,
             "The heavy, driving stomp that krump's groove is built on."),
            ("Krump Arm Swing", 1,
             "Big, powerful arm swings thrown from the back - with the stomp and the "
             "chest pop, one of the three foundations."),
            ("Buck Hop", 2,
             "A krump footwork move: a hopping step with the knees driven up hard."),
        ],
    },

    "Contemporary": {
        "id": 7,
        "desc": None,
        "music": "Classical / Orchestral",
        "words": ["contemporary", "lyrical", "modern"],
        "query": "contemporary dance",
        "adopt": [],
        "moves": [
            ("Fall and Recovery", 2,
             "Giving in to gravity and rebounding out of it - Doris Humphrey's "
             "principle, and one of the ideas contemporary dance is built on."),
            ("Release Technique", 2,
             "Moving through efficiency and breath rather than held muscle, letting "
             "weight and momentum carry the movement."),
            ("Contemporary Improvisation", 2,
             "Generating movement live from a task or an image - how contemporary "
             "dancers find material, and a class in its own right."),
        ],
    },

    "Litefeet": {
        "id": 30,
        "desc": None,
        "music": "Hip-Hop",
        "words": ["litefeet", "lite feet", "lite"],
        "query": "litefeet",
        "adopt": [],
        "moves": [
            ("Aunt Jackie", 2,
             "A Harlem litefeet move from the mid-2000s, a staple alongside the Harlem "
             "Shake and Chicken Noodle Soup."),
        ],
    },

    # ------------------------------------------------------------------ new in round 2
    "Capoeira": {
        "id": None,
        "desc": "Afro-Brazilian art that is dance, fight and game at once, played in a "
                "roda to the berimbau. Kicks, escapes and acrobatics flow out of the "
                "ginga, and the aim is to outplay, not to strike.",
        "music": "Capoeira",
        "words": ["capoeira"],
        "query": "capoeira",
        "adopt": [1985],
        "moves": [
            ("Meia Lua de Frente", 1,
             "The front half-moon kick: the straight leg swept across in front of the "
             "body from outside to in."),
            ("Armada", 2,
             "A spinning outside kick - turn the back, then the straight leg sweeps "
             "round at head height."),
            ("Queixada", 2,
             "An outside crescent kick thrown from a step across, sweeping out and "
             "away."),
            ("Esquiva", 1,
             "The dodges: lowering and turning out of the line of a kick, the reason "
             "capoeira looks like a dance and not a fight."),
            ("Au", 1,
             "Capoeira's cartwheel, done slower and lower than gymnastics, looking at "
             "the other player the whole time."),
            ("Negativa", 2,
             "A low ground position, one leg extended and the body close to the floor, "
             "used to escape and to set up takedowns."),
            ("Role", 1,
             "A low turning movement along the ground, used to travel and to recover "
             "from negativa."),
            ("Martelo", 2,
             "The hammer kick - a roundhouse struck with the instep."),
            ("Macaco", 3,
             "The monkey: a back handspring thrown from a crouch, one hand on the floor "
             "behind."),
            ("Bencao", 1,
             "The blessing: a straight front push kick with the sole of the foot."),
        ],
    },

    "Disco": {
        "id": None,
        "desc": "1970s nightclub dance: the Hustle in all its forms, the line dances "
                "that went with it, and the points, spins and struts of the Saturday "
                "Night Fever era.",
        "music": "Disco",
        "words": ["disco", "70s", "hustle"],
        "query": "disco dance",
        "adopt": [1994],
        "moves": [
            ("The Bus Stop", 1,
             "The 1975 disco line dance - taps, walks, the bump and a turn - the "
             "grandparent of every line dance at a wedding."),
            ("The Hustle Line Dance", 1,
             "The line dance to Van McCoy's 'The Hustle', distinct from the partner "
             "dance of the same name."),
            ("Latin Hustle", 2,
             "The partner hustle, danced on a six-count 'and-1, 2, 3' with continuous "
             "turns - disco's answer to swing."),
            ("Disco Point", 1,
             "The Saturday Night Fever point: arm thrust diagonally up, then down across "
             "the body, in time."),
        ],
    },

    "Memphis Jookin": {
        "id": None,
        "desc": "Street dance from Memphis, Tennessee, grown out of the Gangsta Walk: "
                "smooth gliding, bouncing and toe stands to Memphis rap, famous through "
                "Lil Buck.",
        "music": "Hip-Hop",
        "words": ["jookin", "jook", "jooking", "memphis"],
        "query": "memphis jookin",
        "adopt": [],
        "moves": [
            ("Gangsta Walk", 1,
             "The Memphis walk jookin grew from - a bouncing, stomping stride to "
             "crunk and Memphis rap."),
            ("Jookin Bounce", 1,
             "The constant bounce that sits under all jookin footwork."),
            ("Jookin Glide", 2,
             "Sliding across the floor on the sides and balls of the feet, smoother "
             "and lower than a popping glide."),
            ("Jookin Toe Stand", 3,
             "Standing and turning on the tips of the toes in sneakers - the move that "
             "made Lil Buck famous."),
        ],
    },

    "Polynesian": {
        "id": None,
        "desc": "Dances of the Pacific islands - Hawaiian hula, Tahitian ori, Maori "
                "haka and poi. Hands tell the story in hula; hips drive the drum "
                "dances of Tahiti.",
        "music": "Polynesian",
        "words": ["hula", "tahitian", "polynesian", "hawaiian", "ori", "maori", "poi"],
        "query": "hula",
        "adopt": [1975, 1984, 2011],
        "moves": [
            ("Hula Kaholo", 1,
             "The basic side-to-side vamp step of hula, step-together-step-touch with "
             "the hips swaying."),
            ("Hula Hela", 1,
             "Point one foot forward to the diagonal and back, the hips moving with the "
             "weight."),
            ("Hula Ami", 2,
             "A continuous circular rotation of the hips, clockwise or counter-"
             "clockwise, the knees bent."),
            ("Hula Uwehe", 2,
             "Lift both heels and push the knees forward to snap the hips up, a sharp "
             "accent move."),
            ("Hula Hand Motions", 1,
             "The hand gestures that tell the story of the song - the sea, the rain, a "
             "flower - which is what hula is actually about."),
            ("Tahitian Faarapu", 3,
             "The fast, driving hip circle of Tahitian ote'a, danced to the toere "
             "drums."),
            ("Tahitian Varu", 2,
             "A figure-eight of the hips traced side to side, one of the core ote'a "
             "hip movements."),
            ("Maori Poi", 2,
             "Swinging poi - balls on cords - in rhythmic patterns, a Maori performance "
             "art taught for coordination as much as display."),
        ],
    },

    "Indian Classical": {
        "id": None,
        "desc": "The classical dance traditions of India - Bharatanatyam, Kathak, "
                "Odissi and others - combining rhythmic footwork, sculptural poses and "
                "hand gestures (mudras) that tell stories.",
        "music": "Indian Classical",
        "words": ["kathak", "bharatanatyam", "odissi", "kuchipudi", "mohiniyattam",
                  "indian classical", "classical indian"],
        "query": "indian classical dance",
        "adopt": [2018, 1987],
        "moves": [
            ("Kathak Tatkar", 1,
             "Kathak's foundational footwork: flat-footed rhythmic stamping in time "
             "with the bols, the first thing every class drills."),
            ("Kathak Tihai", 2,
             "A rhythmic phrase repeated three times to land exactly on sam, the first "
             "beat of the cycle."),
            ("Kathak Hastak", 2,
             "The hand and arm movements of Kathak, precise and flowing, that frame the "
             "footwork."),
            ("Bharatanatyam Aramandi", 1,
             "The half-seated position with knees turned out - the base posture of "
             "Bharatanatyam."),
            ("Bharatanatyam Mudras", 1,
             "The hand gestures (hastas) of Bharatanatyam, each with its own name and "
             "meaning - the vocabulary the storytelling is written in."),
            ("Bharatanatyam Natta Adavu", 2,
             "Adavus stretching the leg to the side on the heel - the second set after "
             "Tatta Adavu."),
            ("Odissi Chauka", 1,
             "The square, wide-legged stance of Odissi - one of its two base positions."),
            ("Odissi Tribhanga", 2,
             "The three-bend posture of Odissi - head, torso and hips curved in "
             "opposition, the pose of temple sculpture."),
        ],
    },
}
