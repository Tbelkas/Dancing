# DancePlatform — working rules

ASP.NET Core 8 API + Angular 17 SPA + PostgreSQL, deployed to a Raspberry Pi.
Architecture, schema, and conventions live in [`.ai-context/`](.ai-context/00-README.md) —
read `core-context.md` first, then the relevant `module-context/` file.

---

## Keeping the e2e suite honest

`e2e/` holds a Playwright suite that runs against the **deployed** app. It's the only thing
that catches "the Pi is serving a broken bundle". It's also the first thing to rot if UI
changes land without it, so:

### After changing anything in `dance-platform-ui/src`

1. Run `cd e2e && npm run verify:testids`. Sub-second, no browser. It fails if the suite
   references a `data-testid` the UI no longer has.
2. If you changed markup covered by a test, update the test **in the same commit**. Never
   leave the suite red for someone else to find.
3. Before deploying: `cd dance-platform-ui && npm run build -- --configuration production`,
   then `cd ../e2e && npm run test:local`. This tests the new build; running against
   production would test the *old* one.
4. After deploying: `cd e2e && npm run test:smoke`.

### The `data-testid` contract

25 attributes across six templates are load-bearing — the suite selects on them precisely
so it survives the declutter passes that reshuffle classes and text. They are listed in
[`e2e/README.md`](e2e/README.md#the-test-id-contract).

- Moving an element? Move its `data-testid` with it.
- Replacing an element? Put the same `data-testid` on the replacement.
- Deleting an element? Delete the test that asserts on it, same commit.
- Don't rename a test id to match new markup — rename only if the *concept* changed.

### After changing an API contract

Renaming a DTO field, route, or query param breaks the suite silently — it asserts on
`items[].styleSlug`, on the sort values (`recommended`/`tutorials`/`name`/`rating`/
`popular`/`newest`), and on the browse query params (`q`, `style`, `sort`, `fav`, `page`).
Update `e2e/tests/api.spec.ts` and `e2e/tests/browse.spec.ts` alongside the change.

### Writing new e2e tests

Conventions (and the reasoning behind each) are in
[`e2e/README.md`](e2e/README.md#conventions). The two that bite hardest:

- **The authed tests write to the production database.** Every one must be read-only or
  restore what it changed. Never add a test that creates a dance, video, or practice session
  without deleting it again — scheduled runs repeat forever.
- **A `test.skip` that fires on every run is worse than a failure**, because it looks green.
  If a test skips because data hasn't loaded, wait for the data, then decide.

---

## Secrets

`appsettings.*.json` (except the tracked base and `.example`) and `e2e/.env` are gitignored
and hold real credentials. Scripts must read the connection string from `appsettings`, the
way `scripts/find_chip_candidates.py` and `scripts/enrich_views.py` do — never hardcode it.

> `scripts/apply_sections.py` and `scripts/backfill_durations.py` still hardcode the
> production DB password, and the repo is public. Rotate the password and fix both before
> treating this rule as satisfied.

---

## Deploying

`deploy-dance.bat` commits, pushes, and runs the update script on the Pi. Per the
deploy-test-fix loop: deploy, verify live, fix — don't call a change done until it's been
seen working on `dance.takelord.com`.
