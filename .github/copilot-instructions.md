# Dance Platform – Copilot Instructions

Full-stack dance learning platform: **.NET 8 REST API** (`DancePlatform.API/`) + **Angular 17** frontend (`dance-platform-ui/`), backed by **PostgreSQL**, deployed on Raspberry Pi OS.

---

## Commands

### Backend (`DancePlatform.API/`)

```bash
dotnet restore
dotnet run                          # API at http://localhost:5000, Swagger at /swagger
dotnet publish -c Release -o api-publish

dotnet ef migrations add <Name>     # New migration
dotnet ef database update           # Apply migrations
dotnet ef database update <PrevName> # Revert last migration
```

### Frontend (`dance-platform-ui/`)

```bash
npm install
npm start                           # Dev server at http://localhost:4200
npm run build:prod                  # Production build → dist/dance-platform-ui/browser
```

No test suite is currently configured in this project.

---

## Architecture

### Request flow (backend)

```
HTTP Request → Controller → Service (interface) → AppDbContext (EF Core) → PostgreSQL
```

- **Controllers** handle HTTP concerns only (routing, auth, HTTP result codes). Business logic lives entirely in **Services**.
- Every service has a matching interface (`IXxxService`) registered as `Scoped` in `Program.cs`. Always program against the interface.
- **DTOs** live in `DTOs/<Domain>/` (e.g., `DTOs/Dance/CreateDanceRequest.cs`, `DanceDto.cs`). Models in `Models/` are EF entities — never return them directly from controllers.
- `AppDbContext` configures all composite keys and relationships explicitly in `OnModelCreating`. EF conventions are not relied on for join tables.

### Data model

```
User ──< UserFavoriteDance >── Dance ──< DanceStyle >── Style
User ──< UserLearnedDance  >── Dance ──< Video (1:many)
```

All entities have a `DateAdded` field defaulting to `DateTime.UtcNow`.  
Join tables (`DanceStyle`, `UserFavoriteDance`, `UserLearnedDance`) use composite primary keys.

### Auth

- Passwords hashed with **BCrypt** (`BCrypt.Net-Next`).
- JWT tokens issued on login/register (7-day expiry), validated via `JwtBearerDefaults`.
- The authenticated user ID is extracted in controllers via `User.FindFirstValue(ClaimTypes.NameIdentifier)` — see the `CurrentUserId` pattern in `DancesController.cs`.
- Several endpoints accept an optional JWT (list/get dances) to return personalized `IsFavorite`/`IsLearned` flags; these must **not** carry `[Authorize]`.

### Frontend (Angular 17)

- Uses **standalone components** throughout — no `NgModule`.
- All routes use **lazy loading** via `loadComponent`.
- The `authInterceptor` (functional interceptor) automatically attaches `Bearer` tokens to every outgoing request.
- Services call `environment.apiUrl` for the API base URL (configured in `src/environments/`).
- The `authGuard` protects routes that require login (currently only `/profile`).

---

## Key Conventions

- **No emojis** anywhere in the UI. Design tone: warm and energetic.
- Only add code comments when logic is non-obvious.
- Follow SOLID and DRY. Keep controllers thin.
- New API features require: Model (if needed) → DTO → Service interface → Service implementation → Controller → `Program.cs` registration.
- New Angular features require: model interface in `models/` → service in `core/services/` → page component in `pages/` → route in `app.routes.ts`.
- All Angular components use external `templateUrl` (`.html`) and `styleUrls` (`.css`) — never inline `template` or `styles`.
- CORS origin is configured in `appsettings.json` under `Cors:Origin`. In development this defaults to `http://localhost:4200`.
- **Never commit** `appsettings.json` with real credentials. The JWT key and DB password must be replaced before deployment.
- All templating and styling should be done in .html and .css files

---

## Configuration (`appsettings.json`)

```json
{
  "ConnectionStrings": { "Default": "Host=...;Database=dance_platform;Username=...;Password=..." },
  "Jwt": { "Key": "...", "Issuer": "DancePlatform", "Audience": "DancePlatformUsers" },
  "Cors": { "Origin": "http://localhost:4200" }
}
```

---

## Deployment (Raspberry Pi)

```bash
# Build
cd DancePlatform.API && dotnet publish -c Release -o api-publish
cd dance-platform-ui && npm run build:prod

# Deploy
cp -r DancePlatform.API/api-publish ./api-publish
cp -r dance-platform-ui/dist/dance-platform-ui/browser ./ui-dist
cd deploy && chmod +x setup.sh && sudo ./setup.sh
```

- API runs as a **systemd service** (`deploy/dance-platform.service`).
- Angular is served by **Apache2** with a reverse proxy to the .NET API (`deploy/apache2.conf`).
- Manage service: `sudo systemctl restart dance-platform` / `sudo journalctl -u dance-platform -f`
