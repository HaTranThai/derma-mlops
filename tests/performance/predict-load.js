import http from "k6/http";
import { check } from "k6";

// Tải ảnh mẫu 1 lần (binary) để upload multipart vào /predict.
const img = open("/imgs/akiec__ISIC_0024843.jpg", "b");

export const options = {
  stages: [
    { duration: "20s", target: 4 },
    { duration: "20s", target: 8 },
    { duration: "10s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
    // Mục tiêu THAM KHẢO cho serving CPU (không GPU). Report số thật bất kể đạt/không.
    http_req_duration: ["p(95)<3000"],
  },
};

export default function () {
  const res = http.post("http://api:8000/predict", {
    file: http.file(img, "sample.jpg", "image/jpeg"),
  });
  check(res, { "status is 200": (r) => r.status === 200 });
}
