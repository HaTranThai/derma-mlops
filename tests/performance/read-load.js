import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    reads: { executor: "constant-vus", vus: 20, duration: "30s" },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{endpoint:monitoring}": ["p(95)<500"],
    "http_req_duration{endpoint:predictions}": ["p(95)<500"],
  },
};

const ENDPOINTS = [
  ["http://api:8000/monitoring/stats", "monitoring"],
  ["http://api:8000/predictions?limit=20", "predictions"],
  ["http://api:8000/health", "health"],
];

export default function () {
  for (const [url, tag] of ENDPOINTS) {
    const res = http.get(url, { tags: { endpoint: tag } });
    check(res, { "status is 200": (r) => r.status === 200 });
  }
}
