# Module — Auth & Profile (login, register, roles, profile, public profile)

> Load alongside core-context.md for anything touching login/register, JWT, admin gating,
> profile editing, or public profiles.

## Backend
- Controllers: `AuthController` (`/auth/login`, `/auth/register`),
  `ProfileController` (`[Authorize]`: `/profile`, `PUT /profile`, `/profile/my-dances`),
  `UsersController` (`/users/{username}` — public)
- Services: `IAuthService`/`AuthService` (BCrypt + JWT issuance, stamps the `isAdmin` claim),
  `IUserService`/`UserService`
- Filter: `Filters/RequireAdminAttribute.cs` (checks the signed `isAdmin` claim)
- Models: `User` (+ `ProfileVisibility` enum)
- DTOs: `DTOs/Auth/` (`LoginRequest`, `RegisterRequest`, `AuthResponse`),
  `DTOs/User/` (`UserProfileDto`, `PublicProfileDto`, `UpdateProfileRequest`, `MyDancesDto`)

## Frontend
- Pages: `pages/login/` (login+register toggle), `pages/profile/` (guarded, own profile),
  `pages/user-profile/` (public, `/users/:username`)
- Services: `core/services/auth.service.ts` (signals: `isAuthenticated`, current user; token
  in `localStorage['dp_token']`), `role.service.ts` (`loadFromToken()` decodes the `isAdmin`
  claim — no network call), `profile.service.ts`, `user.service.ts`
- Guard: `core/guards/auth.guard.ts`; Interceptor: `core/interceptors/auth.interceptor.ts`
  (attaches `Bearer` token)

## Key behaviours / rules
- **JWT carries `NameIdentifier` (userId) + `Name` (username) + signed `isAdmin` claim.**
  Admin gating reads that claim (`RequireAdminAttribute` server-side; `jwtIsAdmin()` in the FE)
  — no DB lookup, no `/role/me` endpoint. Never trust an *unsigned* client-sent admin flag
  (core DO-NOT #1). A grant/revoke takes effect on the user's next login.
- **Profiles default `Private`.** `GET /users/{username}` returns data **only if Public**;
  otherwise "Profile not available" (also for anonymous viewers).
- Login mode validates empty fields **client-side** before calling the API (forms are
  `novalidate`, so `required` alone doesn't block — known-issues #3).
- Editable profile: `name`, `nickname`, `avatarUrl`, `visibility`.
- Passwords BCrypt-hashed (`BCrypt.Net-Next`); never log/store plaintext.
