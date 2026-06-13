# Module — Styles, Musical Styles & Instructors (taxonomy)

> Load alongside core-context.md for taxonomy/instructor work.

## Styles (dance categories: Latin, Ballroom, Street, …)
- Controller: `Controllers/StylesController.cs` · Service `IStyleService`/`StyleService`
- Model `Style`; join `DanceStyle` (Dance↔Style m2m); join `UserMyStyle` (User↔Style "my styles")
- DTOs: `DTOs/Style/` (`StyleDto`, `CreateStyleRequest`)
- Endpoints: GET list/one (anon), `POST /styles` (⚠️ unauthenticated — known-issues #A),
  `DELETE /styles/{id}` (admin), `POST /styles/{id}/mystyle` (auth toggle).
- FE: `core/services/style.service.ts`, `models/style.model.ts`.

## Musical Styles (genres: Salsa, Hip-Hop, Tango, …)
- Controller: `Controllers/MusicalStylesController.cs` · Service `IMusicalStyleService`/impl
- Model `MusicalStyle`; join `DanceMusicalStyle` (Dance↔MusicalStyle m2m)
- DTOs: `DTOs/MusicalStyle/`
- Endpoints: GET list/one (anon); `POST` + `DELETE` **admin-only**.
- FE: `core/services/musical-style.service.ts`, `models/musical-style.model.ts`.

## Instructors
- Controller: `Controllers/InstructorsController.cs` · Service `IInstructorService`/impl
- Model `Instructor` (Name, Bio?, AvatarUrl?, Website? — **no DateAdded**); join `DanceInstructor`
  (Dance↔Instructor m2m). **Instructor side of the join is `OnDelete=Restrict`** — you can't
  delete an instructor still linked to a dance; unlink first.
- DTOs: `DTOs/Instructor/`
- Endpoints: GET list/one (anon); `POST` + `DELETE` **admin-only**.
- FE: `core/services/instructor.service.ts`, `models/instructor.model.ts`; shown on dance detail.

## Note on consistency
Styles' create is unauthenticated while MusicalStyles' and Instructors' are admin-gated.
Treat that as the bug (known-issues #A), not the pattern.
