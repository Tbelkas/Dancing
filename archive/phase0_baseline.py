import requests
import json

API_BASE = "https://dance-api.takelord.com/api"
USERNAME = "justas"
PASSWORD = "Dance@Admin2026"

# Phase 0: Login and get baseline
print("=== Phase 0: Baseline ===")

# Login
resp = requests.post(f"{API_BASE}/auth/login", json={"username": USERNAME, "password": PASSWORD})
resp.raise_for_status()
token = resp.json().get("token") or resp.json().get("accessToken") or resp.json().get("access_token")
if not token:
    # Try nested
    data = resp.json()
    print("Login response keys:", list(data.keys()))
    token = data.get("token") or data.get("jwt") or data.get("bearerToken")
    if not token:
        for v in data.values():
            if isinstance(v, str) and len(v) > 20:
                token = v
                break

print(f"Token obtained: {token[:30]}..." if token else "ERROR: No token found")

headers = {"Authorization": f"Bearer {token}"}

# Get dances
resp = requests.get(f"{API_BASE}/dances", headers=headers)
resp.raise_for_status()
dances = resp.json()
print(f"Current dance count: {len(dances)}")

# Get styles
resp = requests.get(f"{API_BASE}/styles", headers=headers)
resp.raise_for_status()
styles = resp.json()
print(f"Dance styles: {len(styles)}")
for s in styles:
    print(f"  [{s.get('id')}] {s.get('name')}")

# Get musical styles
resp = requests.get(f"{API_BASE}/musicalstyles", headers=headers)
resp.raise_for_status()
musical_styles = resp.json()
print(f"Musical styles: {len(musical_styles)}")
for s in musical_styles:
    print(f"  [{s.get('id')}] {s.get('name')}")

# Build existing names set
existing_names = set()
for d in dances:
    name = d.get("name", "")
    if name:
        existing_names.add(name.lower())

print(f"\nExisting dance names (lowercase set): {len(existing_names)} entries")

# Save baseline data
baseline = {
    "token": token,
    "dance_count": len(dances),
    "existing_names": list(existing_names),
    "styles": styles,
    "musical_styles": musical_styles
}
with open(r"C:\Users\valot\Documents\Git\Projects\Dance\baseline.json", "w") as f:
    json.dump(baseline, f, indent=2)

print("Baseline saved to baseline.json")
