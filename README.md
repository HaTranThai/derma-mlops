# Skin Lesion MLOps

Hệ thống MLOps phân loại tổn thương da từ ảnh dermoscopy (HAM10000). Kế hoạch chi tiết: [docs/plan.md](docs/plan.md) · Kiến trúc: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Trạng thái

- ✅ **Phase 0** — Scaffold repo + Docker Compose
- ✅ **Phase 1** — Serving slice: FastAPI `/predict` + Grad-CAM + Next.js
- ✅ **Phase 2** — Lưu trữ: PostgreSQL (prediction log) + MinIO (ảnh) + trang Lịch sử
- ✅ **Phase 3** — Monitoring: Prometheus + Grafana + drift detection + review queue + scripts streaming
- ✅ **Phase 4** — Kafka (KRaft): `/predict` bắn event `prediction-events` → **2 consumer khác group (fan-out)**: `prediction-logger` ghi DB async, `drift-monitor` cảnh báo drift real-time. Có fallback ghi thẳng khi Kafka down
- ✅ **Phase 5** — MLflow registry (backend **PostgreSQL**) + **Prefect orchestration (server + worker)** + retraining flow + promote gate + trang Admin (control plane) + **DVC** (version **data** `data/subset` → MinIO remote `dvc-store`).
- ✅ **Phase 6** — Test (pytest: unit logic gate/drift/config/PSI + 4 tín hiệu trigger + kafka producer + **integration API** qua TestClient) + **coverage** (pytest-cov, floor 25%) + CI (GitHub Actions). *e2e full-stack + module inference (torch) chưa phủ — cần môi trường có stack.*
- ✅ **Phase 7** — **Serving model từ MinIO** (bucket `models`, không còn file local) + **active-learning ingest** (review→`data/subset`+dvc, có leak-guard md5 vs val/test) + **retrain warm-start** từ Production + luôn gom ảnh review + **gate siết**: re-eval Production trên `data/val` (so cùng nguồn) + sàn `mel_recall ≥ 0.40` + biên `macro_f1 0.005`.

> **Hardening đã làm thêm:** MLflow backend chuyển **SQLite → PostgreSQL** (bỏ SPOF); monitoring thêm **drift thống kê PSI** (`population_drift_psi`) bên cạnh heuristic chất lượng ảnh; **secrets externalize** ra `code/.env` (xem `.env.example` + [docs/SECURITY.md](docs/SECURITY.md)); giới hạn cỡ ảnh upload (`MAX_UPLOAD_BYTES`).

## Chạy

1. Build & chạy (từ thư mục `code/`):

```bash
cd code
docker compose up --build
```

2. **Nạp model Production** (hệ thống serving model **từ MinIO** bucket `models`, không đọc file local):
   - Train bằng [notebooks/01_train_models.ipynb](notebooks/01_train_models.ipynb) (Kaggle/GPU) → ra `production.pt` (đúng format checkpoint).
   - Đăng ký vào MLflow → tự push lên MinIO `models/production/model.pt` + set Production (qua script đăng ký, xem `docs/giai-thich-he-thong-mlops.md`).
   - Hoặc dùng `POST /admin/seed-models` để seed model demo (metric mẫu) khi mới dựng.
   - API tự tải model Production từ MinIO lúc startup; đổi model → `POST /admin/reload-model`.

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
| `mlflow` | 5000 | Tracking + Model Registry (backend PostgreSQL, artifacts MinIO) |
| `prefect-server` | 4200 | Prefect orchestration (UI + API) |
| `prefect-worker` | — | Chạy retraining flow (env cô lập) |
| `kafka` | — | Message broker (KRaft) — topic `prediction-events` |
| `consumer` | — | Group `prediction-logger`: đọc Kafka → ghi prediction vào Postgres (async) |
| `alert-consumer` | — | Group `drift-monitor`: đọc cùng topic → cảnh báo drift real-time (fan-out) |

## API

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/health` | Trạng thái + model version |
| POST | `/predict?source=` | Upload ảnh → dự đoán + Grad-CAM; lưu ảnh MinIO + log Postgres + tính drift |
| GET | `/predictions` | Lịch sử dự đoán (phân trang) + URL ảnh (proxy `/api/img/{id}`) |
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
| POST | `/admin/retrain` | Chạy retraining flow (warm-start → re-eval → gate → promote) |
| POST | `/admin/promote/{version}` | Promote 1 version thủ công (sync model → MinIO `models`) |
| POST | `/admin/ingest-reviews` | **Active-learning**: đưa ảnh đã review vào `data/subset` + `dvc add/push` (leak-guard) |
| POST | `/admin/eval-production-val` | Chấm model Production trên `data/val` (cập nhật metric registry) |
| GET / PUT | `/admin/config` | Xem / sửa tham số retrain (gồm `auto_trigger_enabled`, `promote_rules`) |
| POST | `/admin/reload-model` | Hot-reload model từ MinIO (không restart); nhận `model_path`/`model_key` |
| GET | `/admin/trigger-status` | Đánh giá live 4 tín hiệu trigger S1–S4 |
| GET | `/admin/runs` | Lịch sử các lần retrain (kèm `detail` gate) |

> **Auto-trigger (4 tín hiệu)** — 4 tín hiệu OR, chạy ở 2 nơi khác nhau:
> - **S1/S2/S3 (event-driven)** — background loop trong **api** (bật bằng `auto_trigger_enabled`) đánh giá định kỳ: **S1** đủ review mới (`min_reviewed_images`), **S2** drift/confidence thấp (`drift_rate`/`low_confidence_rate`), **S3** hiệu năng online giảm (accuracy dự đoán vs nhãn bác sĩ < `perf_min_accuracy`) — kèm guard `cooldown_minutes`. Tín hiệu bật → gọi retrain qua Prefect.
> - **S4 (định kỳ)** — **lịch Prefect cron** (`schedule_cron`, mặc định `0 2 1 * *`) do `prefect-server` tự bắn, `prefect-worker` chạy. KHÔNG nằm trong api loop. Đổi lịch trong config → restart `prefect-worker` để đăng ký lại.
>
> `trigger_reason` ghi rõ tín hiệu nào kích hoạt (vd `S1+S2+S3`, hoặc `S4` cho run theo lịch). Xem S1–S3 live bằng `/admin/trigger-status` hoặc panel "Tín hiệu trigger" trên trang Admin. Worker luôn thực thi gate+promote. Đây là retraining **event-driven + scheduled** (Level 2).

## DVC (data versioning → MinIO)

DVC version **DỮ LIỆU** `data/subset` (tập train), remote = MinIO bucket `dvc-store`. **Model KHÔNG đi qua DVC** (model nằm ở bucket `models` + `mlflow`). 2 remote: `minio` (host, `localhost:9000`) và `minio_internal` (container, `minio:9000`); `core.no_scm=true` để chạy không cần git.

```bash
# Trên host (.venv đã cài dvc[s3]):
.venv/bin/dvc add data/subset    # version tập train (md5)
.venv/bin/dvc push               # đẩy lên MinIO (bucket dvc-store)
.venv/bin/dvc pull               # kéo về (tái lập trên máy khác)
```

File `data/subset.dvc` (con trỏ md5) được git track; ảnh lưu trên MinIO. Secret remote ở `.dvc/config.local` (gitignored). **Nút Admin "Đưa review vào tập train"** chạy `dvc add/push` **tự động ngay trong container api** (qua remote `minio_internal`) sau khi đưa ảnh review vào `data/subset` — đây là vòng active-learning. Worker đọc `data/subset` (mount) cho retrain; chỉnh `subset_per_class` trong config để train ít/full.

## Test

```bash
# Chạy trong image api (đã có sẵn dependencies)
cd code
docker compose run --rm --no-deps -v "$PWD/backend:/test" -w /test api \
  sh -c "pip install -q pytest==8.2.0 && pytest"

# Hoặc local (cài requirements-dev.txt)
cd code/backend && pip install -r requirements-dev.txt && pytest
```
**34 test** + coverage (pytest-cov):
- **Unit logic**: promote gate · drift scoring · config schema · population drift (PSI) · 4 tín hiệu trigger S1–S3 + cooldown · kafka producer (mock).
- **Integration (TestClient)**: `/health`, `/reviews/queue`, `/monitoring/stats`, `POST /reviews` (validate) — mock repo, không cần DB/torch.
- Coverage ~29% (floor 25% trong `pytest.ini`); module inference torch (`model`/`gradcam`/`trainer`) + glue (`storage`/`consumer`/`flows`) phủ 0% (cần e2e full-stack).

CI tự chạy qua `.github/workflows/ci.yml` (backend pytest+coverage + frontend build).

> **CI có / CD chưa:** CI (test + build mỗi push/PR) đã hoạt động — đã verify pass ở môi trường sạch (`python:3.11`, `node:20`). **CD (deploy tự động) = hướng phát triển** (sẽ thêm job build+push image ghcr.io / deploy SSH lên VPS sau).

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
│   ├── backend/                # FastAPI service (api + consumer dùng chung image)
│   │   ├── app/
│   │   │   ├── api/            # main (lifespan), schemas, routers/ (health, predict, predictions, reviews, monitoring, admin)
│   │   │   ├── services/       # model_service, model_store (MinIO models bucket), gradcam, storage, drift, mlflow, retrain, trainer, ingest, prefect_trigger, auto_trigger, kafka
│   │   │   ├── repositories/   # prediction, review, monitoring, config, run (Postgres)
│   │   │   ├── flows/          # Prefect: retraining_flow + serve (worker)
│   │   │   ├── consumer/       # Kafka consumer: prediction_consumer, drift_alert_consumer
│   │   │   ├── db/             # database (pool), schema.sql, init_db
│   │   │   └── core/           # config, metrics (Prometheus)
│   │   ├── tests/              # pytest (gate, drift, config, PSI)
│   │   ├── Dockerfile · requirements.txt · requirements-dev.txt
│   ├── frontend/               # Next.js + React + Tailwind
│   │   └── app/                # page (Dự đoán), history/, review/, monitoring/, admin/, api/ (proxy)
│   ├── monitoring/             # prometheus.yml + grafana provisioning & dashboard
│   ├── mlflow/ · prefect/ · postgres/init/   # Dockerfile/entrypoint/init SQL từng service
│   ├── scripts/                # simulate_stream.py, create_drift_data.py
│   ├── .env.example            # mẫu secrets (code/.env gitignored)
│   └── docker-compose.yml      # 12 service
├── docs/                       # plan.md, ARCHITECTURE.md, đề cương, SECURITY.md, giai-thich-he-thong-mlops.md, performance/
├── notebooks/                  # 01_train_models.ipynb (+ _build_notebook.py)
├── tests/performance/          # k6 load test (read-load.js, predict-load.js)
├── data/                       # subset.dvc/val.dvc/test.dvc (DVC pointer); ảnh gitignored
├── models/                     # folder thả .pt để đăng ký (model thật lưu ở MinIO bucket "models", không ở đây)
├── .github/workflows/          # ci.yml (backend pytest + frontend build)
└── README.md
```

