# DancePlatform — Context-Locked AI Workspace

This folder is a **context bundle**: a curated, layered description of this system so an
AI assistant (or a new human) can work inside it without re-deriving everything each time.

It is generated from the real code. When the code changes, update the relevant layer
(see "Maintenance" below). Treat these files as the source of truth for *intent and
conventions*; treat the code as the source of truth for *current behaviour*. If they
disagree, the code wins and the doc is stale — fix the doc.

---

## The prepend prompt

Paste this at the top of any AI session that touches this codebase:

> You are working inside the **DancePlatform** system. Do not assume anything outside the
> context I give you. Before writing code, load **core-context.md** (Layer 1). If the task
> touches a specific feature, also load the matching file in **module-context/** (Layer 2).
> I will give you the current task as **session-context** (Layer 3).
> Follow the conventions and obey every rule in the "DO NOT" section of core-context.md.
> If something you need is not in the provided context, ask — do not invent endpoints,
> table columns, fields, or libraries.

---

## The three layers

| Layer | File(s) | Changes… | Load when |
|-------|---------|----------|-----------|
| **1 — core** (never/rarely changes) | `core-context.md` + `reference/*` | on architecture / stack / schema changes | **always** |
| **2 — module** (feature-specific) | `module-context/<feature>.md` | when that feature changes | when the task touches that feature |
| **3 — session** (current task) | `session-context.template.md` → your task | every task | every task |

**Layer 1 — core-context** is the stable spine: stack, architecture, folder structure,
conventions, and the **DO NOT** rules. Its companion `reference/` files hold the bulky
facts that core points to:
- `reference/db-schema.md` — every table, column, key, relationship
- `reference/api-contracts.md` — every endpoint, its auth, request/response shape
- `reference/business-rules.md` — the rules the code enforces (and why)
- `reference/known-issues.md` — bugs (fixed + open), gotchas, "won't fix"

**Layer 2 — module-context** is one file per feature area. Each is self-contained enough
to drop into a session alongside core-context:
- `module-context/dances-catalog.md`
- `module-context/auth-and-profile.md`
- `module-context/practice-log.md`
- `module-context/videos.md`
- `module-context/styles-instructors.md`
- `module-context/import-admin.md`

**Layer 3 — session-context** is the disposable task brief. Copy
`session-context.template.md`, fill it in, hand it to the AI with the two layers above.

---

## How to use it (typical flow)

1. New task → copy `session-context.template.md`, write what you want.
2. Open the AI session with **the prepend prompt** above.
3. Attach / paste: `core-context.md`, the relevant `module-context/*.md`, your session file.
4. Work. The AI now has long-term memory of the system without you re-explaining it.

---

## Maintenance

Keep this bundle honest — a wrong context file is worse than none.

- **Schema change** (model/migration) → update `reference/db-schema.md`.
- **New/changed endpoint** → update `reference/api-contracts.md` and the module file.
- **New rule / behaviour** → `reference/business-rules.md` + module file.
- **New bug or fix** → `reference/known-issues.md` (the repo's `BUG_REPORT.md` is the
  long-form log; this is the distilled "what to watch out for").
- **New feature area** → add a `module-context/<feature>.md`, link it here.

Last regenerated: 2026-06-13 (Opus 4.8, from code in `DancePlatform.API/` and `dance-platform-ui/`).
