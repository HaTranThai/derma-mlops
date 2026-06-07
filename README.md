# Skin Lesion MLOps

Hệ thống MLOps phân loại tổn thương da từ ảnh dermoscopy (HAM10000). Kế hoạch chi tiết: [docs/plan.md](docs/plan.md).

## Trạng thái

- ✅ **Phase 0** — Scaffold repo + Docker Compose
- ✅ **Phase 1** — Serving slice: FastAPI `/predict` + Grad-CAM + Next.js
- ✅ **Phase 2** — Lưu trữ: PostgreSQL (prediction log) + MinIO (ảnh) + trang Lịch sử
- ✅ **Phase 3** — Monitoring: Prometheus + Grafana + drift detection + review queue + scripts streaming
- ✅ **Phase 5** — MLflow registry + **Prefect orchestration (server + worker, service riêng)** + retraining flow + promote gate + trang Admin (control plane) + **DVC** (version model artifact → MinIO remote `dvc-store`; version bộ ảnh HAM10000 chạy ở môi trường có dữ liệu).
- ⬜ Phase 4 — Kafka streaming
- ⬜ Phase 6 — Test + CI

## Chạy (Phase 1)

1. Tải model `model_efficientnet_b0_v2.pt` từ Kaggle về `models/production/` (xem `models/production/README.md`).
2. Build & chạy (chạy từ thư mục `code/`):

```bash
cd code
docker compose up --build
```

3. Truy cập:
   - **Web (Next.js — giao diện chính)**: http://localhost:3100 (Dự đoán · Lịch sử · Cần review · Giám sát)
   - API docs (Swagger): http://localhost:8200/docs
   - **Trang Admin** (control plane): http://localhost:3100/admin (token: `admin-secret`)
   - **Grafana**: http://localhost:3001 (anonymous viewer, admin/admin)
   - **MLflow** (registry + tracking): http://localhost:5000
   - **Prefect** (orchestration UI): http://localhost:4200
   - Prometheus: http://localhost:9090
   - MinIO Console: http://localhost:9001 (user/pass: `minioadmin`)
   - PostgreSQL: `localhost:5434` (user `skin` / pass `skin_pass` / db `skinlesion`)

> Cổng host API là **8200** (cổng 8000 trên máy dev đang bị dự án khác chiếm). Web gọi API qua proxy nội bộ (`/api/*` → `http://api:8000`). Ảnh hiển thị qua **proxy** `/api/img/{id}` (browser → frontend → api → MinIO) — không cần truy cập trực tiếp cổng MinIO, chạy được cả khi port-forwarding từ xa.

## Services (docker-compose)

| Service | Cổng host | Vai trò |
|---|---|---|
| `frontend` | 3100 | Next.js — giao diện chính |
| `api` | 8200 | FastAPI backend |
| `postgres` | 5434 | Prediction log + review |
| `minio` | 9000 / 9001 | Object storage (ảnh) + console |
| `prometheus` | 9090 | Thu thập metrics |
| `grafana` | 3001 | Dashboard giám sát |
| `mlflow` | 5000 | Tracking + Model Registry |
| `prefect-server` | 4200 | Prefect orchestration (UI + API) |
| `prefect-worker` | — | Chạy retraining flow (env cô lập) |

## API

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/health` | Trạng thái + model version |
| POST | `/predict?source=` | Upload ảnh → dự đoán + Grad-CAM; lưu ảnh MinIO + log Postgres + tính drift |
| GET | `/predictions` | Lịch sử dự đoán (phân trang) + presigned URL ảnh |
| GET | `/predictions/{id}` | Chi tiết 1 dự đoán |
| GET | `/predictions/{id}/image` | Stream ảnh gốc từ MinIO |
| GET | `/reviews/queue` | Hàng chờ review (ảnh confidence thấp chưa review) |
| POST | `/reviews` | Gửi nhãn xác nhận cho 1 prediction |
| GET | `/reviews` | Danh sách đã review |
| GET | `/monitoring/stats` | Thống kê tổng hợp (cửa sổ gần nhất) |
| GET | `/metrics` | Metrics định dạng Prometheus |

**Admin (cần header `X-Admin-Token`):**

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/admin/seed-models` | Đăng ký v1/v2 vào MLflow registry (v1 Production, v2 Staging) |
| GET | `/admin/models` | Danh sách model version + stage + metrics |
| GET | `/admin/gate` | Preview promote gate (production vs candidate) |
| POST | `/admin/retrain` | Chạy retraining flow (gate → promote) |
| POST | `/admin/promote/{version}` | Promote 1 version thủ công |
| GET / PUT | `/admin/config` | Xem / sửa tham số retrain (gồm `auto_trigger_enabled`) |
| POST | `/admin/reload-model` | Hot-reload model đang phục vụ (không restart) |
| GET | `/admin/trigger-status` | Đánh giá live 4 tín hiệu trigger S1–S4 |
| GET | `/admin/runs` | Lịch sử các lần retrain |

> **Auto-trigger (4 tín hiệu)** — 4 tín hiệu OR, chạy ở 2 nơi khác nhau:
> - **S1/S2/S3 (event-driven)** — background loop trong **api** (bật bằng `auto_trigger_enabled`) đánh giá định kỳ: **S1** đủ review mới (`min_reviewed_images`), **S2** drift/confidence thấp (`drift_rate`/`low_confidence_rate`), **S3** hiệu năng online giảm (accuracy dự đoán vs nhãn bác sĩ < `perf_min_accuracy`) — kèm guard `cooldown_minutes`. Tín hiệu bật → gọi retrain qua Prefect.
> - **S4 (định kỳ)** — **lịch Prefect cron** (`schedule_cron`, mặc định `0 2 1 * *`) do `prefect-server` tự bắn, `prefect-worker` chạy. KHÔNG nằm trong api loop. Đổi lịch trong config → restart `prefect-worker` để đăng ký lại.
>
> `trigger_reason` ghi rõ tín hiệu nào kích hoạt (vd `S1+S2+S3`, hoặc `S4` cho run theo lịch). Xem S1–S3 live bằng `/admin/trigger-status` hoặc panel "Tín hiệu trigger" trên trang Admin. Worker luôn thực thi gate+promote. Đây là retraining **event-driven + scheduled** (Level 2).

## DVC (data/model versioning → MinIO)

DVC đã init tại repo, remote = MinIO bucket `dvc-store`. Dùng venv `.venv` (đã cài `dvc[s3]`):

```bash
.venv/bin/dvc add models/production/model_efficientnet_b0_v2.pt   # version artifact
.venv/bin/dvc push        # đẩy lên MinIO
.venv/bin/dvc pull        # kéo về (tái lập)
.venv/bin/dvc status -c   # so với remote
```

File `*.dvc` (con trỏ md5) được git track; binary lưu trên MinIO. Secret remote ở `.dvc/config.local` (gitignored). Version bộ ảnh HAM10000 dùng cùng cơ chế, chạy ở môi trường có dataset.

## Scripts (mô phỏng streaming & drift)

```bash
# Tạo ảnh drift (tối/mờ/nhiễu) từ thư mục ảnh sạch
python code/scripts/create_drift_data.py --input <thư-mục-ảnh> --output drift_data --types dark,blur,noise

# Gửi liên tục ảnh vào /predict (mô phỏng streaming)
python code/scripts/simulate_stream.py --dir <thư-mục-ảnh> --api http://localhost:8200 --delay 0.3
```

## Cấu trúc

Source code nằm trong `code/`, tách thành **backend** và **frontend** riêng; tài liệu, notebook và model artifact để ngoài.

```
headloader/
├── code/
│   ├── backend/                # FastAPI service
│   │   ├── app/
│   │   │   ├── api/            # main (lifespan), schemas, routers/ (health, predict, predictions, reviews, monitoring)
│   │   │   ├── services/       # model, gradcam, storage (MinIO), drift
│   │   │   ├── repositories/   # prediction, review, monitoring (Postgres)
│   │   │   ├── db/             # database (pool), schema.sql, init_db
│   │   │   └── core/           # config, metrics (Prometheus)
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── frontend/               # Next.js + React + Tailwind
│   │   ├── app/                # page (Dự đoán), history/, review/, monitoring/, api/ (proxy)
│   │   ├── Dockerfile
│   │   └── package.json
│   ├── monitoring/             # prometheus.yml + grafana provisioning & dashboard
│   ├── scripts/                # simulate_stream.py, create_drift_data.py
│   └── docker-compose.yml
├── docs/                       # plan.md, đề cương
├── notebooks/                  # 01_train_models.ipynb
├── models/production/          # model .pt (gitignored)
└── README.md
```

