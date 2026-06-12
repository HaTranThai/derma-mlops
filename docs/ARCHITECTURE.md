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
│  services: model_service · model_store · gradcam · storage · drift · mlflow · retrain ·  │
│            ingest(active-learning) · prefect_trigger · auto_trigger(S1–S3) · kafka       │
│  model nạp RAM (app.state) ◄── tải từ MinIO: bucket models/production/model.pt           │
└──┬──────────┬───────────┬──────────────┬──────────────┬───────────────┬────────────────┘
   │SQL       │S3 object  │/metrics      │event publish │REST trigger    │REST registry/gate
   ▼          ▼           ▼(scrape)      ▼              ▼                ▼
┌────────┐ ┌─────────┐ ┌──────────┐  ┌─────────┐  ┌──────────────┐  ┌──────────────────┐
│postgres│ │ minio   │ │prometheus│  │  kafka  │  │prefect-server│  │ mlflow           │
│ :5434  │ │9000/01  │ │  :9090   │  │ (KRaft) │  │   :4200      │  │  :5000           │
│ tables:│ │buckets: │ │scrape api│  │ topic:  │  │ • UI/API     │  │ • tracking       │
│predict-│ │•models  │ └────┬─────┘  │predicti-│  │ • CRON S4 ──┐│  │ • Model Registry │
│ions    │ │•predict-│      │query   │on-events│  │   bắn lịch  ││  │ backend: postgres│
│reviews │ │ ions    │      ▼        └────┬────┘  └─────┬───────┼┘  │ artifacts: minio │
│system_ │ │•mlflow  │ ┌──────────┐       │fan-out      │ pickup │   └────────▲─────────┘
│config  │ │•dvc-    │ │ grafana  │   ┌───┴────┐       ▼        ▼            │
│retrain-│ │ store   │ │  :3001   │   ▼        ▼  ┌────────────────────┐    │
│ing_runs│ └───┬─────┘ │dashboard │ consumer  alert- │ prefect-worker     │    │
│        │     │       └──────────┘ (logger)  consumer│ retraining_flow   │────┘
│ +DB    │     │ ảnh prediction      │ ghi DB │ (drift)│ warm-start→train   │ gate/promote
│ mlflow │     │                     ▼        ▼ ALERT  │ →re-eval→gate→prom │
└───▲────┘     │              postgres   (log cảnh báo)└────────────────────┘
    │          │
    └──────────┴── consumer ghi prediction ─┘

 • Model serving:   api ◄── MinIO bucket "models" (production/model.pt — tải 1 lần vào RAM)
 • MLflow artifacts: mọi version model + metrics ──► MinIO bucket "mlflow"
 • Data versioning:  DVC ──add/push (CHỈ data/subset)──► MinIO bucket "dvc-store"  (model KHÔNG đi qua DVC)
 • Promote: worker copy model version → "models" bucket (production/staging/archive); api reload đọc lại từ đó
```

**Cổng host:** frontend 3100 · api 8200 · postgres 5434 · minio 9000/9001 · prometheus 9090 · grafana 3001 · mlflow 5000 · prefect-server 4200. (kafka, consumer, alert-consumer, prefect-worker: không expose cổng.)

## 3. Trách nhiệm từng thành phần

| Service | Trách nhiệm | Trục |
|---|---|---|
| `frontend` | UI Next.js + proxy `/api/*` (không CORS, ẩn URL API) | giao diện |
| `api` | Serving `/predict` + Grad-CAM (model tải từ MinIO); REST admin; **active-learning ingest** (review→`data/subset`+`dvc add/push`); đánh giá tín hiệu S1–S3; producer Kafka | serving + control |
| `postgres` | `predictions/reviews/system_config/retraining_runs` + **MLflow backend store** | trạng thái bền |
| `minio` | Object storage 4 bucket: `models` (**model serving**: production/staging/archive) · `predictions` (ảnh) · `mlflow` (artifacts) · `dvc-store` (DVC remote cho data) | lưu file |
| `kafka` | Message broker (KRaft) — topic `prediction-events` | đường ống sự kiện |
| `consumer` | Group `prediction-logger`: event → ghi `predictions` (async) | logging |
| `alert-consumer` | Group `drift-monitor`: event → cảnh báo drift real-time (fan-out) | monitoring |
| `mlflow` | Tracking + Model Registry + promote gate (backend Postgres) | quản model |
| `prefect-server` | Orchestration: UI/API + lịch cron (tín hiệu S4) | điều phối (lịch) |
| `prefect-worker` | Thực thi `retraining_flow`: smoke train thật (**warm-start từ Production** + luôn gom ảnh review) → **re-eval Production trên data/val** → gate → promote | điều phối (chạy) |
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
│    top_k         JSONB       │         │  used_in_data_version VAR(64)│ ← cờ ingest:
│    latency_ms    INT         │         └──────────────────────────────┘   NULL=chưa vào train;
│    model_version VARCHAR(64) │                                            md5 | leak_skipped | invalid
│    data_version  VARCHAR(64) │  ← hash DVC của tập train tại thời điểm dự đoán
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
                                         │      mode=smoke → trainer: WARM-START từ Production
                                         │        + LUÔN gom ảnh review (pred_*) → train nhiều arch
                                         │           └─ eval data/val · log+register Staging ──►│
                                         │      RE-EVAL Production trên data/val (gate cùng nguồn)
                                         │      PROMOTE GATE: macro_f1(+biên 0.005) · mel_recall │
                                         │                    (not_worse + SÀN 0.40) · acc(±0.02) │
                                         │      đạt → promote → sync model → bucket "models" ──►│
                                         │      ghi retraining_runs(+detail) ►│         │
                                         │  run COMPLETED      │         │         │
 Admin: /admin/reload-model → api TẢI LẠI model production từ MinIO (không restart)
```

> Triết lý 2 tầng: **TRIGGER** (có nên thử) tách **PROMOTE GATE** (có đủ tốt để thay). Trigger rộng tay cũng an toàn vì gate luôn chặn model kém.

## 7. Active-learning — review → ingest → data version mới

```
predict ─► ảnh ở MinIO "predictions/" + bản ghi DB
              │  bác sĩ review (gán nhãn) → reviews.review_status='reviewed'
              ▼  POST /admin/ingest-reviews   (nút Admin "Đưa review vào tập train")
 1. lấy review chưa ingest (used_in_data_version IS NULL)
 2. tải ảnh từ MinIO "predictions/" → VALIDATE (ảnh mở được + nhãn ∈ lớp hợp lệ)
 3. LEAK-GUARD: md5 ảnh trùng val/test? → LOẠI khỏi train, đánh dấu "leak_skipped"
 4. ảnh sạch → ghi data/subset/<nhãn>/pred_<id>.jpg
 5. dvc add data/subset + dvc push -r minio_internal → data version mới (md5) lên "dvc-store"
 6. mark reviews.used_in_data_version = <md5>   (idempotent — không ingest lại)
              ▼
 retrain (S1/tay) → trainer đọc data/subset (đã có ảnh review) + warm-start → gate
```

> DVC chạy **ngay trong container api** (`dvc[s3]`, `core.no_scm=true`, remote nội bộ `minio_internal` → `minio:9000`).
> Vòng human-in-the-loop khép kín: **chỉ** ảnh bác sĩ đã duyệt **và** không trùng holdout (val/test) mới vào tập train.

## 8. Sequence — Rollback data version (DVC)

```
①  git checkout <commit-cũ> -- data/subset.dvc      (lấy cuống vé v1)
②  dvc checkout / dvc pull  → DVC đọc hash → dựng lại ảnh v1 lên đĩa (từ cache/MinIO)
③  trigger retrain          → worker đọc /app/data/subset (đang là v1) → train v1
```
DVC (không phải Prefect) kéo data từ MinIO theo con trỏ; Prefect chỉ chạy code sau khi data đã có trên đĩa.

## 9. Luồng tín hiệu retraining (S1–S4)

| Mã | Tín hiệu | Service đánh giá | Nguồn dữ liệu |
|---|---|---|---|
| S1 | đủ review mới | `api` (loop) | `reviews` (đếm từ lần retrain) |
| S2 | drift / confidence thấp | `api` (loop) | `predictions` (cờ drift/low-conf) |
| S3 | hiệu năng online giảm | `api` (loop) | `reviews`+`predictions` (accuracy) |
| S4 | định kỳ | `prefect-server` (cron) | lịch `schedule_cron` |

S1–S3 event-driven (api → gọi Prefect REST); S4 = Prefect cron tự bắn. Tất cả hội tụ về deployment `retraining/default`, worker thực thi.

## 10. Quyết định thiết kế & đánh đổi (tóm tắt)

| Quyết định | Lý do | Đánh đổi |
|---|---|---|
| Hướng sự kiện (Kafka) | tách serving khỏi logging; fan-out nhiều consumer | log eventual-consistency dưới giây; thêm broker |
| Prefect tách server/worker | hết xung đột dependency; tách lịch vs thực thi | thêm container |
| MLflow backend PostgreSQL | bỏ SPOF SQLite | phụ thuộc Postgres |
| DVC version **data** → MinIO `dvc-store` | reproducibility + data lineage | model dùng `models` bucket riêng (không qua DVC) |
| Ingest tự `dvc add/push` (active-learning) | review→train khép kín, không gõ tay | `dvc add` băm lại cả tập mỗi lần (chậm khi data lớn) |
| Serving nạp model **từ MinIO** (`models/production/model.pt`) | nguồn chân lý tập trung, deploy máy khác chỉ cần MinIO | tải 1 lần vào RAM lúc startup/reload |
| DVC chạy trong container (`no_scm`) | ingest tự `dvc add/push`, không cần thao tác host | hack nhẹ (bỏ tích hợp git của DVC) |
| Auth 1 ADMIN_TOKEN | đủ cho demo/đồ án | chưa RBAC/TLS (xem SECURITY.md) |

## 11. Giới hạn đã biết (trung thực)

- `/predict` không scale theo concurrency (inference CPU tuần tự) — đo trong [PERF-REPORT](performance/PERF-REPORT.md), có lộ trình tối ưu.
- Bảo mật demo-grade (default password, không RBAC/TLS/pentest) — xem [SECURITY.md](SECURITY.md).
- HA: mới bỏ SPOF MLflow; Postgres/MinIO/Kafka còn single-node.
- "Drift" gồm heuristic chất lượng ảnh + PSI phân bố lớp (chưa drift trên embedding/feature đầy đủ).
- **S3 (online accuracy) đo trên ảnh đã review** (vốn là ảnh low-conf) → thiên lệch về phía khó; chưa có tập audit ngẫu nhiên.
- Confidence chưa calibrate; `dvc pull` trước train chưa nối (chạy 1 máy nên data luôn sẵn) — chỉ cần khi train máy khác.
- CD (deploy tự động) chưa làm (đánh dấu hướng phát triển).

> **Đã siết (so với bản đầu):** gate **re-eval Production trên data/val** (so cùng nguồn) + **sàn `mel_recall ≥ 0.40`** + **biên macro_f1 0.005** (chống nhiễu); ingest có **leak-guard** (md5 vs val/test); retrain **warm-start** + luôn gom ảnh review.
