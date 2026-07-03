# One-shot cleanup of junk dance descriptions (YT-title paste-ins, "Trending tutorial:" prefixes,
# Ollama-era "A dance move..." filler). Emits UPDATE SQL on stdout; pipe into psql with
# PGCLIENTENCODING=UTF8 (see fix-videos/apply_sections pattern — never pass non-ASCII on argv).
import sys
sys.stdout.reconfigure(encoding="utf-8")

DESCRIPTIONS = {
    # --- Style cards (dance named after the style itself) ---
    1: "Cuban-rooted partner dance in eight-count timing: quick-quick-slow footwork, spinning turn patterns and constant hip motion, danced socially in lines or a circle.",
    9: "Dominican partner dance in four-count rhythm - three steps and a hip-lifted tap - flavoured with body waves, turns and close connection.",
    4: "Street dance born in the Bronx built on toprock, downrock footwork, power moves and freezes, battled to breakbeats.",
    11: "Expressive concert style blending ballet lines with modern release technique, floor work and improvisation to interpret music and emotion.",
    6: "Andalusian art form uniting percussive zapateado footwork, carved arm lines, palmas hand claps and intense emotional expression.",
    1676: "1970s Los Angeles club style of whipping arm rotations, sharp poses and dramatic musicality, danced to disco.",

    # --- Afrobeats ---
    1715: "Ghanaian dance built on quick footwork and playful hand gestures that mime everyday actions, danced with knees bent and torso relaxed.",
    1815: "Viral Nigerian dance to Kizz Daniel's 'Buga': chest lifted, arms pumping skyward as the shoulders bounce on the beat.",
    1854: "TikTok dance for Rema's 'Calm Down', stringing smooth arm waves and hip sways into a short repeatable phrase.",
    2000: "Ivorian club dance marked by sharp leg cuts, traveling steps and flashy arm displays over driving percussion.",
    1794: "Afro-fusion choreography phrase danced to WizKid's 'Ginger', blending bounce grooves with fluid arm lines.",
    1714: "South African dance where one leg lifts and drags in a circular stomp while the same-side arm swings with it.",
    2020: "Traditional Ghanaian recreational dance with grounded bent-knee steps, rolling arms and call-and-response drum rhythms.",
    2022: "High-energy Angolan street dance of rapid stomps, hip swivels and sudden freezes over fast electronic beats.",
    1763: "Viral dance from A-Star's 'Kupe': crisp hand claps, wrist rolls and a strutting two-step.",
    1716: "Nigerian street style centring fast, loose leg shuffles and crosses while the upper body stays cool - basic, crossed and butterfly variations.",
    1999: "Congolese dance driven by circular hip rotations and small quick steps, building from slow winds to fast soukous tempo.",
    1885: "Afrobeats social move: the arms extend and pulse like signal waves while the feet keep a light bounce step.",
    1718: "Ghanaian move combining a springy knee-lift step with sweeping arm circles.",
    1793: "TikTok dance to Ayra Starr's 'Rush', chaining shoulder rolls, hip hits and quick hand flicks into a beginner-friendly loop.",
    1886: "Choreography phrase to Ayra Starr's 'Sare' mixing winding hips with sharp arm accents.",
    1717: "Nigerian move from MC Galaxy's 'Sekem': shoulders shrug up and down while the arms pump and the knees dip on the beat.",
    1762: "Naira Marley's viral move: one loose hand shakes at the hip while the body dips on a bounce.",
    1816: "Flowing TikTok phrase to Omah Lay's 'Soso', riding the beat with body rolls and slow-building arm waves.",
    2021: "Congolese style of fast hip micro-rotations and gliding steps over intricate rumba guitar rhythms.",
    1855: "Viral dance to Davido's 'Unavailable': a leg-swing-and-plant step with a shoulder lean, done in a repeating loop.",
    927: "Nigerian legwork dance popularised by Zlatan: one leg stomps and flicks while the arms swing across the body, ending in the signature gbese kick.",

    # --- Afro House ---
    1868: "Fast grounded Afro-house footwork: shuffles, stomps and syncopated steps ridden low over four-on-the-floor drums.",
    1869: "South African Afro-house step built on a quick box-step bounce with the arms pumping counter to the feet.",

    # --- Amapiano ---
    1740: "Pretoria-born amapiano step: rapid small kicks on the toes while the hips and shoulders ride the log-drum bounce.",
    1750: "Viral amapiano line dance to Mapara A Jazz's 'John Vuli Gate', built on a strutting side-step with swinging arms.",
    1852: "Amapiano groove to Focalistic's 'Ke Star': a bouncing two-step with rolling shoulders and pointing accents.",
    1752: "TikTok amapiano dance to Tyler ICU's 'Mnike', pairing sharp arm pumps with a stomping side bounce.",
    1853: "Amapiano phrase to Dlala Thukzin's 'Phuze', flowing between hip circles and grounded stomp accents.",
    1741: "Amapiano move mimicking a cat's pounce: the hands paw forward in rhythm as the feet spring in a light bounce.",
    1753: "Township street style with loose, expressive footwork, ankle rolls and sudden pauses over amapiano log drums.",
    1814: "High-energy amapiano 'taxi bounce': deep knee dips with the chest pumping and arms driving like pistons.",
    1791: "Viral dance to TitoM & Yuppe's 'Tshwala Bam': a smooth lean-back two-step with a hand-tipping gesture.",
    1792: "Amapiano dance where the arms sweep in digging scoops while the feet keep a sliding side-step.",
    1754: "Amapiano move miming revving a taxi: fists turn an imaginary wheel as the body drops into the beat.",
    1742: "Amapiano step dragging the foot in a sweeping zig-zag while the arms fold and unfold across the chest.",
    1755: "Step-by-step amapiano groove pairing heel taps and hip sways with delicate hand flicks.",

    # --- Bachata (style) ---
    1832: "The foundational bachata step: three steps to the side with a hip-lifting tap on beat four, danced in open or closed hold.",
    1861: "Dramatic partnered dip: the leader supports the follower into a controlled backward drop, usually as a phrase ending.",
    1979: "Solo bachata footwork drills - taps, syncopated triple steps and weight-change patterns to sharpen timing and hip action.",
    1978: "The sensual branch of bachata: body waves, isolations and close-connection lead-follow layered on the basic step.",
    1833: "Side-to-side bachata basic decorated with combos: crosses, taps and direction changes built off the four-count step.",
    1834: "Lady-styling turns for bachata with arm-styling details: prepare, spot and finish the rotation back into the basic.",

    # --- Ballroom ---
    2033: "Foundational slow-foxtrot figure: the leader steps outside the partner through three smooth walking steps (the feather), followed by the three step.",
    2036: "Sharp jive kicks and flicks: low, fast leg snaps from the knee, danced on the balls of the feet with a lively bounce.",
    2034: "Quickstep's traveling lock step: quick-quick counts where one foot locks tightly behind the other as the couple skims the floor.",
    310: "Core ballroom timing pattern alternating two slow walking counts with quick-quick pairs - the rhythm base of foxtrot and tango figures.",
    3: "Dramatic ballroom dance in 2/4 time with staccato walks, sharp head snaps and a close hold, traveling counter-clockwise around the floor.",
    2035: "Tango check figure: the leader steps back into a lunge, pausing the couple in a dramatic dipped line before recovering.",
    2008: "Tango traveling figure in promenade position: partners open to a V through the progressive link and walk through to closed promenade.",
    1962: "Fast rotary waltz in 3/4: couples whirl through continuous natural and reverse turns while traveling the line of dance.",
    2007: "The right-turning basic of slow waltz: six steps with rise and fall that rotate the couple clockwise as they travel.",

    # --- Bhangra / Bollywood ---
    1973: "A dozen foundational Bollywood moves - shoulder bounces, bhangra arms, hip taps and expressive hand gestures - for film-style routines.",
    2017: "Gujarati stick dance: partners strike dandiya sticks in crossing patterns while circling with light springing steps.",
    1988: "Gujarati circle dance of sweeping arm arcs, claps and turning steps, flowing counter-clockwise around a central point.",

    # --- Brazilian Funk ---
    1838: "Rio favela footwork style: fast, playful step combinations blending samba, break and freestyle over funk carioca beats.",
    1839: "Brazilian funk move of continuous standing hip rolls that ripple up the torso while the feet stay planted.",

    # --- Breakdance ---
    847: "Acrobatic power move: a full backward somersault landed on the feet, used as a battle exclamation point.",
    1040: "Downrock step crossing one leg over the other while the hands carry weight, linking footwork patterns like the six-step.",
    86: "Freestyle showcase combo mixing body isolations, quick footwork and popping accents into one flowing phrase.",
    1056: "Party move where a thumbed hitchhiking fist pumps over alternating shoulders while the feet rock a two-step.",
    145: "Transition move sliding on the knees and rising smoothly back to standing without using the hands.",
    1872: "The standing opening of a b-boy set: rhythmic cross-steps, kicks and side steps danced upright before dropping to the floor.",
    1543: "Footwork pattern twisting the upper body into a sudden freeze - a held pose on hands and toes - before releasing into the next step.",

    # --- Classical / Ballet ---
    400: "Ballet technique of dancing on the very tips of the toes in reinforced pointe shoes, demanding strong ankles and full-body alignment.",
    2040: "Ballet's split leap: a running preparation into a thrown front leg, hitting a full split at the top of the jump.",
    1679: "Turn-technique series covering pirouettes, whipping fouette turns and a la seconde turns, with spotting and balance drills.",
    910: "Ballet rise from flat feet to the balls of the feet through a strong, controlled ankle press, often repeated as a strength drill.",

    # --- Contemporary ---
    1859: "Turn performed in attitude: one leg lifted and bent at ninety degrees while the supporting leg carries the rotation.",
    1966: "Intermediate floor sequences: rolls, slides, spirals and weight shares that move fluidly between standing and ground.",
    1824: "Foundational leap technique: plie preparation, brush through and stretched flight with a soft landing.",
    1733: "Graham-technique fundamental: the pelvis curves and the spine hollows on an exhale, then releases back to length.",
    1734: "Smooth rolling transitions across the floor - shoulder rolls, side rolls and fish rolls - keeping momentum continuous.",
    1774: "Beginner floorwork vocabulary: sweeps, slides and spiral descents for entering and leaving the ground gracefully.",
    1967: "Beginner lyrical phrases pairing sustained balletic lines with emotive dynamics that follow the song's lyric.",
    1735: "Spiralling technique: the torso rotates around the spine's axis to power turns, descents and level changes.",
    1775: "Leg-line skill standing on one leg while the other extends high to the side, the torso tilting away to form a V.",
    1990: "Jumped version of the tilt: the hips kick one leg high to the side mid-air while the torso counter-tilts.",

    # --- Dancehall ---
    1723: "Foundational dancehall move created by Bogle: rolling arm waves crown the head while the body rocks in a lean-back groove.",
    1977: "The Gallis (Sassa) step: a strutting knee-pump walk with swagger arms, from Mr. Vegas's 'Gallis' era.",
    2001: "Core dancehall wine: continuous hip circles isolated under a steady chest, ridden low on bent knees.",
    1719: "Signature female dancehall move combining fast head rolls with winding hips in a wide-legged stance.",
    1818: "Bouncy dancehall step: heel digs travel side to side while the arms pump like pulling a throttle.",
    1724: "Energetic bounce move: shoulders and arms pump downward as the body drops into a springy squat rhythm.",
    1720: "Elephant Man's creeping strut: exaggerated low steps forward with arms swinging in slow-motion menace.",
    1721: "Jump-and-swing dancehall move: the knees pump up as the arms swing across and fling away on the accent.",
    1795: "Classic Elephant Man step rocking forward and back across an imaginary river with paddling arm sweeps.",
    1767: "Reggae party move miming rowing: the arms pull invisible oars in rhythm while the feet rock a two-step.",
    1766: "Skipping dancehall step: light alternating hops with a rope-swing arm styling.",
    1817: "Feel-good dancehall bounce: knees dip on the beat while the arms sway overhead, riding the groove.",
    1764: "Blacka Di Danca's traveling step: the shoulders lead the body sideways in a smooth 'take yourself away' slide.",
    1765: "Dancehall dip variation: a quick level drop with a hip pop on the rise.",
    1678: "Foundational whine: slow circular waist rotations isolated over planted feet - the base of all dancehall winding.",
    1722: "Classic tribute step to Willie Haggart: a side-to-side bounce with a hat-tipping arm swing.",

    # --- Flamenco ---
    1737: "Flamenco arm work: continuous carved arm paths from the shoulder through curling wrists, framing the body's lines.",
    1738: "Flamenco hand articulation: the fingers unfurl and close in flowing circles from the wrist, decorating every arm path.",
    1823: "The 'call' in flamenco: a marked accent phrase of sharp footwork that signals the guitarist and singer a section change.",
    1776: "Flamenco marking steps: understated weight shifts and body marking used to ride the rhythm between accents.",
    1989: "Seville's festive couple dance in four short parts: turning passes, marked steps and raised-arm styling.",
    1777: "Flamenco turn: a controlled walked rotation with spiraled torso and carried arms.",
    1736: "Flamenco percussion footwork: heel, ball and toe strikes drilled into fast rhythmic patterns.",

    # --- Folk / Traditional ---
    2019: "Ghanaian Ashanti ceremonial dance of graceful symbolic hand gestures and small grounded steps, danced to talking drums.",
    1981: "Belly dance staple: the hips trace a horizontal figure eight with knees soft and the torso lifted.",
    1971: "Belly dance accent: one hip lifts and drops sharply on the beat over a planted leg - the style's core percussion.",
    2047: "The maya: a vertical figure-eight hip pattern drawing slow downward-outward loops in a liquid roll.",
    1972: "Fast continuous hip shake driven from the knees or glutes while the upper body floats still.",
    1982: "Belly dance arms rippling in alternating waves from shoulder to fingertips, like a serpent's motion.",
    2046: "Full-torso belly dance wave rolling chest-to-pelvis in one continuous serpentine motion.",
    2018: "The basic units of Bharatanatyam: codified stamping-step sequences (adavus) with precise arm and hand positions.",
    1985: "Capoeira's swaying base step: a rocking triangle of steps that keeps the player in constant motion between attacks and escapes.",
    2049: "American percussive folk dance: loose-ankle double-toe taps and rocking steps hammer out rhythms to bluegrass and country.",
    1995: "Texas partner dance traveling counter-clockwise in quick-quick-slow-slow rhythm with easy turns and wraps.",
    1983: "Levantine line dance: linked dancers stomp, cross and kick in unison behind a leader twirling a scarf.",
    2011: "Maori ceremonial dance of stomps, thigh slaps, chest pounds and fierce chanted calls performed in unison.",
    2048: "Scottish solo dance performed on one spot: precise hops and quick foot placements with the arms arched overhead.",
    2050: "Ukrainian folk showpiece famous for its squat kicks, leaps and spins, building to an acrobatic finale.",
    1975: "Foundational hula: swaying kaholo hip steps and storytelling hand gestures flowing over soft bent knees.",
    1974: "Light Irish step dance in 6/8 time: springing hops, points and kicks under a lifted, still upper body.",
    2016: "Mexico's hat dance: a courting couple circles a sombrero with zapateado heel work in traditional charro dress.",
    2014: "Rajasthani folk dance of serpentine spins, backbends and fast wrist flourishes in swirling black skirts.",
    1987: "Kathak's chakkars: lightning heel-pivot spins landed exactly on the beat, counted against the tabla cycle.",
    2015: "Regional Mexican folk technique: sweeping skirt work (faldeo) and stamped zapateado over festive son rhythms.",
    2012: "Greek line dance made famous by 'Zorba': slow dragging grapevine steps that accelerate into fast kicks and hops.",
    2013: "Southern Italian courtship dance in quick 6/8: skipping steps, turns and tambourine flourishes.",
    1986: "Philippine national dance: dancers step and hop between bamboo poles clapped together in rhythm at their ankles.",
    102: "Line-dance party staple: the body wobbles side to side on a bounce, arms push forward and back, then a quarter turn repeats it all.",
    1984: "Tahitian ori: rapid side-to-side hip oscillations driven by bent knees to fast toere drum rhythms.",

    # --- Gqom ---
    1871: "Durban club style: heavy stomps, chest pumps and broken-beat footwork over dark, minimal gqom drums.",
    1870: "South African squat-kick move: a deep drop onto one leg with the other kicking forward, arms punching down.",

    # --- Heels ---
    1781: "Commercial heels accent: a whipped head-and-hair circle timed to a musical hit, controlled from the neck and core.",
    1780: "Standing body wave in heels: a chest-to-hip ripple ridden down and up with weight poised over the balls of the feet.",
    1850: "Burlesque-style chair choreography: sits, leg fans, dips and floor transitions built around a chair prop.",
    1980: "Beginner heels fundamentals: posture, walks, hip lines and feminine styling danced in high heels.",
    1779: "Floorwork vocabulary in heels: kneels, leg sweeps, rolls and body waves flowing between standing and floor.",
    1808: "Controlled spin on one knee: momentum from a stepped preparation carries a smooth rotation with the legs styled.",
    1807: "Basic turns in heels: paddle and pencil turns, spotted and balanced on the ball of the stiletto.",
    1849: "Runway strut technique: one-foot-in-front placement, pushed hips and counter-swinging shoulders.",
    1778: "The foundational heels walk: heel-to-toe placement along one line, knees brushing, chest lifted.",

    # --- Hip-hop ---
    1632: "Six-count step drill: a repeating footwork pattern counted aloud, used to build coordination and musical timing.",
    1670: "Gliding illusion step: alternating heel pivots and toe drags make the dancer appear to stride on air.",
    1636: "Traveling step crossing one foot behind the other while moving backward, keeping a low rocking groove.",
    98: "Old-school New York party move: rapid-fire arm throws over a rocking two-step groove.",
    56: "Funk-era glide: one foot slides back under a hitching body pop, like a camel's rolling gait - an ancestor of the moonwalk.",
    1252: "Novelty groove swinging the hips and a trailing arm like a swatting cow's tail over a loose bounce.",
    866: "Toprock variation dropping into a quick squat rock and springing back upright between cross-steps.",
    393: "Footwork drill flicking the free leg while the body pivots a quarter turn on each repeat.",
    254: "Novelty funk move flapping bent-elbow wings and pecking the head forward on a strutting bounce.",
    128: "Harlem-born shoulder dance: the shoulders shimmy and pop around a loose, relaxed core - the original street version.",
    390: "Basic party step: a front kick followed by a side step - the base of countless hip-hop grooves.",
    1531: "Farmer variation of the knee-up: high alternating knee lifts paired with a hoeing arm swing.",
    1529: "Basic knee-up groove: alternating ninety-degree knee lifts ridden on the beat with pumping arms.",
    123: "Locking-flavoured variation freezing the body in a point lock while the arms and torso hit tension accents.",
    322: "Playful party move shaking the torso and hips loosely on the beat with carefree arm styling.",
    117: "Fast-footwork party move with sharp direction pivots and arm accents, danced to high-energy breaks.",
    1062: "Footwork pattern stepping to the four corners of an imaginary square with a sliding groove.",
    1826: "Viral Atlanta dance: one arm raised and swaying side to side while the body leans back on a bounce.",
    1455: "Standing quadriceps stretch with square hips: the heel pulls to the glute while the pelvis stays level - a dancer's warm-up staple.",
    1883: "Popping fundamentals: rhythmic muscle contractions (hits) in the arms, chest and legs synced to the beat.",
    1067: "Club move bouncing astride an imaginary horse, one arm swinging lasso circles on the giddy-up rhythm.",
    118: "Glide move where the feet alternate smooth forward-and-back slides as if rolling on skates.",
    52: "Classic 80s/90s move: the knees drive up while the grounded foot slides back, creating a running-in-place illusion.",
    499: "Combo linking running man strides into grounded heel twists that swivel both feet sideways.",
    501: "Running man variation punctuating each cycle with a side kick before catching the slide again.",
    500: "Combo flowing from the running man into the lateral T-step glide.",
    915: "Foot-drag accent scraping the sole across the floor to close a step, adding grit to a groove.",
    947: "Fast side-to-side step-touch glides - the club shuffle groove that seeded the Melbourne shuffle style.",
    1829: "GS Boyz viral move: one bent leg rolls outward in a loose circle while the body leans into it.",
    125: "Hit-and-flow combo: a sudden stuck freeze snaps into a smooth body-roll release.",
    1083: "Confidence walk: an exaggerated strut with shoulder sway, arm swagger and rhythmic pauses.",
    420: "Seventies party dance: partners bump hips on the downbeat between light step-touches.",
    412: "Funk novelty flapping elbow wings with pigeon-neck pecks over a bouncing two-step.",
    1827: "The simplest social groove: a step-touch side to side with relaxed arms - the foundation everyone starts from.",
    66: "Atlanta snap-era dance: pigeon-toed pivots walk the feet in and out while the arms swing loose.",
    377: "Traveling half-turn leap borrowed from skating vocabulary: forward takeoff, airborne half rotation, soft backward landing.",
    1884: "Popping sub-style sending liquid waves through the arms and body, joint by joint, as if a current passes through.",
    1831: "Viral move dropping into a quarter squat while one arm swings across like turning a steering wheel.",

    # --- House ---
    1708: "House choreography combo blending jacking torso grooves with quick skating footwork.",
    1684: "Hard-dance shuffle built on the running man and T-step, stomped out to 150 BPM hardstyle kicks.",
    1549: "Drill pairing fast heel twists with the jacking-in-the-box torso wave - a house coordination challenge.",
    887: "Leg sweep move: one leg circles under the body like rotor blades while the hands briefly carry the weight.",
    1876: "The jack: house dance's core torso wave - an undulating chest-to-pelvis rock that drives every house groove.",
    1877: "Lofting: smooth, aerial-feeling house movement - skips, glides and suspended steps that float above the beat.",
    411: "Descending spiral: the body corkscrews toward the floor through a stepped rotation and rises without breaking flow.",
    92: "Precision move ticking the hands sideways in small increments like a typewriter carriage, finished with a return swipe.",

    # --- Jazz ---
    1727: "Linked traveling turns: quick half-turn weight changes between both feet move along a straight line while spotting.",
    1726: "High kick sweeping a fan-shaped arc across the body, hips square and the supporting leg strong.",
    1968: "Jazz funk starter vocabulary: sharp commercial hits layered over jazz technique - isolations, grooves and attitude.",
    1770: "Jazz-style pirouette in parallel passe: spotted single and double turns finished with jazz arms.",
    766: "Stylised low jazz walk: plie-pressed steps glide forward with reach and shoulder opposition.",
    1725: "Three-step linking pattern (back-side-front) that transfers weight quickly - jazz's most-used transition.",
    1820: "Turn stepping directly onto a straight leg with the free foot drawn up, often chained with soutenu turns.",
    1728: "Half-turn pivot: step forward and swivel on the balls of both feet to face the opposite way without losing level.",
    1677: "Split leap with the front leg bent in stag position and the back leg stretched, chest lifted at the peak.",
    1819: "Split leap that switches: the first leg swings through before the split reverses mid-air.",

    # --- Jersey Club ---
    1799: "The Jersey club bounce: a springy knee pulse synced to chopped 140 BPM club kicks - the base of every Jersey move.",
    1801: "Fast footwork combos - kicks, crosses and heel flicks - chained over Jersey club's triplet kick pattern.",
    1800: "Jersey club's top rock: upright rocking cross-steps borrowed from breaking, ridden double-time.",
    1847: "Signature KB bounce step: a hopping knee-lift bounce with a kick-back snap on the offbeat.",
    1846: "Jersey club move hopping back onto one leg while the free leg kicks forward on the rebound.",
    1848: "Crisp accented knee pulses hitting the chopped kicks, with sudden freezes between combos.",

    # --- Kizomba ---
    1865: "Kizomba's walking basics: grounded weight-transfer steps danced chest-to-chest in slow connection.",
    1866: "The saida: the follower exits to the side from the basic through a guided three-step, opening the slot.",
    1998: "The virgula ('comma'): a quick pivoted hip mark that curves the couple ninety degrees between walks.",
    1867: "Kizomba's slow-motion cousin: micro hip isolations and body waves danced almost in place, deep in connection.",

    # --- K-Pop ---
    1845: "LE SSERAFIM's 'Antifragile' choreography with its whipping point moves and hip-sway chorus, learned section by section.",
    1771: "The viral point dance from ROSE & Bruno Mars's 'APT.': a clapping-game gesture into a bouncing chorus hook.",
    1802: "aespa's 'Armageddon' choreography: sharp isolations and the crossbow point move, broken down step by step.",
    1880: "IVE's 'Baddie' routine: a swaggering chorus groove with finger-gun points, explained and mirrored.",
    1881: "RIIZE's 'Boom Boom Bass' choreography: the bass-plucking point move and bouncy footwork, section by section.",
    1843: "NewJeans' 'Ditto' routine: soft swinging grooves and the heartbeat point choreography.",
    1788: "BABYMONSTER's 'Drip' dance: hard-hitting hooks with fluid transitions, learned step by step.",
    1787: "NewJeans' 'How Sweet' choreography: light bouncing footwork with playful hand hooks, slowed and mirrored.",
    1842: "NewJeans' 'Hype Boy': the era-defining hook - wavy arms into the beckoning chorus point move.",
    1844: "IVE's 'Kitsch' routine: strutting verses and the sassy crossed-arm chorus hook.",
    1805: "IVE's 'Love Dive' choreography: elegant wave arms and the cupid-arrow point move.",
    1772: "ILLIT's 'Magnetic': the viral pinching magnetic-pull hook with skipping chorus steps.",
    1806: "NewJeans' 'OMG' routine: rolling grooves and the phone-call point choreography.",
    1878: "BLACKPINK's 'Pink Venom': the bow-draw hook and hard chorus hits, learned mirrored.",
    1804: "(G)I-DLE's 'Queencard': confident strut hooks and the face-framing point move.",
    1879: "BLACKPINK's 'Shut Down' choreography: sleek turns and the camera-shutter point, explained and mirrored.",
    1786: "LE SSERAFIM's 'Smart': slinky footwork and hip rolls, broken down with explanation.",
    1841: "aespa's 'Spicy' routine: a bold strutting chorus with sharp arm snaps, taught mirrored.",
    1789: "KISS OF LIFE's 'Sticky' choreography: bouncing hooks with the sticky-hands point move.",
    1773: "aespa's 'Supernova': the punchy 'su-su-su-supernova' point hook with staccato hits.",
    1803: "NewJeans' 'Super Shy': fast, light-footed skips with the shy peek-a-boo hook.",
    1785: "aespa's 'Whiplash': whip-crack accents over strutting house-flavoured grooves.",

    # --- Krump ---
    124: "Krump power combo: explosive arm swings build into the chest-out Superman hit, thrown with full commitment.",
    90: "Grounded krump stomp pattern: heavy alternating stomps land under a loose, reactive torso.",
    394: "Krump chest-pop drill rotating the torso between hits so each pop lands facing a new angle.",
    1857: "The krump jab: a piston arm strike thrown from the chest and snapped back with tension - a core krump weapon.",
    1862: "The krump chest pop: an explosive rib-cage hit driven by breath and back muscles, drilled in reps.",
    478: "Combo layering the floss arm swing under repeated chest pops while the lower body keeps the beat.",

    # --- Latin ---
    1963: "The gancho: the follower's leg hooks sharply around the partner's leg mid-figure, then releases.",
    841: "Bachata combo flowing the side basic into a led body wave that ripples through both partners.",
    2010: "Bolero basics in slow-quick-quick timing: long sweeping first steps with rise and fall, danced to romantic ballads.",
    2028: "The New Yorker: partners break open to face the same direction with a checked forward step, then return to the basic.",
    1683: "Party reggaeton for social dancing: perreo-ready hip work, bounce grooves and simple footwork.",
    2024: "Casino's dile que no: the leader redirects the follower across in front, swapping places - the hinge of Cuban salsa.",
    1858: "Colombian social dance: back-rocking basic steps circle the partner with relaxed hip sway and shuffling feet.",
    732: "Social Latin party groove: a smooth hip-swiveled two-step ridden to salsa-urbano party hits.",
    547: "Dominican marching dance: simple weight changes on every beat with strong hip action, spiced with turning patterns.",
    2027: "Milonga: tango's playful, quick cousin - traveling walks and rhythmic double-time steps with no pauses.",
    1688: "Core reggaeton steps to dance any song: the bounce, dembow-riding hips and simple foot patterns.",
    2029: "International rumba walks: delayed hip settling over a straight leg creates the style's signature Cuban motion.",
    2023: "Cuban salsa's enchufla: the leader pulls the follower through a half-turn swap of places, restarting the circle.",
    2031: "Setenta: casino's classic figure - a hand-linked sequence of turns and wraps starting from guapea.",
    1825: "Solo salsa shines: follow-along footwork patterns danced apart from the partner to build rhythm and style.",
    2030: "Samba voltas: traveling crossing steps that curve the dancer around in a circle with samba bounce.",
    2009: "The samba whisk: a side step with a ball-flat cross behind, ridden on samba's pendulum bounce, plus arm styling.",
    2025: "The boleo: the follower's free leg whips around from an interrupted ocho, high or low, powered by the lead's reversal.",
    2026: "The sacada: one partner steps into the other's space, smoothly displacing their leg mid-step.",

    # --- Litefeet ---
    1761: "Litefeet's Bad One: a snapping leg-swing step with a lean, chained into Harlem litefeet combos.",
    1747: "Harlem's Chicken Noodle Soup: the arms ladle side to side while the feet slip in a loose side-shuffle.",
    1760: "Getting lite fundamentals: bouncing kick-steps, arm swings and hat-and-shoe tricks from Harlem's litefeet culture.",
    1813: "Litefeet hat trick: flipping and catching the fitted cap off the head mid-groove as a showpiece.",
    1749: "The Whop (Rev Up): pumping arm revs over a rocking step - litefeet's engine-start groove.",
    1812: "Litefeet drop: a sudden slide down onto the side catching the beat, then springing right back up.",
    1748: "Litefeet toe wop: balancing rocks on the toes with heel swivels, walked in place with swagger.",

    # --- Reggaeton ---
    1783: "The dembow basic: a hip-led two-step riding reggaeton's dembow riddim, danced in place or traveling.",
    1782: "Reggaeton's foundation: bounce-driven step-touches with hip accents landing on the dembow rhythm.",
    1784: "Hip isolation training: circles, figure-eights and pops drilled for reggaeton's hip vocabulary.",
    1976: "Perreo fundamentals: low winding hip work, chest-forward posture and a grounded bounce, in ten core steps.",
    1809: "Upper-body reggaeton: chest and shoulder isolations layered over the bounce for flavor.",
    1810: "Cuban-flavoured perreo: waist-led winding over deep knee grooves, built into party choreography.",

    # --- Shuffle ---
    1744: "Cutting-shapes Charleston: the 1920s swivel-kick step recycled into shuffle footwork over house beats.",
    1746: "Cutting shapes starter pack: five foundational club-footwork moves chained into freestyle patterns.",
    1758: "The diamond step: four pivoting steps trace a diamond on the floor, linking T-steps and spins.",
    1759: "Hardstyle shuffle: stomping running-man kicks and fast T-step glides hammered out at hard-dance tempo.",
    1790: "Heel-toe (happy feet): weight rolls from heel to toe swivel the feet in opposite directions, gliding sideways.",
    1756: "Shuffle's running man: the kick-and-slide illusion drilled clean - the style's first fundamental.",
    1811: "Melbourne shuffle spin: a quick spotted rotation dropped seamlessly between running-man cycles.",
    1745: "The Spongebob: springy behind-the-body kick-steps that skip sideways, straight from 2000s party culture.",
    1743: "The T-step: a heel-toe twisting glide sideways with the feet forming a T - one of shuffle's two pillars.",
    1757: "The V-step: heels pivot outward and in, drawing V shapes that link shuffle patterns together.",

    # --- Soca ---
    2045: "Soca chipping: the relaxed marching shuffle you keep up for hours behind a carnival truck.",
    1837: "Soca bumper: the hips thrust back and forth on the riddim, danced low with springing knees.",
    1863: "Five core soca steps: light jab-steps, jumps and shuffles built for carnival stamina.",
    1836: "Rag-waving styling: five ways to wave the rag overhead while the feet keep the jump-up bounce.",
    1835: "The soca wine: continuous hip circles ridden on the riddim - the Caribbean's universal party motion.",

    # --- Street / Urban (locking) ---
    1875: "Locking's Which-A-Way: alternating leg kicks with directional points, thrown with locking's snap.",
    1874: "Locking wrist rolls: the forearms circle from the wrists between points and locks - a funk-era flourish.",

    # --- Stretching ---
    1892: "Follow-along back-flexibility routine: progressive spinal extensions, bridge preparation and thoracic openers.",
    1949: "Ten-minute wind-down stretch: gentle floor-based holds to relax the body before sleep.",
    1891: "Back-bridge progression: from glute bridges to full wheel, building spine and shoulder mobility safely.",
    1939: "Calf-focused mobility: gastrocnemius and soleus stretches held and pulsed in an easy follow-along.",
    1955: "Chest and shoulder mobility flow: openers, floor slides and reach-throughs in a follow-along session.",
    1954: "Squat mobility workout: ankle, hip and adductor drills working toward a comfortable deep resting squat.",
    1935: "Frog pose breakdown: the knees-wide hip opener with technique cues, benefits and easier regressions.",
    1887: "Fifteen-minute front-split routine: hamstring and hip-flexor holds progressing toward full splits.",
    1933: "Full-body mobility flow: joint circles and dynamic stretches linking every major area in fifteen minutes.",
    1893: "Hamstring unlock routine: active and passive holds with nerve-glide variations, follow-along.",
    1934: "Twenty-minute hip-flexor routine: lunging couch-stretch variations with posterior-tilt form cues.",
    1894: "Twelve-minute hip mobility session: 90/90 transitions, pigeon variations and controlled rotations.",
    1953: "Adductor mobility routine: side lunges, frog rocks and long-hold inner-thigh stretches with coaching.",
    1947: "The Jefferson curl: a slow, lightly loaded spinal roll-down that builds back flexibility and tendon strength.",
    1889: "Oversplit training: elevated front-leg split holds for dancers already comfortable in flat splits.",
    1936: "Pigeon pose for beginners: an external-rotation hip stretch taught with props and square-hip technique.",
    1961: "Banded mobility flow: full-body stretches deepened with the assist of a resistance band.",

    # --- Swing ---
    1965: "Balboa basics: close-embrace shuffling weight changes built for fast swing tempos.",
    2039: "Boogie woogie: a fast rock-step-triple partner dance with playful footwork over boogie piano rhythms.",
    515: "Combo linking swing-era Charleston kicks into the running man's sliding illusion.",
    2038: "Collegiate shag: a slow-slow-quick-quick hopping basic danced in close position at breakneck tempos.",
    1681: "Country swing fundamentals: rock-step basics, inside and outside turns, and dips for the honky-tonk floor.",
    1994: "The hustle: disco-era partner dance counted '&1-2-3', spinning through wheel and wrap turns.",
    2037: "Beginner jitterbug: single-time swing basics - rock step, triple steps and easy underarm turns.",
    386: "Lindy hop vocabulary: kicks, twirls and eight-count circular figures anchored around the swing-out.",
    1964: "The swingout: lindy hop's signature eight-count - the follower launches out of closed position and whips back with swivels.",
    1685: "Swing move where partners slide past each other in opposite directions and back again, like passing doors.",
    1690: "Aerials basics: preparation, timing and spotting for swing flips and lifts, drilled safely with a partner.",
    555: "Slotted swing dance: an elastic connection stretches and releases through pushes, passes and whips along a narrow slot.",

    # --- Tap ---
    1856: "The buffalo: a leap-shuffle-leap traveling step - the classic 'shuffling off to Buffalo' exit move.",
    1821: "The cramp roll: toe-toe-heel-heel rolled into one smooth four-sound cluster.",
    2003: "The Maxie Ford: a step-shuffle-leap-toe combination punctuated with a clean toe-tip landing.",
    2004: "Paddle and roll: alternating dig-brush-heel patterns rolling out continuous rhythms - tap's drum roll.",
    1882: "The pullback: both feet brush backward mid-air from a small jump, landing extra beats - tap's first flash skill.",
    2002: "The shim sham: tap's anthem line routine - four choruses of stomps, shuffles and half-breaks.",
    1830: "Shuffle ball change: a brush-strike followed by two quick weight changes - the most used connector in tap.",
    1969: "Shuffle off to Buffalo: a traveling shuffle-leap pattern drifting sideways - the vaudeville exit step.",
    1675: "Tap starter kit: shuffles, flaps, ball changes and time steps taught with clean weight placement.",
    2042: "Flaps: brush-step walking steps that turn every stride into two clean sounds.",
    2041: "Riffs: heel-dig and brush combinations producing crisp multi-sound clusters while traveling.",
    2043: "The scuff: a forward heel strike that brushes the floor - the heavier cousin of the toe brush.",
    1864: "Wings: the feet scrape out to the side and snap back under the body mid-air - an advanced flash step.",

    # --- Tektonik ---
    1686: "Tecktonik (electro dance): fast spinning arm figures wrap around the head and torso over electro house, with gliding steps.",

    # --- Tutting ---
    1739: "King Tut basics: right-angle arm frames and hieroglyph-style box shapes hit in time - tutting's origin move.",

    # --- Twerk ---
    1796: "Six foundational twerk moves: hip-led bounces and pops from squat and bent-over stances, step by step.",
    1798: "The booty pop: an isolated glute pop driven by pelvic tilt, drilled safely with posture cues.",
    1851: "Twerk technique adapted to heels: balance, squat depth and bounce control on stilettos.",
    1797: "New Orleans bounce twerk: continuous rump bounce ridden on triggerman beats, Big Freedia style.",

    # --- Vogue ---
    1768: "Vogue fem's catwalk: the hips push through each crossing step as the arms sweep - a feline runway strut.",
    1822: "The dip (death drop): a controlled fall onto the back with one leg folded under, hitting exactly on the beat.",
    1729: "The duckwalk: squatting kick-walks on the balls of the feet, gliding low across the floor.",
    1769: "Vogue floor performance: rolls, leg fans and hip work danced on the ground in one continuous line.",
    1730: "Hand performance: illusions, frames and storytelling drawn by the hands and wrists around the face.",
    1731: "Old way vogue: symmetrical lines, arm-control drills and pop-dip-spin precision from the pre-90s ballroom era.",
    1732: "Vogue's spin and dip: a whipped spin unwinding into the dramatic floor dip on the musical crash.",

    # --- Waacking ---
    704: "Loose whipping arm swings - waacking's warm-up flail that builds shoulder freedom before precise strikes.",
}

print("BEGIN;")
for dance_id, desc in DESCRIPTIONS.items():
    safe = desc.replace("$d$", "")  # dollar-quote guard; descriptions never contain it
    print(f'UPDATE "Dances" SET "Description" = $d${safe}$d$ WHERE "Id" = {dance_id};')
print("COMMIT;")
print(f"-- {len(DESCRIPTIONS)} descriptions", file=sys.stderr)
