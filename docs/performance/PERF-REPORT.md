# Performance Test Report — Skin Lesion MLOps

> Báo cáo đo hiệu năng bằng **k6**. Viết trung thực: nêu rõ điều kiện đo, số thật, và phân tích điểm nghẽn. Hệ chạy **CPU (không GPU)** nên kết quả phản ánh đúng giới hạn đó.

## 1. Điều kiện đo (conditions)
| Mục | Giá trị |
|---|---|
| Môi trường | Local dev (Docker Compose), **CPU 16 nhân / 11GB RAM** (~6.8GB trống) |
| GPU | **Không** (inference chạy CPU) |
| Serving | FastAPI 1 uvicorn worker; model CNN (`.pt`) nạp trong RAM, tải từ MinIO bucket `models` (model là thành phần thay thế được) |
| Công cụ | k6 (container `grafana/k6`), gọi `api:8000` trong network `code_default` |
| Dataset | predictions đang có + ảnh upload lặp trong test |
| Ngày đo | 2026-06-08 |

> Lưu ý: đây là môi trường **dev**, không phải staging cấu hình production. Số tuyệt đối chỉ mang tính tham chiếu; quan trọng là **xu hướng + điểm nghẽn**.

## 2. Kịch bản & kết quả

### 2.1. Endpoint ĐỌC (read-load.js) — 20 VUs, 30s
`GET /monitoring/stats`, `GET /predictions?limit=20`, `GET /health`.

| Chỉ số | Kết quả | Mục tiêu | Đạt? |
|---|---|---|---|
| `/monitoring/stats` P95 | **87.5 ms** | < 500 ms | ✅ |
| `/predictions` P95 | **125.8 ms** | < 500 ms | ✅ |
| Error rate | **0.00%** | < 1% | ✅ |
| Throughput | ~**321 req/s** (≈107 iter/s × 3) | — | — |
| Iterations | 3.201 / 30s | — | — |

→ **Tầng đọc (DB async + pool) scale tốt** ở 20 người dùng đồng thời, P95 thấp, không lỗi.

### 2.2. Endpoint /predict (predict-load.js) — ramp 1→4→8 VUs, 50s
`POST /predict` (upload ảnh → inference CPU + Grad-CAM + upload MinIO + ghi Postgres + drift).

| Chỉ số | Kết quả |
|---|---|
| Latency **1 request** (min, không tải) | **300 ms** |
| Median (dưới tải) | 1.46 s |
| **P95** (tới 8 VUs) | **3.19 s** |
| P90 | 2.5 s |
| Max | 7.95 s |
| Throughput | **2.66 req/s** |
| Error rate | **0.00%** (không crash/OOM) |

## 3. Phân tích — điểm nghẽn (quan trọng)

**Phát hiện chính: `/predict` KHÔNG scale theo số người dùng đồng thời — các request inference bị xếp hàng tuần tự.**

- Baseline 1 request = **~300ms** (chấp nhận được cho inference ảnh trên CPU).
- Khi tăng lên 8 VUs: throughput **không tăng** (chỉ ~2.66 req/s ≈ 1/0.37s), còn P95 **phình lên 3.19s** (≈ 8 × thời gian 1 inference). Đây là dấu hiệu kinh điển của **xếp hàng do tuần tự hóa**.

**Nguyên nhân gốc:**
1. Endpoint `async def predict` nhưng gọi **inference torch đồng bộ** → **block event loop** → request nối đuôi nhau.
2. Chỉ **1 uvicorn worker** → không có song song đa tiến trình.
3. CPU inference vốn chậm hơn GPU nhiều lần.

## 4. Đánh giá NFR

| NFR | Mục tiêu (tham chiếu) | Đo được | Kết luận |
|---|---|---|---|
| Read API P95 (20 users) | < 500 ms | 88–126 ms | ✅ Đạt |
| /predict P95 (8 users) | < 3000 ms | 3190 ms | ❌ Không đạt (do tuần tự hóa) |
| /predict 1 user | — | 300 ms | ✅ Hợp lý cho CPU |
| Ổn định dưới tải | không crash/OOM | 0% lỗi | ✅ Đạt |

## 5. Khuyến nghị cải thiện (theo thứ tự hiệu quả)

1. **Bỏ block event loop**: chuyển inference sang threadpool (`def` thay `async def`, hoặc `run_in_threadpool`) — torch nhả GIL khi tính nên threadpool giúp song song một phần. *Rẻ nhất, làm ngay được.*
2. **Nhiều uvicorn worker** (`--workers N`) → song song đa tiến trình (mỗi worker 1 bản model trong RAM; cân nhắc RAM).
3. **GPU** cho inference → giảm mạnh latency/inference.
4. **Tách model server** (TorchServe/Triton) + **batch inference** → throughput cao, serving stateless tách khỏi API.
5. **Hàng đợi bất đồng bộ** (đúng hướng Kafka đã nêu): /predict nhận → đẩy job → worker inference → tách tải.

## 6. Kết luận trung thực
- **Tầng đọc/monitoring: đạt** (nhanh, ổn định ở 20 users).
- **Tầng /predict: 1 user ổn (~300ms), nhưng không scale** khi đồng thời do inference đồng bộ + 1 worker + CPU. **Không crash** (graceful).
- Đây là giới hạn **kiến trúc serving + phần cứng**, không phải lỗi logic. Có lộ trình cải thiện rõ ràng (mục 5). Với đồ án trọng tâm **kiến trúc MLOps**, đây là kết quả NFR đo lường được + phân tích + hướng tối ưu — đủ và trung thực.

## Phụ lục — chạy lại
```bash
cd /home/bbsw/headloader
docker run --rm --network code_default \
  -v "$PWD/tests/performance:/scripts" -v "$PWD/demo:/imgs" \
  grafana/k6 run /scripts/read-load.js      # tầng đọc
docker run --rm --network code_default \
  -v "$PWD/tests/performance:/scripts" -v "$PWD/demo:/imgs" \
  grafana/k6 run /scripts/predict-load.js   # /predict
```
