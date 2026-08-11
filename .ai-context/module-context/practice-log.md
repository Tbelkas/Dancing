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

## The streak has exactly one implementation
`core/utils/practice.utils.ts` → `practiceStreak(sessions, now?)` returns
`{ current, longest, atRisk }`. The Practice Log and the profile both read it, so the number
can't drift between pages. Covered by `practice.utils.spec.ts`.

- **Never compute a streak at a call site.** Need one somewhere new? Call `practiceStreak`.
- It takes **raw** sessions and applies the meaningful-session rule (`meaningfulSessions`,
  > 60s) itself, so a caller can't pass the wrong input set. Use that same helper anywhere
  else "a real session" is meant — the threshold lives in one place.
- Rules it encodes: consecutive **practice days** with ≥1 meaningful session; alive while the
  newest day is today *or* yesterday (one grace day); future-dated sessions are **ignored**,
  not treated as a break; day arithmetic goes through calendar fields, never ±86400000ms.

## Rules (do not regress — known-issues #1/#2)
- **All day logic is LOCAL, never UTC.**
  - The day boundary is the **practice day**: `toPracticeDateString` shifts back 4 h, so a
    1 AM session counts toward the previous day. Anything comparing against "today" —
    including the **form date default** — uses it, not plain local midnight, or a session
    logged at 2 AM lands on a different day than the streak thinks it's on.
  - Render a stored `DateOnly` string by parsing **local midnight**:
    `new Date(dateStr + 'T00:00:00')` (NOT `new Date(dateStr)`, which is UTC midnight and
    shifts the day west of UTC).
- One session = one dance + one calendar date (+ optional duration/notes). Multiple sessions
  per day are allowed.
