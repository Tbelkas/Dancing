# Module — Auth & Profile (login, register, roles, profile, public profile)

> Load alongside core-context.md for anything touching login/register, JWT, admin gating,
> profile editing, or public profiles.

## Backend
- Controllers: `AuthController` (`/auth/login`, `/auth/register`),
  `ExternalAuthController` (`/auth/external/*` — social sign-in),
  `ProfileController` (`[Authorize]`: `/profile`, `PUT /profile`, `/profile/my-dances`),
  `UsersController` (`/users/{username}` — public)
- Services: `IAuthService`/`AuthService` (BCrypt verification), `ITokenService`/`TokenService`
  (**all** JWT issuance — both the password and social paths go through it, so the `isAdmin`
  claim is stamped in exactly one place), `IUserService`/`UserService`,
  `ExternalAuth/` (`IExternalAuthProvider` + `GoogleAuthProvider`, `FacebookAuthProvider`,
  `ExternalAuthService`, `OAuthStateProtector`)
- Filter: `Filters/RequireAdminAttribute.cs` (checks the signed `isAdmin` claim)
- Models: `User` (+ `ProfileVisibility` enum), `UserLogin`
- DTOs: `DTOs/Auth/` (`LoginRequest`, `RegisterRequest`, `AuthResponse`, `ExternalAuthDtos`),
  `DTOs/User/` (`UserProfileDto`, `PublicProfileDto`, `UpdateProfileRequest`, `MyDancesDto`)

## Frontend
- Pages: `pages/login/` (login+register toggle + social buttons), `pages/auth-callback/`
  (consumes the token from the redirect fragment), `pages/finish-signup/` (username step for a
  first-time social sign-in), `pages/profile/` (guarded, own profile — also "Connected accounts"),
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

## Social sign-in (Google, Facebook)

**Instagram is not available and is not an oversight.** Basic Display shut down 2024-12-04; the
replacement (Instagram API with Instagram Login) serves only Business/Creator accounts and returns
no email, so personal accounts — nearly all of them — have no API path. Don't add an IG button.

- **Server-side authorization-code flow with PKCE.** No provider JS on the page; the client
  secret never leaves the Pi. Facebook needs the redirect flow anyway, so both share one path.
- **Identity is `(Provider, ProviderUserId)`**, enforced by a unique index on `UserLogins` —
  never the email. `User.Email` is display/recovery data only.
- **Never auto-merges into an existing account.** A social sign-in resolves to a linked account
  or a brand-new one; linking happens from the profile page while already authenticated
  (`POST /auth/external/{provider}/link-start`, which is a POST so the bearer token rides in a
  header instead of the query string).
- **`state` is HMAC-signed, single-use, 15 min**, and carries the PKCE verifier plus the optional
  link user id (`OAuthStateProtector`). Signed with `Jwt:Key`, not IDataProtection, because the
  Pi's data-protection key ring isn't reliably persisted across restarts.
- **The access token comes back in the URL *fragment*** (`/auth/callback#token=…`), never a query
  param — a fragment isn't sent to the server, keeping it out of Apache's access log and out of
  `Referer`. Both new pages `history.replaceState` it away immediately.
- **Signup tickets use a distinct audience** (`DancePlatformSignup`), so a ticket presented as a
  bearer token fails audience validation before reaching any `[Authorize]` endpoint.
- **A social-only account has an empty `PasswordHash`.** `AuthService.LoginAsync` rejects an
  empty hash *before* calling `BCrypt.Verify` — otherwise the password form could reach it.
- Unlinking the last login method is refused (`UnlinkResult.WouldLockOut`); there is no password
  reset to fall back on. The Facebook data-deletion callback bypasses that guard by design.
- A provider with no configured credentials is absent from `/auth/external/providers`, renders no
  button, and 404s on `/start` — so a dev box with no secrets degrades to the password form.
