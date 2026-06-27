# Dance Platform

A full-stack dance learning platform built with .NET 8 (REST API) and Angular, deployed on Raspberry Pi OS.

## Features

- Browse dances by style, search by name or style
- Favorite and mark dances as learned (requires account)
- Video player with adjustable playback speed and repeat region
- User profiles with visibility settings
- JWT authentication, prepared for OAuth extension

## AI / Contributor Context (`.ai-context/`)

A layered **context bundle** lives in [`.ai-context/`](.ai-context/00-README.md) — a curated,
code-grounded description of the system (architecture, DB schema, API contracts, business
rules, known issues, and per-feature notes) so an AI assistant or new contributor can work
inside the project without re-deriving everything each time.

- **Layer 1 — core** ([`core-context.md`](.ai-context/core-context.md) + [`reference/`](.ai-context/reference)): stack, architecture, folder structure, conventions, and the "DO NOT" rules. Load this every session.
- **Layer 2 — module** ([`module-context/`](.ai-context/module-context)): one file per feature; load the relevant one.
- **Layer 3 — session** ([`session-context.template.md`](.ai-context/session-context.template.md)): the per-task brief.

Start with [`.ai-context/00-README.md`](.ai-context/00-README.md) for the prepend prompt and usage. Keep the bundle updated when the code changes.

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | .NET 8 Web API, Entity Framework Core 8 |
| Database   | PostgreSQL (via Npgsql EF provider) |
| Auth       | JWT Bearer, BCrypt password hashing |
| Frontend   | Angular 17 (standalone components, signals) |
| Deployment | Raspberry Pi OS, systemd, Apache2   |

---

## Project Structure

```
Dance/
├── DancePlatform.API/          # .NET 8 REST API
│   ├── Controllers/            # Auth, Dances, Styles, Videos, Profile, Search
│   ├── Data/                   # AppDbContext (EF Core)
│   ├── DTOs/                   # Request/response data transfer objects
│   ├── Models/                 # Entity models
│   ├── Services/               # Business logic layer
│   ├── Program.cs
│   └── appsettings.json
├── dance-platform-ui/          # Angular 17 frontend
│   └── src/app/
│       ├── core/               # Services, guards, interceptors
│       ├── models/             # TypeScript interfaces
│       ├── pages/              # Login, Dances, Dance Detail, Profile
│       └── shared/components/  # VideoPlayer
└── deploy/                     # Deployment configs
    ├── dance-platform.service  # systemd unit
    ├── apache2.conf            # Apache2 virtual host
    └── setup.sh                # Automated setup script
```

---

## Development Setup

### Prerequisites

- [.NET 8 SDK](https://dotnet.microsoft.com/download)
- [Node.js 20+](https://nodejs.org/)
- [PostgreSQL 15+](https://www.postgresql.org/)
- Angular CLI: `npm install -g @angular/cli`

### Backend

```bash
cd DancePlatform.API

# Restore packages
dotnet restore

# Provide local secrets (NOT committed — appsettings.Development.json is gitignored):
cp appsettings.Development.json.example appsettings.Development.json
# then edit it with your PostgreSQL connection string and a local Jwt:Key (>= 32 chars).

# Apply migrations (creates DB schema)
dotnet ef database update

# Run API
dotnet run
# API available at http://localhost:5000
# Swagger UI at http://localhost:5000/swagger
```

### Frontend

```bash
cd dance-platform-ui

npm install
npm start
# App available at http://localhost:4200
```

---

## Testing

```bash
# Backend — xUnit (SlugGenerator + DanceService against SQLite in-memory)
dotnet test DancePlatform.Tests/DancePlatform.Tests.csproj

# Frontend — Vitest (pure utils: jwt + video-url parsing)
cd dance-platform-ui && npm test
```

Both run headless in CI on every push / PR — see [`.github/workflows/ci.yml`](.github/workflows/ci.yml),
which also builds the API and a production Angular bundle.

---

## Database Migrations

```bash
cd DancePlatform.API

# Create a new migration
dotnet ef migrations add <MigrationName>

# Apply migrations
dotnet ef database update

# Revert last migration
dotnet ef database update <PreviousMigrationName>
```

---

## REST API Reference

### Authentication

| Method | Endpoint              | Auth | Description        |
|--------|-----------------------|------|--------------------|
| POST   | /api/auth/login       | No   | Login              |
| POST   | /api/auth/register    | No   | Create account     |

### Dances

| Method | Endpoint                    | Auth     | Description              |
|--------|-----------------------------|----------|--------------------------|
| GET    | /api/dances                 | Optional | List all dances          |
| GET    | /api/dances/{id}            | Optional | Get dance by ID          |
| POST   | /api/dances                 | Required | Create dance             |
| PUT    | /api/dances/{id}            | Required | Update dance             |
| DELETE | /api/dances/{id}            | Required | Delete dance             |
| POST   | /api/dances/{id}/favorite   | Required | Toggle favorite          |
| POST   | /api/dances/{id}/learned    | Required | Toggle learned           |

### Styles

| Method | Endpoint          | Auth     | Description       |
|--------|-------------------|----------|-------------------|
| GET    | /api/styles       | Optional | List all styles   |
| GET    | /api/styles/{id}  | Optional | Get style by ID   |
| POST   | /api/styles       | Required | Create style      |
| DELETE | /api/styles/{id}  | Required | Delete style      |

### Videos

| Method | Endpoint                     | Auth     | Description           |
|--------|------------------------------|----------|-----------------------|
| GET    | /api/videos/dance/{danceId}  | Optional | Videos for a dance    |
| GET    | /api/videos/{id}             | Optional | Get video by ID       |
| POST   | /api/videos                  | Required | Add video             |
| PUT    | /api/videos/{id}             | Required | Update video          |
| DELETE | /api/videos/{id}             | Required | Delete video          |

### Profile

| Method | Endpoint      | Auth     | Description           |
|--------|---------------|----------|-----------------------|
| GET    | /api/profile  | Required | Get own profile       |
| PUT    | /api/profile  | Required | Update profile        |

### Search

| Method | Endpoint            | Auth     | Description                        |
|--------|---------------------|----------|------------------------------------|
| GET    | /api/search/dances  | Optional | Search by `q` (name) and `styleId` |

**Example search:**
```
GET /api/search/dances?q=salsa&styleId=2
```

---

## Deployment (Raspberry Pi)

### Build artifacts

```bash
# Build API
cd DancePlatform.API
dotnet publish -c Release -o api-publish

# Build Angular
cd dance-platform-ui
npm run build:prod
# Output: dist/dance-platform-ui/browser
```

### Run setup script

Copy `deploy/` contents to the Pi, then:

```bash
# Copy build artifacts alongside setup script
cp -r DancePlatform.API/api-publish ./api-publish
cp -r dance-platform-ui/dist/dance-platform-ui/browser ./ui-dist

cd deploy
chmod +x setup.sh
sudo ./setup.sh
```

### Manage the service

```bash
# Status
sudo systemctl status dance-platform

# Restart
sudo systemctl restart dance-platform

# Logs
sudo journalctl -u dance-platform -f
```

---

## Configuration

The committed `DancePlatform.API/appsettings.json` holds **no secrets** — only safe dev defaults
(empty DB password, a `dev-insecure` JWT key). Real values are supplied per environment and are
never committed:

- **Local dev:** `appsettings.Development.json` (gitignored; copy from `.example`).
- **Production:** environment variables on the host, which override `appsettings.json`. The systemd
  unit sets `ConnectionStrings__Default`, `Jwt__Key`, `Cors__Origin`, and `ASPNETCORE_ENVIRONMENT=Production`.

`Jwt:Key` must be a strong random string (>= 32 chars). The API **refuses to boot outside Development**
if the key is missing or still the `dev-insecure` placeholder — so a misconfigured deploy fails fast
instead of signing tokens with a public key.

**Never commit production secrets to source control.**

---

## Data Model

```
User ─────────────────── UserFavoriteDance ─── Dance
  │                                              │
  └── UserLearnedDance ──────────────────────────┘
                                                 │
                                            DanceStyle ─── Style
                                                 │
                                               Video (one-to-many)
```

All entities include a `DateAdded` (UTC) field.
