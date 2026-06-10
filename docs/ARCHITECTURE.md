# Kiến trúc hệ thống — Skin Lesion MLOps

> Tài liệu kiến trúc để đưa vào báo cáo đồ án. Mọi thành phần/port/luồng đều bám đúng hệ thống đang chạy (`docker compose`, 12 service). Bổ trợ: [README](../README.md) (chạy/cấu trúc), [plan.md](plan.md) (kế hoạch), [giai-thich-he-thong-mlops.md](giai-thich-he-thong-mlops.md) (cơ chế DVC/Prefect/MLflow), [SECURITY.md](SECURITY.md), [performance/PERF-REPORT.md](performance/PERF-REPORT.md).

## 1. Tổng quan

Hệ thống MLOps phân loại tổn thương da từ ảnh dermoscopy (HAM10000). Trọng tâm là **kiến trúc vòng đời ML** (data versioning → serving → monitoring → registry → orchestration → retraining), mô hình học sâu chỉ là một thành phần thay thế được. Tự định vị **MLOps Maturity Level 1 đầy đủ + hiện thực cơ chế Level 2** (retraining tự động hướng sự kiện + theo lịch, promote gate).

**Nguyên tắc thiết kế:** tách trách nhiệm rõ (serving / lưu trữ / điều phối / quản model), hướng sự kiện (Kafka), đóng gói container (Docker Compose), mọi tham số cấu hình được (DB `system_config` + `.env`).

## 2. Sơ đồ kiến trúc tổng (12 service)

```
                                   TRÌNH DUYỆT (người dùng · bác sĩ · admin)
                                              │ http://localhost:3100
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  frontend (Next.js)  :3100      Dự đoán · Lịch sử · Cần review · Giám sát · Admin        │
│  /api/* = proxy route handler ─────────────────────────────────────────┐ (server-side) │
└─────────────────────────────────────────────────────────────────────────┼─────────────┘
                                                                            ▼ http://api:8000
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  api (FastAPI)  :8200→8000                                                              │
│  routers: health · predict · predictions · reviews · monitoring · admin                 │
│  services: model · gradcam · storage · drift · mlflow · retrain · prefect_trigger ·     │
│            auto_trigger(S1–S3 loop) · kafka(producer)                                    │
│  model .pt nạp trong RAM (app.state)                                                     │
└──┬──────────┬───────────┬──────────────┬──────────────┬───────────────┬────────────────┘
   │SQL       │S3 object  │/metrics      │event publish │REST trigger    │REST registry/gate
   ▼          ▼           ▼(scrape)      ▼              ▼                ▼
┌────────┐ ┌────────┐ ┌──────────┐  ┌─────────┐  ┌──────────────┐  ┌──────────────────┐
│postgres│ │ minio  │ │prometheus│  │  kafka  │  │prefect-server│  │ mlflow           │
│ :5434  │ │9000/01 │ │  :9090   │  │ (KRaft) │  │   :4200      │  │  :5000           │
│        │ │buckets:│ │scrape api│  │ topic:  │  │ • UI/API     │  │ • tracking       │
│ tables:│ │•predict│ └────┬─────┘  │predicti-│  │ • CRON S4 ──┐│  │ • Model Registry │
│predicti│ │•mlflow │      │query   │on-events│  │   bắn lịch  ││  │ backend: postgres│
│ons     │ │•dvc-   │      ▼        └────┬────┘  └─────┬───────┼┘  │ artifacts: minio │
│reviews │ │ store  │ ┌──────────┐       │fan-out      │ pickup │   └────────▲─────────┘
│system_ │ └───┬────┘ │ grafana  │   ┌───┴────┐       ▼        ▼            │
│config  │     │      │  :3001   │   ▼        ▼  ┌────────────────────┐    │
│retrmain│     │      │dashboard │ consumer  alert- │  prefect-worker     │    │
│ing_runs│     │      └──────────┘ (logger)  consumer│  retraining_flow   │────┘
│ + DB   │     │                     │       (drift) │  → gate → promote   │ gate/promote
│ mlflow │     │ ảnh+artifact         │ ghi DB │ ALERT │  (đọc DB+MLflow)    │
└───▲────┘     │                     ▼        ▼       └─────────────────────┘
    │          │              postgres    (log cảnh báo)
    └──────────┴── consumer ghi prediction ─┘
                                                
   DVC (.venv/bin/dvc)  ──push/pull (model .pt + data/subset)──►  minio bucket "dvc-store"
```

**Cổng host:** frontend 3100 · api 8200 · postgres 5434 · minio 9000/9001 · prometheus 9090 · grafana 3001 · mlflow 5000 · prefect-server 4200. (kafka, consumer, alert-consumer, prefect-worker: không expose cổng.)

## 3. Trách nhiệm từng thành phần

| Service | Trách nhiệm | Trục |
|---|---|---|
| `frontend` | UI Next.js + proxy `/api/*` (không CORS, ẩn URL API) | giao diện |
| `api` | Serving `/predict` + Grad-CAM; REST admin; đánh giá tín hiệu S1–S3; producer Kafka | serving + control |
| `postgres` | `predictions/reviews/system_config/retraining_runs` + **MLflow backend store** | trạng thái bền |
| `minio` | Object storage: ảnh prediction · DVC remote · MLflow artifacts | lưu file |
| `kafka` | Message broker (KRaft) — topic `prediction-events` | đường ống sự kiện |
| `consumer` | Group `prediction-logger`: event → ghi `predictions` (async) | logging |
| `alert-consumer` | Group `drift-monitor`: event → cảnh báo drift real-time (fan-out) | monitoring |
| `mlflow` | Tracking + Model Registry + promote gate (backend Postgres) | quản model |
| `prefect-server` | Orchestration: UI/API + lịch cron (tín hiệu S4) | điều phối (lịch) |
| `prefect-worker` | Thực thi `retraining_flow` → gate → promote; smoke train thật | điều phối (chạy) |
| `prometheus` | Thu thập metrics (scrape `api:/metrics`) | giám sát |
| `grafana` | Dashboard giám sát | giám sát |

## 4. Mô hình dữ liệu (ERD)

Database `skinlesion` (app) — 4 bảng:

```
┌─────────────────────────────┐         ┌──────────────────────────────┐
│ predictions                 │ 1     1 │ reviews                      │
├─────────────────────────────┤◄────────┤──────────────────────────────┤
│ PK id            BIGSERIAL  │         │ PK id              BIGSERIAL  │
│ UQ prediction_id VARCHAR(40)│─────────│ FK,UQ prediction_id VARCHAR  │
│    created_at    TIMESTAMPTZ│         │    review_label    VARCHAR(16)│
│    image_key     VARCHAR    │         │    review_status   VARCHAR(16)│ pending|reviewed
│    image_width/height  INT  │         │    reviewer        VARCHAR(64)│
│    predicted_class VARCHAR  │         │    reviewed_at     TIMESTAMPTZ│
│    confidence    REAL        │         │    created_at      TIMESTAMPTZ│
│    top_k         JSONB       │         │    used_in_data_version VARCHAR│
│    latency_ms    INT         │         └──────────────────────────────┘
│    model_version VARCHAR(64) │
│    data_version  VARCHAR(32) │  ← hash DVC khi model train trong hệ thống
│    is_low_confidence  BOOL   │
│    is_drift_suspected BOOL   │  ← drift heuristic (brightness/blur)
│    brightness/blur_score REAL│
│    source        VARCHAR(16) │  web|stream
│    correlation_id VARCHAR(64)│
└─────────────────────────────┘

┌─────────────────────────────┐         ┌──────────────────────────────┐
│ system_config               │         │ retraining_runs              │
├─────────────────────────────┤         ├──────────────────────────────┤
│ PK key    VARCHAR(64)       │         │ PK id            BIGSERIAL    │
│    value  JSONB             │         │    triggered_at  TIMESTAMPTZ  │
│    updated_at TIMESTAMPTZ   │         │    trigger_reason VARCHAR(16) │ S1+S2+S3 | S4 | manual
│    updated_by VARCHAR(64)   │         │    mode          VARCHAR(16)  │ artifact | smoke
└─────────────────────────────┘         │    reviewed_count INT         │
  key='retrain_config' (JSONB:          │    production_tag/candidate_tag│
  mode, trigger S1–S4, smoke,           │    gate_passed   BOOL         │
  promote_rules, schedule_cron…)        │    promoted      BOOL         │
                                        │    detail        JSONB        │
                                        └──────────────────────────────┘
```

- **predictions 1—1 reviews**: mỗi prediction có tối đa 1 review (FK + UNIQUE). Bảng tách: predictions bất biến (log), reviews là annotation của bác sĩ.
- **Quan hệ logic (không FK cứng)**: `model_version`/`data_version` ↔ MLflow registry + DVC hash (governance).

Database `mlflow` (Postgres riêng) — do MLflow tự quản: `experiments`, `runs`, `registered_models`, `model_versions`, `model_version_tags`… (registry + tracking).

## 5. Sequence — Dự đoán (event-driven qua Kafka)

```
BR        FE(proxy)     api               MinIO     Kafka        consumer   alert-consumer  PG
 │ POST /api/predict     │                 │         │             │            │           │
 │──(ảnh)──►│ POST /predict                │         │             │            │           │
 │          │──(ảnh)────►│                 │         │             │            │           │
 │          │            │ model→top-k; Grad-CAM; drift            │            │           │
 │          │            │ upload ảnh ────►│         │             │            │           │
 │          │            │ publish event ──────────►│ (topic)     │            │           │
 │          │  200 JSON   │ (top-k+gradcam) │         │             │            │           │
 │◄─────────│◄───────────│ TRẢ NGAY        │         │ fan-out ────┼───────────►│           │
 │          │            │                 │         │             │ insert ───────────────►│
 │          │            │                 │         │             │            │ tính rate │
 │          │            │                 │         │             │            │ >ngưỡng→ALERT
 │  (Kafka down → api ghi thẳng PG: fallback)                     │            │           │
```

## 6. Sequence — Retraining (Prefect → gate → promote)

```
[trigger]              prefect-server   prefect-worker         PG       MLflow
 S1/S2/S3 (api loop) ──create_flow_run─►│                      │         │
 Admin "Retrain Now" ──/admin/retrain──►│                      │         │
 S4 (cron 0 2 1 * *) ──tự lên lịch──────►│ tạo flow run         │         │
                                         │──pickup────────────►│         │
                                         │      retrain_service.run(reason)│
                                         │      mode=smoke → trainer.py train thật (subset)
                                         │           └─ log+register version Staging ─────►│
                                         │      đọc config/reviews ◄──────│         │
                                         │      lấy production+candidate ─────────────────►│
                                         │      PROMOTE GATE (macro_f1/mel_recall/accuracy)│
                                         │      đạt → promote → stage ────────────────────►│
                                         │      ghi retraining_runs ─────►│         │
                                         │  run COMPLETED      │         │         │
 Admin: /admin/reload-model → api nạp lại .pt (không restart)
```

> Triết lý 2 tầng: **TRIGGER** (có nên thử) tách **PROMOTE GATE** (có đủ tốt để thay). Trigger rộng tay cũng an toàn vì gate luôn chặn model kém.

## 7. Sequence — Rollback data version (DVC)

```
①  git checkout <commit-cũ> -- data/subset.dvc      (lấy cuống vé v1)
②  dvc checkout / dvc pull  → DVC đọc hash → dựng lại ảnh v1 lên đĩa (từ cache/MinIO)
③  trigger retrain          → worker đọc /app/data/subset (đang là v1) → train v1
```
DVC (không phải Prefect) kéo data từ MinIO theo con trỏ; Prefect chỉ chạy code sau khi data đã có trên đĩa.

## 8. Luồng tín hiệu retraining (S1–S4)

| Mã | Tín hiệu | Service đánh giá | Nguồn dữ liệu |
|---|---|---|---|
| S1 | đủ review mới | `api` (loop) | `reviews` (đếm từ lần retrain) |
| S2 | drift / confidence thấp | `api` (loop) | `predictions` (cờ drift/low-conf) |
| S3 | hiệu năng online giảm | `api` (loop) | `reviews`+`predictions` (accuracy) |
| S4 | định kỳ | `prefect-server` (cron) | lịch `schedule_cron` |

S1–S3 event-driven (api → gọi Prefect REST); S4 = Prefect cron tự bắn. Tất cả hội tụ về deployment `retraining/default`, worker thực thi.

## 9. Quyết định thiết kế & đánh đổi (tóm tắt)

| Quyết định | Lý do | Đánh đổi |
|---|---|---|
| Hướng sự kiện (Kafka) | tách serving khỏi logging; fan-out nhiều consumer | log eventual-consistency dưới giây; thêm broker |
| Prefect tách server/worker | hết xung đột dependency; tách lịch vs thực thi | thêm container |
| MLflow backend PostgreSQL | bỏ SPOF SQLite | phụ thuộc Postgres |
| DVC version data+model → MinIO | reproducibility + data lineage | thao tác thủ công (`dvc add/push`) |
| Serving nạp `.pt` trực tiếp | đơn giản, nhanh | registry chỉ là lớp governance |
| Auth 1 ADMIN_TOKEN | đủ cho demo/đồ án | chưa RBAC/TLS (xem SECURITY.md) |

## 10. Giới hạn đã biết (trung thực)

- `/predict` không scale theo concurrency (inference CPU tuần tự) — đo trong [PERF-REPORT](performance/PERF-REPORT.md), có lộ trình tối ưu.
- Bảo mật demo-grade (default password, không RBAC/TLS/pentest) — xem [SECURITY.md](SECURITY.md).
- HA: mới bỏ SPOF MLflow; Postgres/MinIO/Kafka còn single-node.
- "Drift" gồm heuristic chất lượng ảnh + PSI phân bố lớp (chưa drift trên embedding/feature đầy đủ).
- CD (deploy tự động) chưa làm (đánh dấu hướng phát triển).
