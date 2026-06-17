#!/usr/bin/env python3
"""
fix_names.py — Strip leading numbers from dance names.
"""
import re
import requests

API_BASE = "https://dance-api.takelord.com/api"
USERNAME = "justas"
PASSWORD = "Dance@Admin2026"

# Pattern: one or more digits, optional separator (. ) : -), optional whitespace
NUMBER_PREFIX = re.compile(r"^\d+[\.\)\:\-]?\s+")


def login():
    r = requests.post(f"{API_BASE}/auth/login", json={"username": USERNAME, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["token"]


def fetch_all_dances(token):
    r = requests.get(f"{API_BASE}/dances", params={"pageSize": 5000}, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()


def update_dance_name(token, dance_id, new_name):
    r = requests.put(
        f"{API_BASE}/dances/{dance_id}",
        json={"name": new_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r


def main():
    print("Logging in...")
    token = login()
    print("Fetching all dances...")
    dances = fetch_all_dances(token)
    print(f"Fetched {len(dances)} dances.")

    renamed = 0
    for dance in dances:
        old_name = dance["name"]
        if NUMBER_PREFIX.match(old_name):
            new_name = NUMBER_PREFIX.sub("", old_name).strip()
            try:
                update_dance_name(token, dance["id"], new_name)
                print(f"[RENAME] {old_name!r} -> {new_name!r}")
                renamed += 1
            except requests.HTTPError as e:
                print(f"[FAIL] id={dance['id']} {old_name!r}: {e}")

    print(f"\nDone. {renamed} dance(s) renamed.")


if __name__ == "__main__":
    main()
