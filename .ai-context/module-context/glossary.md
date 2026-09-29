# Module — Glossary (per-style move reference, with learned marks)

> Load alongside core-context.md when the task touches `/glossary`, the authored content in
> `Data/Glossary/`, or glossary learned marks.

## What it is

A **reference** for each style's vocabulary: every move (and the handful of concepts a learner
needs, like "on the one"), with a summary, an in-depth description, step-by-step instructions,
tips, aliases, difficulty, related terms, and — where the catalog has a trustworthy clip — a link
to the move's videos. Users tick moves off as learned.

Browse answers "what videos exist?", a roadmap answers "what order do I learn things in?", the
glossary answers "what *is* this move and how do I do it?".

## Content

- One file per style: `DancePlatform.API/Data/Glossary/<style>.json` (`styleName` must match
  `Styles.Name`). `//` comments are allowed. Shape: `categories[] → terms[]`, each term
  `slug, name, aliases[], summary, description, steps[], tips[], related[], difficulty,
  learnable (default true), danceSlug?`.
- `GlossarySeeder` runs every boot (after `RoadmapSeeder`) and **upserts by (style, slug)**.
  A term removed from the file is deleted along with users' marks on it (logged as a warning).
  **Never rename a slug** — it's the key learned marks hang off. e2e asserts `jack` exists.
- `danceSlug` only borrows the dance for its videos. Link only when the video really teaches
  the move — the House catalog has several dances whose seeded descriptions are wrong. The
  term's own text is the reference, never the dance's description. Unknown slugs log a
  warning and leave the term unlinked; links re-resolve every boot.
- Categories render in the order of their first term; terms in file order.

Live (2026-09-29): **House** (66 terms), **Hip-hop** (83), **Breakdance** (56). Next styles: reuse
the roadmap's style list. Every learnable term should have a clip: when the catalog lacks one, add
the move to `scripts/style_catalog.py` (prefix the style name if the bare name exists elsewhere -
the seeder skips known names) and run `seed_style_moves.py` search -> curate `_proto/style_seed.json`
-> insert -> `verify_intake.py --only-unscored apply` -> `promote_confirmed.py apply` -> promote apply,
then set `danceSlug`. Silent/wordless tutorials (BANRI Jackin) never verify; approve them by hand
with a `ReviewNote` after checking the title.

## Backend
- `Models/GlossaryTerm.cs`, `Models/UserLearnedGlossaryTerm.cs`; migration `AddGlossary`.
- `IGlossaryService` / `GlossaryService`, `Controllers/GlossaryController.cs`, `DTOs/Glossary/`.
- Style is addressed by `SlugGenerator.Slugify(Style.Name)`, resolved in memory.

## Frontend
- `pages/glossary/` (index, `/glossary`) and `pages/glossary-detail/` (`/glossary/:style`).
- Search (name, aliases, summary), category chips, "Hide learned", expand/collapse all.
- `#slug` fragment opens and scrolls to a term; "Related" chips do the same in-page, clearing
  any filter that would hide the target.
- Learned toggle is optimistic (reverts + toast on error); signed out it opens
  `SignInDialogComponent`, and signing in reloads the glossary to pick up existing marks.
- Header nav: `nav-glossary`, after Roadmaps.

## Not built
- Glossary marks and `UserLearnedDances` are independent — ticking "The jack" does not mark the
  `house-jack` dance learned, or vice versa.
