# Service Level Objectives (SLOs)

Defines the reliability and performance targets for the URL shortener service.

## SLIs (Service Level Indicators)

| Indicator | How We Measure It |
|-----------|-------------------|
| **Availability** | % of `/health` checks returning 200 over a rolling window |
| **Latency** | p95 response time across all endpoints |
| **Error Rate** | % of requests returning 5xx status codes |
| **Redirect Latency** | p95 response time for `GET /<short_code>` specifically |

## SLOs (Service Level Objectives)

| Objective | Target | Measured By |
|-----------|--------|-------------|
| **Availability** | 99.9% (43 min downtime/month) | Health check monitoring |
| **Latency (p95)** | < 1000ms | k6 load test results |
| **Error Rate** | < 1% under normal load | k6 threshold checks |
| **Error Rate (peak)** | < 5% at 500 concurrent users | k6 Gold tier test |
| **Redirect Latency (p95)** | < 800ms | k6 `redirect_duration` metric |
| **Recovery Time** | < 30 seconds after container crash | Docker restart: always |

## Current Performance vs SLOs

| Objective | Target | Actual | Status |
|-----------|--------|--------|--------|
| Availability | 99.9% | 100% (during test window) | MEETING |
| Latency p95 | < 1000ms | 768ms at 500 VUs | MEETING |
| Error Rate | < 1% | 0% at 500 VUs | MEETING |
| Error Rate (peak) | < 5% | 0% at 500 VUs | MEETING |
| Redirect p95 | < 800ms | 774ms at 500 VUs | MEETING |
| Recovery Time | < 30s | ~5s (Docker restart) | MEETING |

## Error Budget

With a 99.9% availability SLO:
- **Monthly error budget:** 43.2 minutes of downtime
- **Weekly error budget:** 10.1 minutes of downtime
- **Current consumption:** 0% (no unplanned downtime observed)

## How SLOs Map to k6 Thresholds

```javascript
// In loadtest.js
thresholds: {
    http_req_duration: ['p(95)<3000'],  // Maps to Latency SLO (conservative)
    errors: ['rate<0.05'],              // Maps to Error Rate SLO (peak)
}
```

## When to Revisit

- After any incident that consumes >50% of error budget
- When adding new endpoints or changing infrastructure
- Quarterly review of whether targets are too tight or too loose
