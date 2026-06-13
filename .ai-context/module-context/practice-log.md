# Module — Practice Log & Streaks

> Load alongside core-context.md for anything touching practice sessions or streaks.
> **This is the most timezone-sensitive area of the app — read the rules.**

## Backend
- Controller: `Controllers/PracticeController.cs` (class-level `[Authorize]`)
- Service: `IPracticeService` / `PracticeService.cs`
- Model: `PracticeSession` (`Date` is **`DateOnly`** — a calendar day, not a timestamp)
- DTOs: `DTOs/Practice/` — `PracticeSessionDto`, `CreatePracticeSessionRequest`
- Endpoints: `GET /practice`, `POST /practice`, `DELETE /practice/{id}` (own sessions only;
  user resolved from JWT, not body).

## Frontend
- Page: `pages/practice/` (`practice.component.ts` / `.html`) — guarded route `/practice`
- Service: `core/services/practice.service.ts`
- Model: `models/practice-session.model.ts`
- UI: log form (dance, date, duration?, notes?), streak counter, total, grouped list, delete.

## Rules (do not regress — known-issues #1/#2)
- **All day logic is LOCAL, never UTC.**
  - Form date default = **user's local today** (NOT `new Date().toISOString().split('T')[0]`).
  - Render a stored `DateOnly` string by parsing **local midnight**:
    `new Date(dateStr + 'T00:00:00')` (NOT `new Date(dateStr)`, which is UTC midnight and
    shifts the day west of UTC).
  - Streak = consecutive local days with ≥1 session, anchored on local today/yesterday.
- One session = one dance + one calendar date (+ optional duration/notes). Multiple sessions
  per day are allowed.
