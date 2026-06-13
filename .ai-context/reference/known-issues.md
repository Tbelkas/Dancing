# Reference — Known Issues & Gotchas

Distilled "what to watch out for." Long-form QA log lives in repo-root `BUG_REPORT.md`
(QA sweep 2026-06-13, Playwright against the live site). Keep this list current.

## Open / unresolved

### A. Public write endpoints are unauthenticated  ⚠️ (security gap)
`POST /api/dances`, `POST /api/videos`, `POST /api/styles` have **no auth attribute** —
anyone can create dances/videos/styles. Their `PUT`/`DELETE` siblings are `[RequireAdmin]`,
and `POST /musicalstyles` / `POST /instructors` *are* admin-gated. Almost certainly an
oversight. **Fix:** add `[RequireAdmin]` (or `[Authorize]`, per intent) to those three POSTs.
Until fixed, do not treat "dance exists" as implying an admin created it.

### B. Duplicate dances allowed (data quality) — was known-issues #5
API accepts duplicate dance names and auto-suffixes the slug (`reebok`, `reebok-2`…). Prod
had Reebok ×5, Butterfly ×2, etc.; cleaned up by hand on the Pi 2026-06-13 (backup first,
kept only copies that had videos). **Still suggested:** warn on name collision in the API or
admin create form. Don't assume dance names are unique.

### C. Cold-start API latency (observation, not a bug)
First request after idle intermittently takes 2–4 s (cold EF/connection). Loading states
cover it. A keep-warm ping or server tuning would help first impressions. Earlier-suspected
"infinite LOADING on dance detail" was just this latency.

### D. Slug doesn't reset on rename
Admin edit regenerates the slug from the name, but a rename that collides with nothing won't
free/reset an already-suffixed slug without a manual DB update or small API tweak. Cosmetic.

## Fixed (kept here as regression tripwires — don't reintroduce)

### 1 & 2. Practice timezone bugs ✅ FIXED — **the #1 trap in this app**
- Streak/"today" was computed in **UTC** (`new Date().toISOString().split('T')[0]`) → sessions
  logged after local midnight counted as the wrong day; streaks broke east of UTC.
- Session dates rendered a day early west of UTC (`new Date(dateStr)` parses as UTC midnight).
- **Rule going forward:** all day logic is **local**; default the form to local today; render
  `DateOnly` strings by parsing `dateStr + 'T00:00:00'`. See business-rules → Practice log.

### 3. Empty login submitted to API ✅ FIXED
Angular forms are `novalidate`, so `required` didn't block submit; empty login fired a POST
and showed a generic error. Login mode now has client-side empty-field validation (register
mode already did). **Lesson:** validate client-side before the network call; don't rely on
`required`.

### 4. Unknown dance slug → "LOADING" then silent redirect ✅ FIXED
`/dances/<bad-slug>` hung on LOADING then silently bounced to `/dances`. Now shows a
"Dance not found" state with a Browse link on API 404 (other errors keep the redirect).
Mirror this pattern (explicit not-found state) for any new detail page.

### 6. Third-party embed console noise — WON'T FIX
TikTok/YouTube player scripts spam the console (appContext, blocked CORS to `mon.tiktokv.com`,
permissions-policy/accelerometer, aborted `qoe` telemetry). All inside third-party iframes;
no user-visible impact. Don't chase these.

## What's verified working (per the 2026-06-13 sweep)
All 32 routes load; SPA deep links + global 404 work; no horizontal overflow at
1920/1280/768/375; no broken images; no first-party console errors; auth + guards
(`/profile`, `/my-dances`, `/practice`) hold before login and after sign-out; favorite/
learned/in-progress toggles, rating persistence, practice CRUD + counters, search + all
filter pills, profile edit + visibility (public visible to anon, private hidden), video
accordion + embed.
