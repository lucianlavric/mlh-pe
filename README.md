# MLH PE Hackathon — URL Shortener

A production-grade URL shortener built with Flask, Peewee ORM, and PostgreSQL.

**Stack:** Flask · Peewee ORM · PostgreSQL · uv · Docker · GitHub Actions CI

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/lucianlavric/mlh-pe.git && cd mlh-pe

# 2. Install dependencies
uv sync

# 3. Create the database
createdb hackathon_db

# 4. Configure environment
cp .env.example .env   # edit if your DB credentials differ

# 5. Seed data (optional)
uv run python seed.py

# 6. Run the server
uv run run.py

# 7. Verify
curl http://localhost:5000/health
# → {"status":"ok"}
```

### Docker Quick Start

```bash
docker compose up -d --build
curl http://localhost:5001/health
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_NAME` | `hackathon_db` | PostgreSQL database name |
| `DATABASE_HOST` | `localhost` | Database host |
| `DATABASE_PORT` | `5432` | Database port |
| `DATABASE_USER` | `postgres` | Database user |
| `DATABASE_PASSWORD` | `postgres` | Database password |
| `FLASK_DEBUG` | `true` | Enable Flask debug mode |

See `.env.example` for the template.

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│   Client     │────▶│  Flask App (run.py)                          │
│  (curl/web)  │◀────│                                              │
└─────────────┘     │  ┌────────────┐  ┌─────────────────────────┐ │
                    │  │  Routes     │  │  Error Handlers          │ │
                    │  │  /shorten   │  │  400, 404, 405, 500     │ │
                    │  │  /<code>    │  │  (all return JSON)      │ │
                    │  │  /urls/*    │  └─────────────────────────┘ │
                    │  │  /users/*   │                              │
                    │  │  /events/*  │                              │
                    │  │  /health    │                              │
                    │  └─────┬──────┘                               │
                    │        │                                      │
                    │  ┌─────▼──────┐                               │
                    │  │  Models     │                              │
                    │  │  User       │                              │
                    │  │  Url        │◀── short_code (unique)      │
                    │  │  Event      │◀── audit log for all ops    │
                    │  └─────┬──────┘                               │
                    └────────┼──────────────────────────────────────┘
                             │
                    ┌────────▼──────┐
                    │  PostgreSQL    │
                    │  hackathon_db  │
                    └───────────────┘
```

## API Endpoints

### Health

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/health` | Health check | `{"status": "ok"}` → 200 |

### URL Shortener

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| POST | `/shorten` | Create a short URL | URL object → 201 |
| GET | `/<short_code>` | Redirect to original URL | 302 redirect |
| GET | `/urls` | List all URLs (paginated) | Array → 200 |
| GET | `/urls/<id>` | Get URL by ID | URL object → 200 |
| GET | `/urls/code/<code>` | Get URL by short code | URL object → 200 |
| PUT | `/urls/<id>` | Update a URL | URL object → 200 |
| DELETE | `/urls/<id>` | Deactivate a URL | Message → 200 |

### Users

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/users` | List all users (paginated) | Array → 200 |
| GET | `/users/<id>` | Get user by ID | User object → 200 |

### Events

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/events` | List all events (paginated) | Array → 200 |
| GET | `/events/<id>` | Get event by ID | Event object → 200 |

### POST /shorten — Request Body

```json
{
  "url": "https://example.com/long-url",
  "user_id": 1,
  "short_code": "CUSTOM",
  "title": "My Link"
}
```

- `url` (required): Must start with `http://` or `https://`
- `user_id` (required): Must reference an existing user
- `short_code` (optional): Custom code; auto-generated if omitted
- `title` (optional): Display name for the URL

### PUT /urls/:id — Request Body

```json
{
  "url": "https://example.com/new-url",
  "title": "New Title",
  "is_active": false
}
```

All fields are optional. At least one must be provided.

### Pagination

All list endpoints support `?page=1&per_page=20`. Both must be positive integers.

### Error Responses

All errors return JSON:

```json
{"error": "Description of what went wrong"}
```

| Code | Meaning |
|------|---------|
| 400 | Bad request (invalid input, missing fields, bad pagination) |
| 404 | Resource not found |
| 405 | Method not allowed |
| 409 | Conflict (duplicate short code) |
| 410 | Gone (deactivated URL) |
| 500 | Internal server error |

## Project Structure

```
mlh-pe/
├── app/
│   ├── __init__.py          # App factory (create_app)
│   ├── database.py          # DatabaseProxy, BaseModel, connection hooks
│   ├── errors.py            # JSON error handlers (400/404/405/500)
│   ├── models/
│   │   ├── __init__.py      # Model exports
│   │   ├── user.py          # User model
│   │   ├── url.py           # Url model (short_code, original_url, is_active)
│   │   └── event.py         # Event model (audit log)
│   └── routes/
│       ├── __init__.py      # Blueprint registration
│       ├── users.py         # /users endpoints
│       ├── urls.py          # /shorten, /<code>, /urls endpoints
│       └── events.py        # /events endpoints
├── tests/                   # pytest test suite (59 tests, 91% coverage)
├── seed_data/               # CSV seed files (users, urls, events)
├── .github/workflows/ci.yml # GitHub Actions CI
├── Dockerfile               # Container image
├── docker-compose.yml       # Multi-service with restart: always
├── FAILURE_MODES.md         # Failure mode documentation
├── RUNBOOK.md               # Operational runbook
├── DECISIONS.md             # Technical decision records
├── seed.py                  # Database seeder
├── run.py                   # Entry point
└── .env.example             # Environment variable template
```

## Testing

```bash
# Run all tests with coverage
uv run pytest

# Run with verbose output
uv run pytest -v --tb=short
```

Tests use SQLite in-memory — no PostgreSQL needed. CI enforces a 70% coverage floor.

## Deployment

### With Docker Compose (recommended)

```bash
# Start
docker compose up -d --build

# Verify
curl http://localhost:5001/health

# View logs
docker compose logs -f web

# Stop
docker compose down

# Rollback: revert to previous image
docker compose down
git checkout <previous-commit>
docker compose up -d --build
```

### Without Docker

```bash
uv sync
createdb hackathon_db
cp .env.example .env
uv run python seed.py   # optional
uv run run.py
```

### Rollback Steps

1. `docker compose down` (stop current)
2. `git log --oneline` (find last good commit)
3. `git checkout <commit>` (revert code)
4. `docker compose up -d --build` (redeploy)
5. `curl http://localhost:5001/health` (verify)
