# Module — Auth & Profile (login, register, roles, profile, public profile)

> Load alongside core-context.md for anything touching login/register, JWT, admin gating,
> profile editing, or public profiles.

## Backend
- Controllers: `AuthController` (`/auth/login`, `/auth/register`), `RoleController` (`/role/me`),
  `ProfileController` (`[Authorize]`: `/profile`, `PUT /profile`, `/profile/my-dances`),
  `UsersController` (`/users/{username}` — public)
- Services: `IAuthService`/`AuthService` (BCrypt + JWT issuance), `IRoleService`/`RoleService`
  (`IsAdminAsync` — used by `RequireAdminAttribute`), `IUserService`/`UserService`
- Filter: `Filters/RequireAdminAttribute.cs`
- Models: `User` (+ `ProfileVisibility` enum)
- DTOs: `DTOs/Auth/` (`LoginRequest`, `RegisterRequest`, `AuthResponse`),
  `DTOs/User/` (`UserProfileDto`, `PublicProfileDto`, `UpdateProfileRequest`, `MyDancesDto`)

## Frontend
- Pages: `pages/login/` (login+register toggle), `pages/profile/` (guarded, own profile),
  `pages/user-profile/` (public, `/users/:username`)
- Services: `core/services/auth.service.ts` (signals: `isAuthenticated`, current user; token
  in `localStorage['dp_token']`), `role.service.ts` (`loadRole()` on startup),
  `profile.service.ts`, `user.service.ts`
- Guard: `core/guards/auth.guard.ts`; Interceptor: `core/interceptors/auth.interceptor.ts`
  (attaches `Bearer` token)

## Key behaviours / rules
- **JWT carries only `NameIdentifier` (userId) + `Name` (username)** — no admin flag.
  Admin is a **live DB check**. Frontend gets its role from `GET /role/me` on startup.
  → Never gate admin UI/endpoints on a token claim (core DO-NOT #1).
- **Profiles default `Private`.** `GET /users/{username}` returns data **only if Public**;
  otherwise "Profile not available" (also for anonymous viewers).
- Login mode validates empty fields **client-side** before calling the API (forms are
  `novalidate`, so `required` alone doesn't block — known-issues #3).
- Editable profile: `name`, `nickname`, `avatarUrl`, `visibility`.
- Passwords BCrypt-hashed (`BCrypt.Net-Next`); never log/store plaintext.
