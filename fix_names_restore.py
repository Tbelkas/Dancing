#!/usr/bin/env python3
"""
fix_names_restore.py — Restore dances that were incorrectly renamed by fix_names.py.
These are moves where the number is genuinely part of the name (N Step, N Count Freeze,
25 Easy Breakdance Moves, 2 Days Live Workshop).
"""
import requests

API_BASE = "https://dance-api.takelord.com/api"
USERNAME = "justas"
PASSWORD = "Dance@Admin2026"

# (id, correct_name) pairs — restored from descriptions/slugs
RESTORES = [
    # N Step / N Step 2 breakdance series
    (731, "4 Count Freeze"),
    (739, "5 Step"),
    (741, "6 Step"),
    (743, "7 Step"),
    (745, "8 Step"),
    (747, "9 Step"),
    (750, "10 Step"),
    (752, "11 Step"),
    (754, "12 Step"),
    (756, "13 Step"),
    (757, "14 Step"),
    (759, "15 Step"),
    (761, "16 Step"),
    (774, "5 Step 2"),
    (775, "6 Step 2"),
    (778, "7 Step 2"),
    (779, "8 Step 2"),
    (781, "9 Step 2"),
    (783, "10 Step 2"),
    (785, "11 Step 2"),
    (787, "12 Step 2"),
    (789, "13 Step 2"),
    (791, "14 Step 2"),
    (793, "15 Step 2"),
    # Tutorial titles where number is genuinely part of the name
    (132, "25 Easy Breakdance Moves"),
    (218, "2 Days Live Workshop"),
    # Numbered mistake series — number is sequence label but part of the name
    (526, "1 Handstand/Elbow Freeze Mistake"),
    (527, "2 General Freeze Mistake"),
    (528, "3 Jump Thread Mistake"),
    (529, "4 Kip Up Mistake"),
    (530, "5 Move Creation Mistake"),
    (531, "6 Coffee Grinder/One Step Mistake"),
    (532, "7 Get Up Mistake"),
    (533, "8 Roll Back Elbow Mistake"),
    (534, "9 Training Mistake"),
    (535, "10 Compact Freezes Mistake"),
    (536, "11 Power Transition Mistake"),
    (537, "12 Freeze Transition Mistake"),
    (538, "13 Back Taps Mistake"),
    (539, "14 Footwork Mistake"),
    (540, "15 Round Flow Mistake"),
    (541, "16 Tabletop - Handstand Mistake"),
    (542, "17 Ground Power Mistake"),
    (543, "18 Flare Mistake #1"),
    (544, "19 Flare Mistake #2"),
    (545, "20 Baby Freeze Switches Mistake"),
]


def login():
    r = requests.post(f"{API_BASE}/auth/login", json={"username": USERNAME, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["token"]


def main():
    print("Logging in...")
    token = login()
    headers = {"Authorization": f"Bearer {token}"}

    fixed = 0
    for dance_id, name in RESTORES:
        try:
            r = requests.put(f"{API_BASE}/dances/{dance_id}", json={"name": name}, headers=headers)
            r.raise_for_status()
            print(f"[RESTORE] id={dance_id} -> {name!r}")
            fixed += 1
        except requests.HTTPError as e:
            print(f"[FAIL] id={dance_id} {name!r}: {e}")

    print(f"\nDone. {fixed} dance(s) restored.")


if __name__ == "__main__":
    main()
