# Second pass: the remaining "Flexibility & mobility for dancers: <YT title>" stretching cards.
import sys
sys.stdout.reconfigure(encoding="utf-8")

DESCRIPTIONS = {
    1888: "Middle-split training: adductor and hip stretches progressing toward a flat side split.",
    1890: "Backbend fundamentals: bridge preparation, chest openers and hip-flexor work toward a safe standing backbend.",
    1895: "The pancake: a wide-straddle forward fold trained from beginner tilts to a flat chest-to-floor stretch.",
    1896: "Needle and scorpion training: extreme back and shoulder flexibility drills for the standing needle scale.",
    1897: "Twelve-minute shoulder mobility session: rotations, hangs and wall slides to free up overhead range.",
    1898: "Foot and ankle mobility for dancers: strength and articulation drills for demi-pointe, releve and jumps.",
    1899: "Dynamic pre-dance warm-up: pulse-raising grooves plus mobility drills to prep the body before training.",
    1900: "Post-dance cool-down: slow static holds that ease the muscles down after a session.",
    1901: "Spine mobility routine: segment-by-segment rolls, cat-cows and rotations to unlock the whole back.",
    1932: "Fifteen-minute deep-stretch session holding long split-specific stretches at intensity.",
    1937: "Lizard pose progressions: a deep lunge-based hip opener with variations for tight or mobile hips.",
    1938: "Couch stretch progressions: knee-to-wall hip-flexor and quad stretch scaled from beginner to advanced.",
    1940: "IT-band and glute relief: yoga-based stretches for the outer hip and thigh line.",
    1941: "Twelve minutes of lower-back relief: gentle flexion, rotation and decompression stretches.",
    1942: "Neck, traps and shoulder release: slow follow-along stretches for a stiff upper body.",
    1943: "Wrist and forearm mobility: six simple exercises to prep the hands for floorwork and balances.",
    1944: "Thoracic-spine rotation workout: twelve minutes of mid-back twists and extension drills.",
    1945: "Quick morning mobility flow: joint circles and easy stretches to start the day loose.",
    1946: "Kick flexibility drills: active leg swings and holds to raise battement and high-kick height.",
    1948: "Ballet-style strength-and-stretch workout: barre-inspired exercises pairing control with flexibility.",
    1950: "Cobra pose: a prone press-up back extension that opens the front body and eases the lower back.",
    1951: "Camel pose: a kneeling backbend opening the chest, quads and hip flexors, taught for beginners.",
    1952: "Wheel pose: the full yoga backbend - pressing from the floor into a complete bridge, step by step.",
    1956: "Leg-extension holds: active flexibility work for higher, controlled developpes and battements.",
    1957: "Hip CARs: slow controlled articular rotations from tabletop that map and expand hip range.",
    1958: "Ten-minute daily full-body stretch: a maintenance routine covering every major muscle group.",
    1959: "PNF stretching: contract-hold-relax techniques that unlock deeper range than passive holds.",
    1960: "The cossack squat: a side-to-side deep squat building hip, knee and ankle mobility with strength.",
}

print("BEGIN;")
for dance_id, desc in DESCRIPTIONS.items():
    print(f'UPDATE "Dances" SET "Description" = $d${desc}$d$ WHERE "Id" = {dance_id};')
print("COMMIT;")
print(f"-- {len(DESCRIPTIONS)} descriptions", file=sys.stderr)
