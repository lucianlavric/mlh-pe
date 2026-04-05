import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const redirectDuration = new Trend('redirect_duration');

const BASE_URL = __ENV.BASE_URL || 'http://localhost:5001';

// Stages ramp from Bronze (50) to Silver (200) to Gold (500)
export const options = {
  stages: [
    { duration: '10s', target: 50 },   // Bronze: ramp to 50
    { duration: '20s', target: 50 },   // Hold at 50
    { duration: '10s', target: 200 },  // Silver: ramp to 200
    { duration: '20s', target: 200 },  // Hold at 200
    { duration: '10s', target: 500 },  // Gold: ramp to 500
    { duration: '20s', target: 500 },  // Hold at 500
    { duration: '10s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'],  // Silver: p95 under 3s
    errors: ['rate<0.05'],             // Gold: error rate under 5%
  },
};

// Short codes from seed data (mix of active and inactive)
const ACTIVE_CODES = ['VcJfJv', 'hSdWFz', 'e3X32L', 'vXoXtL', 'sPqGFc', 'QYF60z'];
const TEST_URLS = [
  'https://example.com/test1',
  'https://example.com/test2',
  'https://example.com/test3',
];

export default function () {
  const scenario = Math.random();

  if (scenario < 0.4) {
    // 40%: Redirect (the core operation)
    const code = ACTIVE_CODES[Math.floor(Math.random() * ACTIVE_CODES.length)];
    const res = http.get(`${BASE_URL}/${code}`, { redirects: 0 });
    const success = check(res, {
      'redirect status is 302': (r) => r.status === 302,
    });
    errorRate.add(!success);
    redirectDuration.add(res.timings.duration);

  } else if (scenario < 0.6) {
    // 20%: Health check
    const res = http.get(`${BASE_URL}/health`);
    const success = check(res, {
      'health status is 200': (r) => r.status === 200,
    });
    errorRate.add(!success);

  } else if (scenario < 0.8) {
    // 20%: List URLs
    const page = Math.floor(Math.random() * 10) + 1;
    const res = http.get(`${BASE_URL}/urls?page=${page}&per_page=10`);
    const success = check(res, {
      'list status is 200': (r) => r.status === 200,
    });
    errorRate.add(!success);

  } else if (scenario < 0.95) {
    // 15%: List users
    const res = http.get(`${BASE_URL}/users?per_page=10`);
    const success = check(res, {
      'users status is 200': (r) => r.status === 200,
    });
    errorRate.add(!success);

  } else {
    // 5%: Create a short URL
    const url = TEST_URLS[Math.floor(Math.random() * TEST_URLS.length)];
    const payload = JSON.stringify({ url: url, user_id: 1 });
    const params = { headers: { 'Content-Type': 'application/json' } };
    const res = http.post(`${BASE_URL}/shorten`, payload, params);
    const success = check(res, {
      'shorten status is 201': (r) => r.status === 201,
    });
    errorRate.add(!success);
  }

  sleep(0.1);
}
