# Bug Report — dance.takelord.com

QA sweep performed 2026-06-13 with Playwright (Chromium 148) against the live site.
Coverage: 32 URLs (all routes + 22 dance detail pages + error/guard cases), 4 viewport
widths (1920 / 1280 / 768 / 375), console + network monitoring, broken-image and
horizontal-overflow checks, and end-to-end flows: register (valid + 3 invalid cases),
login (valid, wrong password, empty), favorite / learned / in-progress toggles,
5-star rating (persisted across reload), practice-session logging (empty + valid),
search + style/music/level/status filters, profile edit + visibility toggle,
public profile (authed + anonymous), video accordion + embed, sign out + guard re-check.
Test account created: `qa_bot_933321` (left in place; contains 1 favorite, 1 learned,
1 rating, 1 practice session — safe to delete).

---

## Bugs

### 1. Practice page computes "today" in UTC, not local time ✅ FIXED
- **Severity:** Medium
- **Page:** https://dance.takelord.com/practice
- **Steps to reproduce:** In a timezone ahead of UTC (e.g. UTC+3), open Practice
  between local midnight and UTC midnight, click "Log Session".
- **What happened:** Date field pre-filled with **2026-06-12** while local date was
  2026-06-13. The streak computation compares against the UTC "today"/"yesterday",
  so a session logged "today" (local) can count as yesterday and a streak can appear
  broken (or alive) at the wrong time of day.
- **What should happen:** Date defaults to the user's local date; streak rolls over
  at local midnight.
- **Cause:** `new Date().toISOString().split('T')[0]` in `practice.component.ts`
  (form default, streak "today"/"yesterday").
- **Fix:** Local-date helper used for the form default and streak anchors.

### 2. Session dates render one day off for users west of UTC ✅ FIXED
- **Severity:** Medium
- **Page:** https://dance.takelord.com/practice
- **Steps to reproduce:** Log a session dated 2026-06-12, view the list from a
  UTC− timezone (e.g. US).
- **What happened:** `formatDate('2026-06-12')` parses the string as **UTC midnight**
  and then formats it in local time, so it renders as "Jun 11" anywhere west of UTC.
- **What should happen:** The stored calendar date renders as-is in every timezone.
- **Cause:** `new Date(dateStr)` in `practice.component.ts` `formatDate()`.
- **Fix:** Parse as local midnight (`dateStr + 'T00:00:00'`).

### 3. Empty login submit sends request to API and shows generic error ✅ FIXED
- **Severity:** Low
- **Page:** https://dance.takelord.com/login
- **Steps to reproduce:** Leave username and password blank, click "Sign In".
- **What happened:** A POST to `/api/auth/login` fires, the API returns 400, and the
  user sees the generic "An error occurred. Please try again." (Register mode has
  client-side checks; login mode has none — `required` attributes don't block
  submission because Angular forms are `novalidate`.)
- **What should happen:** Client-side message ("Please enter your username and
  password.") with no network call.
- **Fix:** Added empty-field validation for login mode in `login.component.ts`.

### 4. Unknown dance slug shows "LOADING..." then silently redirects ✅ FIXED
- **Severity:** Low
- **Page:** https://dance.takelord.com/dances/&lt;any-bad-slug&gt;
- **Steps to reproduce:** Visit `/dances/totally-bogus-slug`.
- **What happened:** Page shows "LOADING..." for ~3 s (API 404 round-trip), then
  silently lands on `/dances` with no explanation. Compare: a bad username at
  `/users/xyz` correctly shows "Profile not available".
- **What should happen:** A clear "dance not found" state (the global 404 page
  already exists for bad routes).
- **Fix:** `dance-detail.component.ts` now shows a "Dance not found" message with a
  Browse link on API 404 (other errors keep the old redirect).

### 5. Duplicate dances in production data ✅ FIXED (data cleanup 2026-06-13)
- **Severity:** Low (data quality)
- **Page:** https://dance.takelord.com/dances
- **Details:** "Reebok" existed 5× (`reebok` … `reebok-5`), "Butterfly" 2×,
  "Waacking vid choreo" 2× — identical names with auto-suffixed slugs. The admin
  create form already disables its submit button while saving, so these look
  manually created; the API accepts duplicate names silently and auto-suffixes
  the slug.
- **Fix:** Kept only the copies that have videos — `butterfly-2` (id 14) and
  `reebok-5` (id 21). Deleted ids 13, 15–20 (including both "Waacking vid choreo"
  entries, which had no videos) directly in the `dancing` Postgres DB on the Pi.
  Pre-checked that no videos, practice sessions, favorites, learned/in-progress
  marks, or ratings referenced the deleted rows (only their style-tag join rows,
  which cascade). Backup taken first: `/tmp/dances-backup-20260613.sql` on the Pi
  and `C:\Temp\dance-qa\dances-backup-20260613.sql` locally.
- **Note:** The surviving entries keep their suffixed slugs (`/dances/butterfly-2`,
  `/dances/reebok-5`); the base slugs are free again if you want to rename them
  (admin edit regenerates the slug from the name, but that would change nothing
  here since the names collide with… nothing anymore — a rename to the same name
  won't reset the slug; it would need a manual DB update or a small API tweak).
- **Still suggested:** have the API or create form warn when a dance with the same
  name already exists.

### 6. TikTok embed floods the console — WON'T FIX (third-party)
- **Severity:** Low (cosmetic)
- **Page:** https://dance.takelord.com/dances/butterfly-2 (any TikTok embed)
- **Details:** TikTok's player script logs "Consume appContext before init" ×5, a
  blocked CORS call to `mon.tiktokv.com`, and permissions-policy violations
  (accelerometer). YouTube embeds similarly abort their `qoe` telemetry requests.
  All errors originate inside the third-party iframes/scripts; no user-visible impact
  was found (the embed plays).

---

## Observations (not bugs)

- **API latency:** First API response after idle intermittently takes 2–4 s
  (`/api/dances/salsa` measured at 3.4 s once, &lt;500 ms warm). Loading states cover
  it, but a keep-warm ping or server tuning would improve first impressions.
- The earlier-suspected "infinite LOADING on dance detail when logged in" was this
  latency, not a hang — content renders once the API responds.

## What passed

- All 32 URLs load (200, no blank screens); SPA deep links work; global 404 page works.
- No horizontal overflow at 1920/1280/768/375 on any page; no broken images.
- No first-party console errors anywhere.
- Auth: register validation (short username/password, missing name), wrong-password
  error, guards on `/profile` `/my-dances` `/practice` (before login and after
  sign-out), JWT login, sign out.
- Favorite/Learned/In-Progress toggles update counts and appear on Profile.
- Rating: POST persists, survives reload, aggregate updates (4.0 ×1).
- Practice log: validation, creation, streak/total counters, delete button present.
- Search (incl. "No dances found." empty state) and all filter pill groups.
- Profile edit (name/nickname/avatar/visibility); public profile respects
  Private (hidden) vs Public (visible to anonymous users).
- Video accordion expands and loads the player iframe.
