# Layer 3 — Session Context (current task)  [TEMPLATE]

> Copy this file per task (e.g. `session-context.active.md`), fill it in, and hand it to the
> AI together with **core-context.md** and the relevant **module-context/*.md**.
> Delete/overwrite it when the task is done — this layer is disposable.

---

## Prepend (paste first)

> You are working inside the **DancePlatform** system. Do not assume anything outside the
> context I give you. You have: core-context.md (Layer 1) + the module file(s) below
> (Layer 2) + this task (Layer 3). Obey every rule in core-context.md §8 "DO NOT".
> If you need something not in the context, ask — do not invent endpoints, columns, fields,
> or libraries.

## Task
<!-- One or two sentences: what outcome do you want? -->

## Scope / modules in play
<!-- Which module-context files apply? e.g. practice-log.md + dances-catalog.md -->
- [ ] dances-catalog
- [ ] auth-and-profile
- [ ] practice-log
- [ ] videos
- [ ] styles-instructors
- [ ] import-admin

## Touchpoints (files you expect to change)
<!-- e.g. DancePlatform.API/Controllers/PracticeController.cs, pages/practice/practice.component.ts -->

## Constraints for THIS task
<!-- Anything beyond the standing rules: "FE only", "no migration", "must stay backward-compatible" -->

## Acceptance criteria
<!-- How we'll know it's done. Be concrete. -->
1.
2.

## Out of scope
<!-- What NOT to touch this session. -->

---

### Reminders that bite in this codebase (delete if irrelevant)
- New API feature follows: model → AppDbContext → DTO → service interface → impl →
  controller → **`dotnet ef migrations add <Name> --no-build`** → Angular model → service →
  component.
- Controllers return **DTOs**, call **IXxxService**, never `AppDbContext` directly.
- Admin = **DB check**, not a JWT claim. Don't gate on token claims.
- Practice/date work: **local** dates only; parse `DateOnly` as `str + 'T00:00:00'`.
- Profiles default **Private**; public profile only when `Visibility == Public`.
- Add `DateAdded` to any new entity. No emojis in UI copy.
