# Reference — Known Issues & Gotchas

Distilled "what to watch out for." Long-form QA log lives in repo-root `BUG_REPORT.md`
(QA sweep 2026-06-13, Playwright against the live site). Keep this list current.

## Open / unresolved

### A. ~~Public write endpoints are unauthenticated~~ ✅ RESOLVED (2026-06-28)
Historically `POST /dances|/videos|/styles` were a concern. Actual state: `POST /dances` and
`POST /videos` were already `[Authorize]`; `POST /styles` genuinely had **no** attribute (anon
could create styles) — now fixed to `[Authorize]`. These three are intentionally `[Authorize]`
(any signed-in user), **not** `[RequireAdmin]`, because the **My Dances** page is a self-service
add flow. Don't "promote" them to admin-only without reworking that flow. (PUT/DELETE siblings
and `POST /musicalstyles` / `POST /instructors` remain `[RequireAdmin]`.)

Since 2026-09-03 that open door has a gate behind it: a dance created by a non-admin is
`ReviewState = "pending"` and `OwnerUserId = <them>`. Its author sees it everywhere they already
would; browse, search, `names`, recommendations, neighbours and the `grandTotal` count skip it
until an admin approves it at `/admin/review`. This is **not** a global query filter (Video's
quarantine is) — see the comment on `Dance.ReviewState` for why. Any *new* dance listing must go
through `DanceService.Visible(...)`, or it will leak unreviewed rows onto the public site.

### B. ~~Duplicate dances allowed~~ ✅ RESOLVED (2026-09-03)
API accepted duplicate dance names and auto-suffixed the slug (`reebok`, `reebok-2`…). Prod had
Reebok ×5, Butterfly ×2, etc.; cleaned up by hand on the Pi 2026-06-13. `POST /dances` now
refuses a name that already exists **in one of the requested styles** and returns 409 with the
existing dance in the body, so the caller can select it instead. Admins are exempt — a
deliberate duplicate is curation. Same-name-in-a-different-style is still legal (that's what
per-style slugs are for), so **don't assume dance names are globally unique.**

### C. ~~Cold-start API latency~~ ✅ ADDRESSED (2026-09-03)
First request after idle intermittently took 2–4 s (cold EF/connection). `KeepWarmService`
(a hosted background service) now runs the real browse query every 4 minutes, so the pool has a
live connection and the compiled query stays compiled. In-process on purpose — a cron job or
systemd timer on the Pi is a thing to remember on a rebuild and a thing that can stop silently.
Earlier-suspected "infinite LOADING on dance detail" was just this latency.

### D. Slug doesn't reset on rename
Admin edit regenerates the slug from the name, but a rename that collides with nothing won't
free/reset an already-suffixed slug without a manual DB update or small API tweak. Cosmetic.

### E. Nothing watches the Pi
`GET /api/health` exists now (200 + `{database:true}`, or 503 when Postgres is unreachable) but
**nothing calls it on a schedule**. There is no alerting: if the Pi goes down, the first anyone
knows is a person reporting it. The e2e smoke run (`e2e-dance.bat`, schedulable hourly) is the
closest thing to a monitor.

## Rules the whole auth surface now depends on

- **Tokens carry `iat`, and `TokenService` stamps it explicitly.** The `JwtSecurityToken`
  constructor does *not* add one. `UserTokenGuard` compares it against `User.TokensValidFrom` to
  retire tokens issued before a password change/reset — drop the claim and revocation silently
  stops working (or, worse, retires everybody).
- **The cutoff is cached for 60s** (`UserTokenGuard`), so anything that moves `TokensValidFrom`
  must also call `UserTokenGuard.Forget(cache, userId)` or the change takes up to a minute.
- **`/auth/forgot-password` must answer identically for a known and an unknown address** (202,
  same body). Any difference — status, wording, timing shape — turns it into an account oracle.
- **Rate limiting partitions on the caller's address, which only works because
  `UseForwardedHeaders` runs first.** Apache proxies from localhost; remove it and every visitor
  shares one bucket, so the first busy minute locks out the whole site.

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
