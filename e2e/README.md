# End-to-end suite

Playwright smoke tests for DancePlatform. They drive a **deployed** app over real HTTP —
production by default — so they answer the question the unit tests can't: *is the thing the
Pi is actually serving working right now?*

40 tests, ~25 seconds.

---

## Running them

```bash
cd e2e
npm install
npm run install:browsers        # one time — downloads Chromium
cp .env.example .env            # then fill in E2E_USERNAME / E2E_PASSWORD
```

| Command | What it does |
|---|---|
| `npm test` | Everything, against `E2E_BASE_URL` (default: production) |
| `npm run test:smoke` | Just the `@smoke` subset — the fast post-deploy check |
| `npm run test:api` | API only, no browser. ~1s. Run this first when something breaks |
| `npm run test:local` | Builds nothing, but serves `dance-platform-ui/dist` and tests **that** |
| `npm run verify:testids` | Static check of the test-id contract (see below). Milliseconds |
| `npm run report` | Opens the HTML report from the last run |

### Before deploying (tests UI changes not yet on the Pi)

```bash
cd dance-platform-ui && npm run build -- --configuration production
cd ../e2e && npm run test:local
```

`test:local` serves the build on `localhost:4300` and proxies `/api` to the real API. The
proxy exists because the production bundle's API base
(`https://dance-api.takelord.com/api`) allows CORS only from `https://dance.takelord.com` —
a localhost-served bundle would have every response blocked by the browser. That's correct
API behaviour; making the test origin same-origin is the right fix, not loosening prod CORS.

### After deploying

```bash
cd e2e && npm run test:smoke
```

### Against a local dev pair

```bash
E2E_BASE_URL=http://localhost:4200 E2E_API_URL=http://localhost:5000/api npm test
```

---

## Running them periodically

`e2e-dance.bat` in the repo root runs the smoke subset against production and writes a
timestamped log to `e2e/runs/`. To schedule it (e.g. hourly):

```powershell
schtasks /create /tn "DancePlatform e2e smoke" /tr "C:\Users\valot\Documents\Git\Projects\Dance\e2e-dance.bat" /sc hourly
```

Delete it with `schtasks /delete /tn "DancePlatform e2e smoke"`.

CI also runs the suite on every push (`.github/workflows/ci.yml`), against a build served in
the runner — so a regression is caught before it ever reaches the Pi.

---

## ⚠️ These tests write to production

`E2E_API_URL` defaults to the real API, so the `authed` project acts on the real database
using the throwaway account in `.env`.

Every authed test is therefore **either read-only or restores what it changed** — the
favourite-toggle test flips a favourite and flips it back in a `finally` block.

**Do not add a test that creates a dance, video, or practice session without deleting it
again.** A scheduled run repeats forever; anything it leaves behind accumulates in the real
catalog. This is not hypothetical: an early version of `api.spec.ts` asserted that a
non-admin *couldn't* `POST /dances`, discovered that it can (deliberately — a non-admin needs
to create a dance to attach a personal video to), and left three junk dances in the
production catalog that had to be deleted by hand. That test now targets `PUT` on an id that
cannot exist, so a regression in authorization damages nothing on its way to failing.

---

## The test-id contract

The UI churns — declutter passes reshuffle markup regularly. Tests keyed on CSS classes or
visible text would break on every one of those and teach you to ignore them. So the suite
anchors on a small, deliberate set of `data-testid` attributes.

**These 19 attributes are a contract. Treat them like a public API.**

| Test id | Lives in | Anchors |
|---|---|---|
| `nav-browse`, `nav-my-dances`, `nav-sign-in` | `app.component.html` | Header nav links |
| `user-menu-button`, `sign-out` | `app.component.html` | Account menu |
| `login-username`, `login-password`, `login-submit`, `login-error` | `login.component.html` | Sign-in form |
| `search-input`, `results-count`, `sort-select`, `empty-state` | `dances.component.html` | Browse controls |
| `style-filter-pills` | `dances.component.html` | The Style filter row — `.style-filters` alone also matches the Level row |
| `dance-card`, `dance-card-link` | `dances.component.html` | Result cards — **on both the grid card and the list row** |
| `dance-title`, `favorite-button`, `progress-learned` | `dance-detail.component.html` | Detail page |

Everything else is selected by ARIA role or accessible name (`getByRole('button', { name:
'Next page' })`), which is stable *because* it's an accessibility contract — if it changes,
the change is worth knowing about.

### Rules when you change the UI

1. **Moving an element?** Move its `data-testid` with it.
2. **Deleting an element?** Delete the test that asserts on it, in the same commit.
3. **Replacing an element?** Put the same `data-testid` on the replacement.
4. **Never rename a test id to match new markup** — rename it only if the *concept* changed.
5. **Renaming a URL query param** (`q`, `style`, `sort`, `fav`, `page`)? Update `browse.spec.ts`
   and `authed.spec.ts`, which assert on them.
6. Run `npm run verify:testids` before you commit. It fails in under a second if the suite
   references an anchor the UI no longer has — instead of a browser run failing minutes
   later, or a scheduled run failing at 3am.

`verify:testids` also lists anchors that no test asserts on. That's a warning, not a
failure: either write the test or drop the attribute.

---

## Layout

```
e2e/
├─ playwright.config.ts     4 projects: api, anon (desktop), authed, mobile (Pixel 7)
├─ .env.example             copy to .env — .env is gitignored
├─ fixtures/
│  ├─ env.ts                loads .env; shell env always wins
│  └─ auth.ts               signs in over the API, plants the JWT in localStorage
├─ tests/
│  ├─ api.spec.ts           contract + health, browserless (~1s)
│  ├─ smoke.spec.ts         shell, routing, guards, SPA fallback — runs desktop AND mobile
│  ├─ browse.spec.ts        search, filters, sort, pagination, URL sync
│  ├─ dance-detail.spec.ts  detail page, video embed, prev/next
│  └─ authed.spec.ts        signed-in flows + the login form
└─ scripts/
   ├─ verify-testids.mjs    the contract guard
   ├─ serve-dist.mjs        static server + SPA fallback + /api proxy
   └─ run-against-build.mjs `npm run test:local` — starts the server, runs, tears down
```

---

## Conventions

- **Assert behaviour, never content.** `expect(cards.count()).toBeGreaterThan(0)`, not
  "Bachata is on page 1". The catalog is curated and reseeded; content assertions rot.
- **Poll after an action that triggers a re-query.** The browse grid keeps the previous
  results on screen (dimmed) while the next page loads, so reading straight after a click
  gets stale data. Use `expect.poll`.
- **Don't assert a full sort order.** Postgres's collation and JS `localeCompare` genuinely
  disagree on spaces and diacritics (`Airfreeze` / `Air Walk` / `À la seconde`). The sort test
  compares first letters only.
- **A `test.skip` must be justified and reachable.** Skips that fire on every run are worse
  than failures — they look green. If a test skips because data hasn't loaded yet, that's a
  bug in the test: wait for the data, then decide.
- **Wait for async-loaded lists before clicking into them.** Style pills arrive from
  `/api/styles` after first paint; clicking at first paint either hits a node that's about to
  be replaced by the re-render, or the wrong row entirely. Poll for the expected count first.
- **Scope locators tightly.** Shared class names recur across rows (`.style-filters` is used
  by both the Style and Level filters). Prefer a `data-testid` on the container over an
  `nth()` that silently points somewhere else once the page changes.
- **Nothing in `smoke.spec.ts` may assume a viewport** — it runs under both desktop and
  mobile. Below 720px the nav collapses behind the hamburger and the filter panel behind a
  "Filters" toggle; use the `revealNav` / `openFilters` helpers.
