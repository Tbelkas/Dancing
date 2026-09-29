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
        "words": ["samba", "latin", "brazilian", "brazil", "cha cha", "chacha",
                  "cha-cha", "rumba", "paso doble", "pasodoble"],
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
            ("Cha Cha Hockey Stick", 2,
             "The follower travels out from fan position and turns under the arm, "
             "tracing a hockey-stick shape.", "Salsa"),
            ("Cha Cha Fan", 1,
             "The follower steps back to the leader's left side, opening to an L "
             "shape - the position half the syllabus starts from.", "Salsa"),
            ("Cha Cha Alemana", 2,
             "The follower's turn under the arm from fan position, turning to the "
             "right.", "Salsa"),
            ("Cha Cha Time Step", 1,
             "The cha cha basic danced in place, apart - the chasse and check that "
             "every figure is built on.", "Salsa"),
            ("Rumba Fan", 1,
             "The rumba version of the fan: slow and stretched, with Cuban motion "
             "through the hips.", "Salsa"),
            ("Rumba Alemana", 2,
             "The follower's underarm turn from fan, slow enough in rumba to show "
             "every ounce of hip action.", "Salsa"),
            ("Rumba Hockey Stick", 2,
             "Out of fan, the follower closes, turns under and walks away along the "
             "shape of a hockey stick.", "Salsa"),
            ("Paso Doble Sur Place", 1,
             "Marching on the spot on the balls of the feet - the paso doble's "
             "stamp-and-hold matador posture.", "Salsa"),
            ("Paso Doble Appel", 1,
             "A stamp that marks a change of direction - the matador calling the "
             "bull's attention.", "Salsa"),
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

    # ================================================================== round 3
    # The big styles, filling the canonical vocabulary they were missing.

    "Dancehall": {
        "id": 14,
        "desc": None,
        "music": "Dancehall",
        "words": ["dancehall", "jamaica", "jamaican"],
        "query": "dancehall",
        "adopt": [],
        "moves": [
            ("Signal di Plane", 1,
             "Arms waved overhead like marshalling an aircraft while the feet bounce - "
             "one of the early-2000s moves out of Bogle's generation."),
            ("Log On", 1,
             "The foot stepping as though pressing into the ground and twisting out, "
             "from Elephant Man's 2002 song."),
            ("Sweep", 1,
             "Sweeping one foot across the floor on the beat while the body leans with "
             "it, from the Elephant Man tune."),
            ("World Dance", 2,
             "A sequence move popularised by Beenie Man's song, the arms turning like "
             "the globe."),
            ("Zip It Up", 1,
             "Miming zipping up a jacket from waist to chin, in time, with a bounce."),
            ("Chaka Chaka", 2,
             "A dancehall step with a rhythmic knee and hip action, from the Ding Dong "
             "era."),
            ("Dancehall Butterfly", 2,
             "Knees opening and closing like wings - the 1990s dancehall queen move."),
            ("Shampoo", 1,
             "Hands scrubbing the head as if washing hair, while the feet keep the "
             "bounce."),
            ("Pelpa", 2,
             "A later Ding Dong move, all quick feet and shoulders, from the Ravers "
             "Clavers crew."),
        ],
    },

    "Afrobeats": {
        "id": 13,
        "desc": None,
        "music": "Afrobeats",
        "words": ["afro", "afrobeats", "afrobeat", "afrodance", "naija", "nigerian",
                  "nigeria", "ghana", "african"],
        "query": "afro dance",
        "adopt": [],
        "moves": [
            ("Etighi", 1,
             "A shoulder-and-chest wiggle with small steps, from Iyanya's 2012 'Kukere' "
             "era - Calabar in origin."),
            ("Alkayida", 1,
             "The Nigerian street move of rocking the torso with arms swinging loosely, "
             "popular in 2012-13."),
            ("Skelewu", 1,
             "The dance from Davido's 2013 song, released with a video tutorial and a "
             "contest - loose, bouncy and all shoulders."),
            ("Gbese", 1,
             "A leg-lifting, bouncing Lagos street move, the knee swinging out and in."),
            ("Odi Dance", 1,
             "The Kenyan dance from the Odi wa Muranga crew: a swaying, shoulder-led "
             "groove that spread through Nairobi."),
        ],
    },

    "Breakdance": {
        "id": 12,
        "desc": None,
        "music": "Hip-Hop",
        "words": ["breakdance", "breakdancing", "bboy", "b-boy", "breaking", "bgirl",
                  "b-girl", "breakin"],
        "query": "breakdance",
        "adopt": [],
        "moves": [
            ("Indian Step", 1,
             "A toprock: crossing one foot in front, then stepping back out with the "
             "arms opening - after the 'Indian' step of early Bronx b-boys."),
            ("Three Step", 1,
             "The shorter footwork circle - three steps round instead of six - used to "
             "change direction quickly."),
            ("Kick Out", 1,
             "From the crouch, one leg kicks straight out while the hand supports - the "
             "simplest downrock accent."),
            ("Shoulder Freeze", 2,
             "A freeze balanced on one shoulder and the hand, legs in the air."),
            ("Hollowback", 3,
             "A handstand with the back arched and the legs dropped over towards the "
             "head."),
            ("Jackhammer", 3,
             "Bouncing on one hand while the body spins in a pike, the legs held up."),
            ("Halo", 3,
             "A power move spinning round the head in a tilted circle, the body swept "
             "from the back of the head to the forehead."),
            ("Airflare", 3,
             "An aerial power move: the body flips in the air between hand contacts "
             "while the legs circle wide."),
            ("Hand Glide", 2,
             "Spinning horizontally on one hand, the elbow planted in the stomach."),
            ("Crickets", 3,
             "Spinning in a series of hops on the hands, the elbow tucked into the hip."),
            # Round 7 (2026-09-29): Breaking glossary terms without a clip.
            ("Breaking Indian Step", 1,
             "The basic toprock: step across, back to centre, out to the side, and "
             "switch."),
            ("Salsa Rock", 1,
             "A toprock from salsa's back step: step back on a diagonal, return, switch "
             "sides."),
            ("Toprock Two Step", 1,
             "Kick forward, step back beside the other foot, and switch - a bouncy "
             "toprock."),
            ("Toprock Kick Step", 1,
             "A toprock kick followed by a step down in front and a switch."),
            ("Brooklyn Rock", 2,
             "A toprock from uprock: jerks, crosses and shoulder rocks aimed at an "
             "opponent."),
            ("Outlaw Toprock", 2,
             "Step across, turn on the balls of the feet and open back out facing "
             "front."),
            ("CC Footwork", 2,
             "Switching quickly between a tucked leg and a leg kicked out - a classic "
             "footwork pattern."),
            ("Breaking Sweep", 2,
             "One leg sweeping low in an arc while the body rotates on the hands."),
            ("Breaking Airchair", 3,
             "Balanced on one bent arm, elbow in the lower back, body facing up."),
            ("Elbow Freeze", 2,
             "The whole body balanced on one hand, the elbow dug into the side of the "
             "waist."),
            ("Backspin", 2,
             "Spinning on the upper back with the legs tucked, started by a push of "
             "the hands."),
            ("1990 Spin", 3,
             "A handstand spin on one hand, the body straight."),
            ("2000 Spin", 3,
             "A handstand spin on both hands stacked on top of each other."),
            ("Munchmill", 3,
             "A windmill with the knees tucked in, rolling low and fast."),
            ("Suicide Drop", 3,
             "A dramatic fall straight onto the upper back, landed safely."),
        ],
    },

    "House": {
        "id": 11,
        "desc": None,
        "music": "Electronic / EDM",
        "words": ["house"],
        "query": "house dance",
        "adopt": [],
        "moves": [
            ("Loose Legs", 2,
             "House footwork with the legs kept relaxed and flicking out, the knees "
             "leading, loose as the name says."),
            ("House Skate", 2,
             "A gliding step pushed off like ice skating, travelling side to side."),
            ("Salsa Hop", 2,
             "A hopping house step with a salsa-like cross, landing on the beat."),
            ("Crossroads", 2,
             "Crossing and uncrossing the feet in a square pattern - a house footwork "
             "foundation."),
            ("Train", 2,
             "A travelling house step, the feet stepping and pulling like a train's "
             "pistons."),
            ("Scribble Legs", 3,
             "Fast, scrambled footwork that looks like the legs are scribbling on the "
             "floor."),
            ("Sidewalk", 2,
             "A travelling house step moving laterally, heel and toe alternating."),
            # Round 7 (2026-09-29): every learnable House glossary term without a clip.
            # Names that already exist under another style ("Roger Rabbit", "Happy
            # Feet") carry a "House" prefix, or the seeder would skip them as known.
            ("House Bounce", 1,
             "The knees giving and returning on every beat - the pulse every house step "
             "sits on."),
            ("Side Jack", 1,
             "The jack turned sideways: the ribcage and hips rocking left and right on "
             "the beat."),
            ("Rolling Jack", 2,
             "The jack taken round in a circle - forward, side, back, side - one "
             "quarter per beat."),
            ("House Stomp", 1,
             "A flat-footed step driven into the floor on the beat, the jack sinking "
             "into it."),
            ("Jack in the Box", 2,
             "The jack on a jazz-box floor pattern: cross, back, side, together."),
            ("House Heel Toe", 1,
             "Heel tapped forward, then toe, before the feet change over - one of the "
             "first house footwork patterns."),
            ("House Loose Legs", 2,
             "The free knee turns in and the lower leg flicks loosely out before the "
             "weight changes."),
            ("House Happy Feet", 2,
             "Quick alternating steps on the balls of the feet, loose at the ankles."),
            ("House Pas de Bourree", 2,
             "Three quick weight changes - behind, side, front - borrowed from jazz and "
             "ballet."),
            ("House Heel Step", 1,
             "A heel placed out on the beat while the torso jacks forward over it."),
            ("House Cross Step", 1,
             "Step out, step back, cross over in front - then the same to the other "
             "side."),
            ("Lotus", 2,
             "The leg releases out to the side and is drawn back to centre on the beat; "
             "named for Marjory 'Lotus' Smarth."),
            ("House Chase", 1,
             "Step out on a diagonal with the back heel pivoting, then slide in and "
             "twist - the precursor to loose legs."),
            ("Pow Wow", 2,
             "Leg back, kick, hop back onto the other leg, then step over - danced on "
             "one side with an up feel."),
            ("House Sponge Bob", 2,
             "Kick a leg out and back into a figure four while the standing foot "
             "returns to centre."),
            ("House Roger Rabbit", 2,
             "The hip-hop party step danced house style: hop forward, swing the free "
             "leg out, land it behind."),
            ("Around the World", 3,
             "Step back, float two hops while the free leg traces a U, and step back to "
             "the same spot."),
            ("House JB Step", 2,
             "Sliding sideways on one foot by pivoting ball, heel, ball, the other leg "
             "dragged along."),
            ("House Pivot Turn", 1,
             "A half turn on the balls of both feet - step, pivot, and the weight "
             "settles on the other foot."),
            ("House Spin", 2,
             "Wind up, hop onto the ball of one foot and turn, spotting a point in the "
             "room; land open on two feet."),
            ("House Knee Drop", 2,
             "Dropping from standing to the floor by rolling onto the shin and thigh, "
             "never the kneecap."),
            ("House Back Roll", 2,
             "Rolling over one shoulder along the back and returning to the feet "
             "without stopping the groove."),
            ("House Seat Spin", 2,
             "Sitting down and spinning on the seat with the legs tucked, pushed by "
             "one hand."),
            ("House Kip Up", 3,
             "Springing from the back straight to the feet - a clean way out of "
             "floorwork."),
            ("House Split", 3,
             "Dropping into a jazz split from footwork and coming back up."),
        ],
    },

    "Jazz": {
        "id": 20,
        "desc": None,
        "music": "Jazz",
        "words": ["jazz"],
        "query": "jazz dance",
        "adopt": [],
        "moves": [
            ("Calypso Leap", 3,
             "A turning leap: the front leg in attitude, the body turning in the air "
             "and landing as the back leg extends."),
            ("Hitch Kick", 2,
             "A scissor kick in the air - the first leg kicks up, the second follows as "
             "the first comes down."),
            ("Jazz Layout", 3,
             "One leg kicked high as the torso tips back, making a long diagonal line."),
            ("Toe Touch Jump", 2,
             "A straddle jump with the arms reaching towards the toes."),
            ("Jazz Isolations", 1,
             "Moving the head, shoulders, ribcage and hips independently - the warm-up "
             "every jazz class opens with."),
            ("Jazz Hinge", 3,
             "Leaning back on the knees with a straight line from knees to head, "
             "lowered and recovered with control."),
            ("Illusion Turn", 3,
             "A turn on one leg in which the body folds down into a split and back up "
             "as it goes round."),
            ("Jazz Pencil Turn", 2,
             "A turn with both legs straight together like a pencil, arms tight to "
             "the body."),
        ],
    },

    "Classical / Ballet": {
        "id": 4,
        "desc": None,
        "music": "Classical / Orchestral",
        "words": ["ballet"],
        "query": "ballet",
        "adopt": [],
        "moves": [
            ("Five Positions of the Feet", 1,
             "First to fifth position - the five basic placements of the feet every "
             "ballet step starts and ends in."),
            ("Port de Bras", 1,
             "The carriage of the arms: moving through the arm positions with the head "
             "and upper body following."),
            ("Passe", 1,
             "The working foot drawn up to the knee of the standing leg, the position "
             "pirouettes are turned in."),
            ("Pas de Basque", 2,
             "A travelling step in three, the leg sweeping round in a half circle - "
             "from the folk dances of the Basque country."),
            ("Changement", 1,
             "A jump from fifth position, changing feet in the air to land in fifth "
             "with the other foot in front."),
            ("Soubresaut", 2,
             "A jump from fifth to fifth without changing feet, the legs held tightly "
             "together in the air."),
            ("Saute", 1,
             "A basic jump from two feet, landing in the same position - the first "
             "allegro step."),
            ("Temps Leve", 1,
             "A hop on one foot, the other held in position."),
            ("Sissonne", 2,
             "A jump from two feet landing on one, the legs opening in the air like "
             "scissors."),
            ("Entrechat Quatre", 3,
             "A vertical jump beating the legs so they cross twice in the air."),
            ("Brise", 3,
             "A small travelling beaten jump, the legs beating in the air before "
             "landing."),
        ],
    },

    "Tap": {
        "id": 19,
        "desc": None,
        "music": "Jazz",
        "words": ["tap"],
        "query": "tap dance",
        "adopt": [],
        "moves": [
            ("Paradiddle", 2,
             "Heel dig, toe scuff, heel drop, toe drop - four sounds that roll like a "
             "drummer's paradiddle."),
            ("Drawback", 2,
             "A backward brush and step that pulls the foot back under the body with "
             "two sounds."),
            ("Scuffle", 1,
             "A scuff and brush back - a shuffle that strikes the heel first."),
            ("Waltz Clog", 2,
             "A classic tap combination in three, danced to waltz time."),
            ("Cincinnati", 2,
             "A traditional tap step combining a shuffle, hop and flap - a standard "
             "of the old tap repertoire."),
            ("Over the Top", 3,
             "Leaping over the standing foot from one side to the other, the classic "
             "flash step of the Nicholas Brothers era."),
            ("Trenches", 3,
             "Running steps with the body leaning forward and the feet sliding back, "
             "a flash step of the 1930s."),
            ("Bombershay", 2,
             "A traditional step travelling sideways - step, shuffle, ball change - "
             "danced in the old soft-shoe routines."),
        ],
    },

    # ================================================================== round 4
    "Ballroom": {
        "id": 2,
        "desc": None,
        "music": "Classical / Orchestral",
        "words": ["ballroom", "waltz", "foxtrot", "quickstep", "jive", "viennese",
                  "standard"],
        "query": "ballroom",
        "adopt": [],
        "moves": [
            ("Waltz Reverse Turn", 2,
             "The waltz's turn to the left, six steps over two bars, the partner of "
             "the natural turn."),
            ("Waltz Whisk", 2,
             "A figure crossing the feet behind into promenade position, usually "
             "followed by a chasse from promenade."),
            ("Waltz Spin Turn", 3,
             "A natural pivoting turn that spins the couple round and sends them off "
             "in a new direction."),
            ("Foxtrot Three Step", 2,
             "Three forward walking steps in foxtrot's smooth, gliding rise and fall, "
             "the leader passing outside."),
            ("Foxtrot Reverse Turn", 2,
             "The foxtrot's turn to the left with a heel turn for the follower."),
            ("Quickstep Quarter Turns", 1,
             "The first quickstep figure: a natural and a progressive chasse, each "
             "turning a quarter.", "Jazz"),
            ("Quickstep Tipple Chasse", 2,
             "A turning chasse travelling round a corner - the quickstep's quick "
             "footwork at its most typical.", "Jazz"),
            ("Viennese Waltz Reverse Turn", 2,
             "The fast rotating turn to the left that, with the natural turn, makes "
             "up most of a Viennese waltz."),
            ("Viennese Waltz Fleckerl", 3,
             "Spinning on the spot in the middle of the floor, the most advanced "
             "figure in the Viennese waltz."),
            ("Jive Basic Step", 1,
             "Triple step, triple step, rock step - chasse left, chasse right, back "
             "rock - the basic of ballroom jive.", "Jazz"),
            ("Jive Change of Places", 1,
             "The follower passes under the leader's arm from right to left and back "
             "- the first jive figure.", "Jazz"),
            ("Jive American Spin", 2,
             "The follower is pushed off into a full spin and recaught in the leader's "
             "right hand.", "Jazz"),
            ("Jive Chicken Walks", 2,
             "The follower walks backward with swivelling kicks as the leader draws "
             "her in.", "Jazz"),
        ],
    },

    "Swing": {
        "id": 6,
        "desc": None,
        "music": "Jazz",
        "words": ["swing", "wcs", "lindy", "west coast", "shag", "steppin",
                  "stepping"],
        "query": "west coast swing",
        "adopt": [],
        "moves": [
            ("Sugar Push", 1,
             "The West Coast Swing basic: the follower is drawn in, compressed and "
             "sent back along the slot on six counts."),
            ("Left Side Pass", 1,
             "The follower passes the leader on his left side, travelling down the "
             "slot - the second WCS basic."),
            ("Right Side Pass", 1,
             "The follower passes on the leader's right side, with an underarm turn."),
            ("West Coast Swing Whip", 2,
             "An eight-count figure in which the couple rotate a half turn together "
             "in closed position before the follower is sent out."),
            ("Tuck Turn", 2,
             "The follower is tucked in and released into a turn on the anchor, a "
             "basic WCS turn pattern."),
            ("Anchor Step", 1,
             "The triple step at the end of every WCS pattern, where the couple settle "
             "into the connection before the next figure."),
            ("Carolina Shag", 1,
             "The South Carolina beach dance: a smooth six-count partner swing to "
             "beach music, all footwork and hardly any turns.", "Jazz"),
            ("St. Louis Shag", 2,
             "A fast, bouncy solo-ish swing to up-tempo jazz, built on kicks and "
             "double-time triples."),
            ("Lindy Circle", 2,
             "Leader and follower rotating together through an eight-count circle in "
             "closed position - the swingout's rotating sibling."),
            ("Texas Tommy", 2,
             "A Lindy Hop figure where the follower's hand is passed behind her back "
             "and the leader turns her out of it."),
            ("Sugar Tuck", 2,
             "A West Coast Swing sugar push with a tuck and underarm turn at the "
             "end."),
            ("Basket Whip", 3,
             "A West Coast Swing whip with the follower wrapped in the leader's arm "
             "before she is released."),
            ("Chicago Steppin", 1,
             "Smooth partner dance from Chicago's South Side, a descendant of swing "
             "and the Bop, danced to R&B and steppers' music.", "Hip-Hop"),
            ("Starter Step", 1,
             "The two-count preparation at the start of a WCS dance or pattern - how "
             "the couple begin on the same beat."),
        ],
    },

    "Scottish Highland": {
        "id": None,
        "desc": "Scottish Highland dancing: a competitive solo style danced on the "
                "balls of the feet to bagpipes, with precise footwork, high elevation "
                "and fixed dances such as the Fling and the Sword Dance.",
        "music": "Classical / Orchestral",
        "words": ["highland", "scottish", "scotland"],
        "query": "highland dance",
        "adopt": [2048],
        "moves": [
            ("Highland Sword Dance", 2,
             "Ghillie Callum: danced over two crossed swords on the floor without "
             "touching them, speeding up for the final steps."),
            ("Seann Triubhas", 2,
             "A Highland dance whose slow part mimes shaking off the trousers banned "
             "after 1746, followed by a quick-time finish."),
            ("Highland Reel", 2,
             "A dance for four in figure-eight travelling steps and setting steps."),
            ("Highland Pas de Basque", 1,
             "The Highland setting step, sprung onto the ball of the foot - the first "
             "thing a Highland class teaches."),
            ("Highland Shedding", 2,
             "A foundation step of the Fling: the foot cutting behind and in front of "
             "the supporting leg."),
            ("Highland Backstep", 2,
             "A step travelling backwards with the working foot cutting behind the "
             "supporting leg."),
        ],
    },

    # ================================================================== round 5
    "Hip-hop": {
        "id": 10,
        "desc": None,
        "music": "Hip-Hop",
        # Viral dances are titled "How to do the Griddy", with no style word at all,
        # so "dance" has to count here. The move names are distinctive enough to
        # carry the match on their own.
        "words": ["hip hop", "hip-hop", "hiphop", "dance", "dancing"],
        "query": "dance",
        "adopt": [],
        "moves": [
            ("Griddy", 1,
             "Heels tapped alternately while the arms swing and the hands make "
             "glasses over the eyes - created by Allen 'Griddy' Davis, made famous by "
             "NFL touchdown celebrations."),
            ("Hitting the Woah", 1,
             "A sharp, snapping pose - fists pulled in and the shoulders hit - from the "
             "late-2010s Florida and Atlanta scene."),
            ("Shoot Dance", 1,
             "Hopping on one foot while the opposite arm swings and punches up, "
             "popularised by BlocBoy JB's 'Shoot' in 2018."),
            ("Hit Dem Folks", 1,
             "An Atlanta dance where one arm swings across like a punch while the knee "
             "lifts - from the 2010s."),
            ("Crank That", 1,
             "Soulja Boy's 2007 dance: the leans, the 'Superman' jump and the stomps, "
             "one of the first dances to spread through YouTube."),
            ("Tootsie Roll", 1,
             "Rolling the hips while stepping side to side, hands rolling at the knees "
             "- from the 69 Boyz song, 1994."),
            ("Hit the Quan", 1,
             "The 2015 dance from iLoveMemphis's song: a bounce with rolling shoulders "
             "and a hand wave."),
            ("Sturdy", 2,
             "The New York drill-era dance: a hunched, stomping bounce with the arms "
             "swinging, from the early 2020s."),
            # Round 7 (2026-09-29): Hip-hop glossary terms without a clip.
            ("Shmoney Dance", 1,
             "Bobby Shmurda's 2014 dance: a low shoulder bounce with alternating arm "
             "swings."),
            ("Hip Hop Rock", 1,
             "The chest and hips rocking forward and back on the beat - the second core "
             "groove after the bounce."),
            ("Hip Roll", 1,
             "The hips circling forward, side, back and side while the upper body stays "
             "calm."),
        ],
    },

    "Forro": {
        "id": None,
        "desc": "Partner dance from north-east Brazil, danced close to accordion, "
                "zabumba and triangle: a two-step with a sway, ranging from rootsy pe "
                "de serra to the turn-heavy universitario style.",
        "music": "Forro",
        "words": ["forro", "xote", "baiao"],
        "query": "forro",
        "adopt": [],
        "moves": [
            ("Forro Basic Step", 1,
             "Two quick steps and a slow one, side to side or forward and back, the "
             "hips swaying with the zabumba."),
            ("Xote", 1,
             "The slower forro rhythm, danced close with small steps - the first forro "
             "most people learn."),
            ("Baiao", 2,
             "The faster, bouncier forro rhythm popularised by Luiz Gonzaga."),
            ("Forro Universitario", 2,
             "The urban style from 1990s Sao Paulo, with more turns and open figures "
             "than traditional forro."),
            ("Forro Giro", 2,
             "The follower's basic turn out of the embrace, led from the basic."),
        ],
    },

    # ================================================================== round 6
    # The thin Afro and Jersey styles. I could not author these names from
    # knowledge, so each was corroborated first the way find_trending does it:
    # kept only if several separate channels teach a move by that name (Tobetsa 6,
    # Sika Lekhekhe 5, Snokonoko 5, Abrir 5, Jafi Rock 4, Jersey Rock 3).
    # "Betha Kick", "Gqoz Gqoz" and "Fee Bounce" came from one channel each and
    # were dropped - one channel cannot tell a move from a song title.

    "Amapiano": {
        "id": 28,
        "desc": None,
        "music": "Amapiano",
        "words": ["amapiano", "piano", "south africa", "sa "],
        "query": "amapiano dance",
        "adopt": [],
        "moves": [
            ("Tobetsa", 1,
             "A stamping amapiano step - the name is Sesotho for 'press' - danced with "
             "the weight driving down into the floor on the log-drum beat."),
            ("Sika Lekhekhe", 1,
             "An amapiano move whose name means 'cut the cake', the arms slicing "
             "across while the feet keep the piano bounce."),
            ("Snokonoko", 1,
             "A 2020s amapiano dance that spread from the Al Xapo track of the same "
             "name."),
        ],
    },

    "Afro House": {
        "id": 40,
        "desc": None,
        "music": "Afro House",
        "words": ["afro house", "afrohouse", "afro"],
        "query": "afro house dance",
        "adopt": [],
        "moves": [
            ("Abrir", 1,
             "An Afro house step named with the Portuguese for 'to open': the legs "
             "open out and close again in time with the drums."),
        ],
    },

    "Jersey Club": {
        "id": 35,
        "desc": None,
        "music": "Electronic / EDM",
        "words": ["jersey club", "jerseyclub", "jersey"],
        "query": "jersey club dance",
        "adopt": [],
        "moves": [
            ("Jersey Rock", 1,
             "The rocking, bouncing footwork that Jersey club dancing is built on, "
             "danced to the kick pattern of the music."),
            ("Jafi Rock", 2,
             "A Jersey club rock variation, part of the footwork vocabulary taught "
             "alongside the basic rock and the bounce."),
        ],
    },
}
