# End-to-end suite

Playwright smoke tests for DancePlatform. They drive a **deployed** app over real HTTP —
production by default — so they answer the question the unit tests can't: *is the thing the
Pi is actually serving working right now?*

48 tests, ~45 seconds.

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

Nothing in the suite creates rows any more. The `personal skill trees` block did, and was
removed on 2026-08-12 along with the feature's UI (`PERSONAL_ROADMAPS_ENABLED` in
`dance-platform-ui/src/app/core/constants/feature-flags.ts`) — restore it from git history when
the flag goes back on. It followed four rules worth copying for anything else that has to write:

- the tree's name carries `Date.now()`, so two overlapping runs can't fight over one slug;
- cleanup goes over the **API**, in a `finally`, rather than through the UI — a test that only
  tidies up when the UI still works would leave its rows behind on exactly the run that found
  a bug;
- **cleanup identifies its rows by diffing, not by the id the test read back.** `ownedTreeIds()`
  snapshots what the account owns before the test; the `finally` deletes anything that wasn't in
  it. Keying off the slug looks equivalent and isn't: a test can only learn the slug from the URL
  *after* the save, so a save that succeeded and then timed out waiting for the navigation left
  `slug` empty and the `finally` did nothing. That window is how the prod account quietly
  collected 13 orphaned trees. Verified by injecting a throw into exactly that spot — old
  cleanup leaked two trees over the run and its retry, the diff leaks none;
- the cleanup uses a 30s timeout and retries, **re-listing before each pass** so the previous
  pass's deletes are confirmed rather than assumed, and it **throws if it gives up**. It also
  holds its own API token rather than reading the page's, so it works when the page is on
  `about:blank`, wedged, or closed. The Pi has exceeded the default 10s under load, and a cleanup
  that silently times out is worse than none because the run still looks green.

⚠️ **The builder registers a `beforeunload` handler while it has unsaved edits.** Playwright
auto-dismisses that dialog, which *cancels* the navigation — so a `page.goto()` away from a
dirty builder hangs until the 20s timeout instead of failing usefully. Save first, or drive the
navigation through a link click and handle the dialog with `page.once('dialog', …)`, which is
what the unsaved-changes test does.

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

**These 86 attributes are a contract. Treat them like a public API.**

The personal-skill-tree rows below (`roadmap-new` … `builder-step-clip`, and
`profile-shared-roadmaps`) are **dormant**: the markup still carries them, but it is gated on
`PERSONAL_ROADMAPS_ENABLED` and nothing selects on them while the flag is off. Keep them where
they are — the tests come back with the feature.

| Test id | Lives in | Anchors |
|---|---|---|
| `nav-browse`, `nav-my-dances`, `nav-sign-in`, `nav-roadmaps` | `app.component.html` | Header nav links |
| `user-menu-button`, `sign-out` | `app.component.html` | Account menu |
| `login-username`, `login-password`, `login-submit`, `login-error` | `login.component.html` | Sign-in form |
| `login-google`, `login-facebook` | `login.component.html` | Social sign-in buttons. Rendered from `GET /auth/external/providers`, so a provider with no server-side credentials produces **no button at all** — assert on them conditionally, never unconditionally |
| `finish-signup-username`, `finish-signup-submit`, `finish-signup-error` | `finish-signup.component.html` | The username step a first-time social sign-in lands on. Reachable only with a valid ticket in the URL fragment; without one the page redirects to `/login` |
| `auth-callback` | `auth-callback.component.ts` | The post-provider landing page. Consumes the token from the fragment and redirects — it is never a resting state |
| `connected-accounts` | `profile.component.html` | The Connected accounts card. **Absent** until `GET /auth/external/links` resolves |
| `search-input`, `results-count`, `sort-select`, `empty-state` | `dances.component.html` | Browse controls |
| `style-filter-pills` | `dances.component.html` | The Style filter row — `.style-filters` alone also matches the Level row |
| `dance-card`, `dance-card-link` | `dances.component.html` | Result cards — **on both the grid card and the list row** |
| `dance-title`, `favorite-button`, `progress-learned` | `dance-detail.component.html` | Detail page |
| `roadmap-card`, `roadmap-card-link` | `roadmaps.component.html` | Roadmap index cards |
| `roadmap-new`, `my-roadmaps` | `roadmaps.component.html` | The "Build a skill tree" button and the grid of the user's own trees. **Both signed-in only** |
| `roadmap-owned-badge`, `roadmap-edit`, `roadmap-delete`, `roadmap-delete-confirm`, `roadmap-copy` | `roadmap-detail.component.html` | Owner controls. `roadmap-edit`/`roadmap-delete` appear only on a tree the viewer owns; `roadmap-copy` only on one they don't. Their **absence** is the assertion that a curated path can't be edited in place |
| `roadmap-share`, `roadmap-shared-badge`, `roadmap-copy-link`, `roadmap-shared-by` | `roadmap-detail.component.html` | Sharing. The first three are owner-only; `roadmap-shared-by` is the opposite — it renders for everyone *except* the owner, so asserting it needs a fresh signed-out context, not the authed fixture |
| `profile-shared-roadmaps` | `user-profile.component.html` | A user's shared trees on their public profile — the only place one is listed, since they never join the roadmap index. **Absent** when they've shared none |
| `builder-title`, `builder-name`, `builder-style`, `builder-save`, `builder-error`, `builder-dirty` | `roadmap-builder.component.html` | The builder's heading, the two required fields, Save, the validation message, and the unsaved-changes marker |
| `builder-add-branch`, `builder-add-step`, `builder-step`, `builder-step-delete`, `builder-step-link`, `builder-step-move`, `builder-requires-add` | `roadmap-builder.component.html` | Structure editing: add a branch/move, each move row, its delete, the catalog-link button, the linked move chip, and the "comes after" dropdown. `builder-add-step` is **per branch** — use `.last()`, not the bare locator |
| `builder-step-pin`, `builder-clip-picker`, `builder-step-clip` | `roadmap-builder.component.html` | Pinning a step to one section of a video: the button, the picker, and the resulting clip chip. All three need the step to have a linked move first |
| `roadmap-title`, `roadmap-progress`, `roadmap-step`, `roadmap-step-videos`, `roadmap-step-learned` | `roadmap-detail.component.html` | A path: its title, the progress bar, each step row (list view), a step's video list, and the Learned chip (signed-in only) |
| `roadmap-view-tree`, `roadmap-view-list`, `roadmap-detail-panel` | `roadmap-detail.component.html` | The view toggle and the tree's detail panel. **All three are signed-in only** — signed out the page renders the bare tree, so a test that needs the list view or a step's videos must use the `authed` project |
| `roadmap-tree-hint` | `roadmap-detail.component.html` | The signed-out line under the tree. Its presence is how the anon suite proves the teaser state is still the teaser state |
| `roadmap-tree`, `tree-node` | `roadmap-tree.component.html` | The skill-tree SVG and each node `<g>` in it. The component is reused as the builder's live preview, so these also match on `/roadmaps/new` and `/roadmaps/:slug/edit` |
| `signin-dialog`, `signin-username`, `signin-password`, `signin-submit`, `signin-error` | `sign-in-dialog.component.html` | The in-place sign-in modal a signed-out visitor gets when they touch a roadmap node — distinct ids from `login-*`, which anchor the `/login` page |
| `camera-toggle`, `stage-fullscreen` | `video-player` + `local-video-player` templates | The Camera tool button and the stage-fullscreen button — **on both players** |
| `camera-pane`, `camera-close`, `camera-error`, `camera-notice`, `camera-replay`, `camera-exit-fullscreen` | `camera-pane.component.html` | The camera pane, its close button, its failure panel, its fallback notice, the delayed-replay `<video>`, and the fullscreen exit it carries |

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
│  ├─ camera.spec.ts        the camera pane — see "Testing the camera" below
│  └─ authed.spec.ts        signed-in flows + the login form
└─ scripts/
   ├─ verify-testids.mjs    the contract guard
   ├─ serve-dist.mjs        static server + SPA fallback + /api proxy
   ├─ run-against-build.mjs `npm run test:local` — starts the server, runs, tears down
   └─ flicker/              measuring tools, not tests — see "Checking for flicker"
```

---

## Checking for flicker

`scripts/flicker/` holds six probes. They are **measuring tools, not tests** — nothing here
runs in the suite or fails a build. Reach for them when someone says the app "flashes" or
"blinks", or after touching a loading state.

They all read `e2e/.env` and target the deployed app, same as the suite. They are read-only:
they type, sort, paginate, hover and navigate, and never write. (`probe-lib.mjs` is the shared
rig — login, a per-frame DOM recorder, and an abort on `POST /videos/:id/view` so probing a
dance page can't touch prod view counts.)

| Probe | Answers |
|---|---|
| `npm run flicker:skeletons` | How many ms is each page's skeleton actually on screen? |
| `npm run flicker:empty-state` | Does a page claim it has nothing while a request is still in flight? |
| `npm run flicker:fidelity` | While a skeleton is up, is it the right *shape* for what replaces it? |
| `node scripts/flicker/redirect-flash.mjs` | Does a redirect paint the wrong page on the way past? |
| `node scripts/flicker/record-pages.mjs` | Video + CLS + a load/idle/scroll phase timeline per page |
| `node scripts/flicker/dom-oscillation.mjs` | Does anything go A → B → A while the page is driven? |

The last two of the first three are the pair that catches what `flicker:skeletons` can't: a
skeleton can be on screen for a perfectly healthy 400ms and still be covering the wrong
request, or reserving two cards where three land. Both slow one endpoint deliberately, because
on a warm API most of these states never render at all.

### Reading the skeleton timings

`flicker:skeletons` is the one to run first, and the regression check for
[`delayedLoading()`](../dance-platform-ui/src/app/core/utils/delayed-loading.ts).

- **`none`** — healthy. The response beat the 220ms delay, so no skeleton ever rendered.
- **a few hundred ms** — healthy. A genuinely slow response got a skeleton that stayed put
  long enough to read.
- **anything under ~150ms** — the bug. Too short to register as loading, long enough to see a
  grey block and half a shimmer sweep. Every page did this before delayedLoading existed:
  17–115ms across the board, because the API answers in 30–80ms.

A skeleton bound straight to a `loading` signal will always land in that third bucket on a
fast connection. That is why the templates carry a third branch — skeleton, then a silent
window, then content — instead of the usual two.

### The other three

`record-pages.mjs` and `dom-oscillation.mjs` write artifacts for a second pass:

```bash
OUT_DIR=/tmp/flicker node scripts/flicker/record-pages.mjs
python scripts/flicker/analyze-frames.py /tmp/flicker        # needs ffmpeg + Pillow

OUT_FILE=/tmp/dom.json node scripts/flicker/dom-oscillation.mjs
python scripts/flicker/osc.py /tmp/dom.json
```

`analyze-frames.py` reports per-phase pixel change. Expect zero in the idle window on every
page **except the landing page**, whose style marquee is a deliberate animation.

Run `record-pages.mjs` when the Pi is otherwise idle. Eighteen cold contexts back to back can
saturate its SD card, and a page that then sits blank for twenty seconds is that, not a UI bug.

---

## Testing the camera

`camera.spec.ts` needs a webcam, and there isn't one on CI. It sets its own launch options
via `test.use`, and both halves matter:

- `launchOptions.args: ['--use-fake-device-for-media-stream']` — a synthetic capture device,
  so no hardware and no human clicking "Allow".
- `channel: 'chromium'` — **required.** Playwright's default headless shell has no media
  stack at all: `getUserMedia` there rejects with `NotSupportedError` whatever permissions
  you grant. The `chromium` channel runs the full browser in new headless mode, which does
  capture. `npx playwright install chromium` already fetches it, so CI needs no extra step.

The `camera denied` block drops `permissions` to assert the failure path — a blocked camera
has to keep the pane up and explain itself, not silently vanish.

Nothing here touches the API or the database: the camera is browser-local, and the only state
it leaves behind is `dp_camera_*` in a context that Playwright throws away.

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
