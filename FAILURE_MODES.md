# Failure Modes

How the application handles failures, and how it recovers.

## 1. Database Connection Failure

**What happens:** PostgreSQL is down or unreachable.
**Symptom:** Requests return a `500 Internal Server Error` JSON response.
**Mitigation:**
- The `500` error handler catches unhandled exceptions and returns a clean JSON response instead of a stack trace.
- In Docker, the `web` service depends on a `db` healthcheck — it won't start until Postgres is ready.
- The `restart: always` policy means the web container retries if it crashes on startup due to a missing database.

## 2. Invalid User Input

**What happens:** A client sends non-integer pagination (`?page=abc`) or negative values (`?per_page=-1`).
**Symptom:** Returns `400 Bad Request` with `{"error": "Invalid pagination parameters"}`.
**Mitigation:** All list endpoints validate pagination parameters before querying the database.

## 3. Resource Not Found

**What happens:** A client requests a user, URL, or event that doesn't exist (e.g., `/users/9999`).
**Symptom:** Returns `404 Not Found` with a descriptive JSON error.
**Mitigation:**
- Route-level: Each detail endpoint uses `get_or_none()` and returns a 404 JSON response.
- App-level: Unknown routes (e.g., `/foo`) hit the global 404 handler and also return JSON.

## 4. Wrong HTTP Method

**What happens:** A client sends POST/PUT/DELETE to a GET-only endpoint.
**Symptom:** Returns `405 Method Not Allowed` with JSON.
**Mitigation:** Flask enforces allowed methods per route; the 405 error handler returns JSON.

## 5. Container Crash (Chaos Mode)

**What happens:** The web container is killed (`docker kill`), OOM-killed, or crashes.
**Symptom:** Momentary downtime (seconds).
**Recovery:** Docker's `restart: always` policy automatically restarts the container. The `db` healthcheck ensures the app doesn't restart before Postgres is ready.

**To test:**
```bash
# Start services
docker compose up -d

# Verify it's running
curl http://localhost:5000/health

# Kill the web container
docker kill mlh-pe-web-1

# Wait a few seconds, then verify it restarted
curl http://localhost:5000/health
```

## 6. Data Integrity

**What happens:** A bulk insert partially fails.
**Mitigation:** The seed script wraps inserts in `db.atomic()` — if any row fails, the entire batch is rolled back. No partial data corruption.

## 7. Connection Leaks

**What happens:** Database connections are not properly closed after requests.
**Mitigation:** Flask's `teardown_appcontext` hook closes the Peewee database connection after every request, even if the request raised an exception.

## 8. Duplicate Short Codes

**What happens:** A client submits a `POST /shorten` with a `short_code` that already exists.
**Symptom:** Returns `409 Conflict` with `{"error": "Short code already exists"}`.
**Mitigation:** The endpoint checks uniqueness before inserting. The database also enforces a unique constraint on `short_code`.

## 9. Deactivated URL Access

**What happens:** A client tries to follow a short URL that has been deactivated (soft-deleted).
**Symptom:** Returns `410 Gone` with `{"error": "This short URL has been deactivated"}`. No redirect event is logged.
**Mitigation:** The redirect handler checks `is_active` before redirecting. Inactive URLs are clearly distinguished from missing ones (410 vs 404).

---

## Capacity Assumptions and Known Limits

| Resource | Limit | Notes |
|----------|-------|-------|
| Short code space | ~56 billion codes | 62^6 alphanumeric combinations |
| Concurrent connections | ~100-200 | Flask dev server is single-threaded; use gunicorn for production |
| Database connections | 1 per request | Opened on request, closed on teardown |
| Bulk insert batch size | 100 rows | Used in seed script; prevents memory spikes |
| Max URL length | Unlimited (TEXT column) | PostgreSQL TEXT has no practical limit |
| Pagination default | 20 items/page | Prevents large response payloads |

### Known Limitations

- **Single-process Flask dev server:** Not suitable for high-concurrency production use. For production, use gunicorn with multiple workers.
- **No rate limiting:** The API has no rate limiting. A malicious client could create millions of short URLs.
- **No authentication:** All endpoints are public. Any client can create, update, or delete URLs.
- **No caching:** Every redirect hits the database. For high-traffic short URLs, a Redis cache would help.
- **Sequential short code generation:** Under extreme concurrency, two requests could generate the same code simultaneously. The database unique constraint prevents data corruption, but one request would fail.
