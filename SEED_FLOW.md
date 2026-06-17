# Dance Platform — Seeding Orchestration Flow

You are being asked to autonomously seed the DancePlatform database with dance moves,
classification metadata, and linked tutorial videos. Follow each phase in order.
Do not ask for confirmation between steps unless you hit an unrecoverable error.

---

## Environment

| Thing | Value |
|---|---|
| API base | `https://dance-api.takelord.com/api` |
| Frontend | `https://dance.takelord.com` |
| Pi (server) | `192.168.0.197` — SSH as `pi@pi` |
| Ollama host | `http://localhost:11434` (Windows PC on LAN, accessible from Pi at `http://192.168.0.174:11434`) |
| Ollama model | `llama3.1:8b` |
| Seeder script | `seed_dances.py` in the project root |
| Deploy script | `deploy-dance.bat` in the project root |

Admin credentials (for the API):
- Ask the user for username/password at the start if not already known.
- Alternatively they may be in a local `.env` file or the user will paste them.

---

## Phase 0 — Discover existing content

Before seeding anything, learn what already exists so you don't create duplicates.

```
GET https://dance-api.takelord.com/api/dances
GET https://dance-api.takelord.com/api/styles
GET https://dance-api.takelord.com/api/musicalstyles
```

Parse the responses. Build:
- `existing_dance_names` — set of lowercase dance names already in the DB
- `style_list` — list of `{id, name}` for dance styles
- `music_list` — list of `{id, name}` for musical styles

Print a summary: how many dances exist, what styles are defined.
If no styles exist yet, stop and tell the user — Ollama classification will be useless
without styles to map to.

---

## Phase 1 — Discover dance content from YouTube

Use `yt-dlp` to find YouTube videos that contain timestamped dance move lists.
These are typically "dance moves compilation" or "how to dance X" videos whose
descriptions contain lines like `Running Man [00:29]`.

### 1a — Build a search plan

For each style in `style_list`, generate 2–3 search queries:

```
"{style_name} dance moves tutorial timestamps"
"{style_name} dance compilation how to"
"learn {style_name} dance moves beginner"
```

Also run these general queries regardless of styles:
```
"hip hop dance moves tutorial timestamps"
"street dance beginner moves timestamps"
"ballroom dance steps for beginners timestamps"
"latin dance moves tutorial timestamps"
```

### 1b — Search and extract video metadata

For each query, run:
```bash
yt-dlp --dump-json --no-download --no-warnings --flat-playlist "ytsearch5:{query}"
```

Collect unique video IDs. For each unique video, fetch the full description:
```bash
yt-dlp --dump-json --no-download --no-warnings "https://youtube.com/watch?v={video_id}"
```

Parse the description for timestamp lines using this pattern:
```
^\s*(?:\d+[\.\)]|\*|-)?\s*(.+?)\s*\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*$
```

Also check the `chapters` field in the yt-dlp JSON — YouTube chapters are structured
as `[{title, start_time, end_time}]` and are another source of dance names + timestamps.

### 1c — Score and select videos

A video is worth seeding if it has:
- At least 5 timestamp/chapter entries
- None of the extracted names already exist in `existing_dance_names`
- Video duration > 3 minutes (likely a real tutorial, not a clip)

Rank by: `(new_names_count / total_names_count) * log(view_count + 1)`
Pick the top 10 videos. Print the list with their new-name counts before proceeding.

---

## Phase 2 — Classify and seed

For each selected video, create a temporary input file and run the seeder:

```bash
python seed_dances.py <tempfile>
```

The tempfile format:
```
https://youtube.com/watch?v={video_id}
{Dance Name} [{MM:SS}]
{Dance Name} [{MM:SS}]
...
```

The seeder will:
1. Call Ollama (via `localhost:11434`) for each dance name to get style IDs, musical style IDs, difficulty, and a description
2. Create the dance via `POST /api/dances`
3. Link the YouTube video segment via `POST /api/videos`

Watch stdout for any `FAILED:` lines and log them separately.

### Fallback — names only (no video)

If a batch has no timestamped video but you have a good list of dance names
(e.g. extracted from a web page, a Wikipedia list, or Ollama's own knowledge),
write them one-per-line to a file and run the seeder in names-only mode.
The seeder will auto-search YouTube and TikTok for each name via yt-dlp.

---

## Phase 3 — Gap-fill with Ollama knowledge

After the YouTube discovery pass, ask Ollama directly for dances you may have missed:

Send this prompt to `http://localhost:11434/api/generate` (model: `llama3.1:8b`):

```
List 30 well-known {style_name} dance moves or steps that a beginner should learn.
Return ONLY a JSON array of strings, no explanation.
Example: ["Running Man", "Cabbage Patch", "Roger Rabbit"]
```

Do this for each style in `style_list`. Filter out names already in `existing_dance_names`.
Write the remaining names to a file and run the seeder in names-only mode so it
auto-searches for videos.

---

## Phase 4 — Verify

After seeding, re-fetch:
```
GET https://dance-api.takelord.com/api/dances
```

Print:
- Total dances now in DB (vs. count before seeding)
- Breakdown by style (how many dances per style)
- How many have at least one video linked
- How many were given a difficulty level (not "None")
- Any dance names that ended up with no style assigned (may need manual review)

If fewer than 80% of newly created dances have a style assigned, it likely means
the Ollama classification is not matching your style names. Print the style names
Ollama suggested vs. the names in the DB and ask the user whether to rename styles
or re-run classification.

---

## Phase 5 — Deploy (only if API code changed)

If you made any code changes to `DancePlatform.API/` during this session, run:
```
deploy-dance.bat
```
from the project root. Otherwise skip — the seeder only calls the API and no deploy is needed.

---

## Error handling

| Error | Action |
|---|---|
| `yt-dlp` not found | Run `pip install yt-dlp` then retry |
| Ollama unreachable (`localhost:11434`) | Check that Ollama is running on the Windows PC; the seeder falls back gracefully (dances created without classification) |
| API 401 Unauthorized | Re-login and get a fresh token |
| API 409 / duplicate slug | The dance already exists — skip it |
| API 500 | Print the response body, skip the dance, continue |
| yt-dlp returns 0 results | Skip video search for that dance, create without video |

---

## Style guidance for Ollama prompts

When classifying, the model performs best when the available style names are
descriptive. If a style name like "Street" is in the DB but Ollama keeps returning
"Hip-Hop" or "Urban", the mismatch means those dances get no style. In that case,
consider creating additional style entries via:

```
POST https://dance-api.takelord.com/api/styles
Authorization: Bearer {token}
{"name": "Hip-Hop", "description": ""}
```

Then re-run classification for untagged dances.

---

## Success criteria

The run is complete when:
- At least 50 new dances have been created (or all discovered names exhausted)
- At least 70% have a dance style assigned
- At least 60% have a linked video
- The verification summary has been printed

Print a final one-paragraph summary of what was seeded and any notable issues.
