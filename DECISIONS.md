# Technical Decisions

Key architectural and implementation decisions, with rationale.

## 1. Peewee ORM over SQLAlchemy

**Decision:** Use Peewee as the ORM instead of SQLAlchemy.

**Why:** Peewee is lightweight, has a simpler API, and is well-suited for small-to-medium applications. The hackathon template was built around it, and switching would add unnecessary complexity. Peewee's `DatabaseProxy` pattern also makes it trivial to swap databases for testing (SQLite in-memory vs PostgreSQL in production).

## 2. SQLite In-Memory for Tests

**Decision:** Tests use `SqliteDatabase(":memory:")` instead of a real PostgreSQL instance.

**Why:** This makes tests fast (~0.5s for 59 tests), eliminates CI infrastructure needs (no Postgres service in GitHub Actions), and isolates test runs completely. The tradeoff is that Postgres-specific features (JSONB, array columns) can't be tested, but we don't use any.

## 3. Soft Delete for URLs

**Decision:** `DELETE /urls/<id>` sets `is_active=False` instead of removing the row.

**Why:** Hard deletes would break referential integrity with the events table (audit log). Soft deletes preserve history, allow recovery, and ensure the audit trail remains intact. Deactivated URLs return `410 Gone` on redirect, clearly communicating the state.

## 4. Event Audit Log

**Decision:** Every URL operation (create, update, delete, redirect) creates an Event record.

**Why:** Provides a complete audit trail for debugging and analytics. The event log answers questions like "who created this URL?", "when was it deactivated?", and "how many redirects has it served?" without needing separate analytics infrastructure.

## 5. Auto-Create Tables on Startup

**Decision:** The app calls `db.create_tables()` on every startup rather than requiring a migration step.

**Why:** Peewee's `create_tables` is idempotent (uses `CREATE TABLE IF NOT EXISTS`). This eliminates the need for a separate migration tool in a hackathon context and ensures the app works on first run against an empty database.

## 6. JSON Error Responses Everywhere

**Decision:** All error responses (400, 404, 405, 500) return JSON, never HTML.

**Why:** This is an API service — clients expect machine-readable errors. Flask's default error pages return HTML, which breaks API consumers. Custom error handlers ensure consistent `{"error": "..."}` responses at every level.

## 7. Docker restart: always

**Decision:** The web container uses `restart: always` policy.

**Why:** For a production service, automatic recovery from crashes is essential. If the app crashes (OOM, unhandled exception, etc.), Docker restarts it within seconds. Combined with the database healthcheck dependency, this ensures the app waits for Postgres before reconnecting.

## 8. Short Code Generation

**Decision:** 6-character alphanumeric codes generated with `random.choices()`, with a retry loop for uniqueness.

**Why:** 6 characters from `[a-zA-Z0-9]` gives 62^6 = ~56 billion possible codes — collision probability is negligible at our scale. The retry loop (up to 10 attempts) handles the rare case. Custom codes are also supported for users who want memorable URLs.

## 9. Pagination with Validation

**Decision:** All list endpoints require positive integer pagination params, defaulting to page=1, per_page=20.

**Why:** Without pagination, listing thousands of URLs would be slow and memory-heavy. Validating params prevents crashes from malformed input (`?page=abc`) and returns a clean 400 error instead.
