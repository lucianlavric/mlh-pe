# Operational Runbook

Step-by-step procedures for operating and troubleshooting the URL shortener service.

## Starting the Service

### Local Development
```bash
uv sync
createdb hackathon_db  # first time only
cp .env.example .env   # first time only
uv run run.py
```

### Docker Production
```bash
docker compose up -d --build
```

### Verify Health
```bash
curl http://localhost:5000/health
# Expected: {"status":"ok"} with HTTP 200
```

## Stopping the Service

```bash
# Docker
docker compose down

# Local
# Ctrl+C in the terminal running run.py
```

## Restarting After Failure

Docker's `restart: always` policy handles automatic restarts. To manually restart:

```bash
docker compose restart web
```

## Troubleshooting

### App returns 500 errors

**Likely cause:** Database connection failure.

1. Check if PostgreSQL is running:
   ```bash
   docker compose logs db        # Docker
   pg_isready                    # Local
   ```
2. Check database credentials in `.env` match what PostgreSQL expects
3. Verify the database exists:
   ```bash
   psql -l | grep hackathon_db
   ```

### App won't start — port in use

```bash
# Find what's using the port
lsof -i :5000

# Kill it
kill $(lsof -ti:5000)

# Or change the port in docker-compose.yml
```

### Tables don't exist

Tables are auto-created on app startup. If they're missing:

```bash
# Drop and recreate
psql -d hackathon_db -c "DROP TABLE IF EXISTS events, urls, users CASCADE;"
# Restart the app — tables will be recreated
```

### Seed data is missing

```bash
uv run python seed.py
```

This loads users, URLs, and events from `seed_data/` CSVs.

### Docker container keeps crashing

```bash
# Check logs
docker compose logs web --tail 50

# Common fixes:
# 1. Database not ready — wait for healthcheck
docker compose down && docker compose up -d

# 2. Port conflict — change port in docker-compose.yml
# 3. Bad environment variables — check docker-compose.yml environment section
```

### Tests failing locally

```bash
# Tests use SQLite in-memory, no Postgres needed
uv sync --dev
uv run pytest -v --tb=long
```

## Monitoring

### Health Check
```bash
curl http://localhost:5000/health
# Returns: {"status":"ok"}
```

### Check recent events (audit log)
```bash
curl http://localhost:5000/events?per_page=10
```

### Check active URLs
```bash
curl http://localhost:5000/urls
```

## Alert Response Procedures

| Symptom | Action |
|---------|--------|
| `/health` returns non-200 | Check database connectivity, restart app |
| High 500 error rate | Check `docker compose logs web`, verify DB is up |
| Container not running | Docker auto-restarts; if stuck, `docker compose restart web` |
| Database connection refused | `docker compose restart db`, wait for healthcheck |
| Disk full | Clean up Docker volumes: `docker system prune` |
