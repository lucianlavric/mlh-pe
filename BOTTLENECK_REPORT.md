# Bottleneck Analysis Report

## Initial Baseline (Flask Dev Server, Single Instance)

- **Setup:** 1 Flask dev server (single-threaded), PostgreSQL
- **50 concurrent users:** ~450 req/s, p95 ~50ms, 0% errors
- **200 concurrent users:** ~550 req/s, p95 ~400ms, ~15% errors
- **500 concurrent users:** ~589 req/s, p95 783ms, **27% error rate**

**Bottleneck identified:** Flask's built-in dev server is single-threaded. Under high concurrency, it queues requests and eventually drops connections. The server itself was the bottleneck, not the database.

## Fix 1: Gunicorn (Production WSGI Server)

Replaced Flask dev server with **gunicorn** (4 workers, 2 threads per worker = 8 concurrent handlers per instance).

**Result:** Error rate dropped from 27% to ~5% at 500 concurrent users.

## Fix 2: Horizontal Scaling (3 Instances + Nginx)

Deployed **3 gunicorn instances** behind an **Nginx** load balancer. Total capacity: 24 concurrent handlers (3 × 4 workers × 2 threads).

**Result at 500 concurrent users:**
- **0% error rate** (was 27%)
- **705 req/s** (was 589 req/s)
- **p95 latency: 768ms** (was 783ms)

## Fix 3: Redis Caching

Added **Redis** to cache URL lookups on the redirect path (the hottest endpoint at 40% of traffic). Cache TTL: 300 seconds. Cache is invalidated on URL update or delete.

**Impact:** Redirect lookups that hit cache skip the PostgreSQL query entirely, reducing database load under high concurrency.

## Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Error rate (500 VUs) | 27% | 0% | Eliminated |
| Throughput | 589 req/s | 705 req/s | +20% |
| p95 latency | 783ms | 768ms | -2% |
| Concurrent handlers | 1 | 24 | 24x |

**Root cause:** The single-threaded Flask dev server was the primary bottleneck. Switching to gunicorn + horizontal scaling solved it. Redis caching reduces database pressure but the main win came from concurrency.
