# Kiến trúc hệ thống — Skin Lesion MLOps

> Tài liệu kiến trúc để đưa vào báo cáo đồ án. Mọi thành phần/port/luồng đều bám đúng hệ thống đang chạy (`docker compose`, 12 service). Bổ trợ: [README](../README.md) (chạy/cấu trúc), [plan.md](plan.md) (kế hoạch), [giai-thich-he-thong-mlops.md](giai-thich-he-thong-mlops.md) (cơ chế DVC/Prefect/MLflow), [SECURITY.md](SECURITY.md), [performance/PERF-REPORT.md](performance/PERF-REPORT.md).

## 1. Tổng quan

Hệ thống MLOps phân loại tổn thương da từ ảnh dermoscopy (HAM10000). Trọng tâm là **kiến trúc vòng đời ML** (data versioning → serving → monitoring → registry → orchestration → retraining), mô hình học sâu chỉ là một thành phần thay thế được. Tự định vị **MLOps Maturity Level 1 đầy đủ + hiện thực cơ chế Level 2** (retraining tự động hướng sự kiện + theo lịch, promote gate).

**Nguyên tắc thiết kế:** tách trách nhiệm rõ (serving / lưu trữ / điều phối / quản model), hướng sự kiện (Kafka), đóng gói container (Docker Compose), mọi tham số cấu hình được (DB `system_config` + `.env`), truy cập có xác thực (JWT) + phân quyền (RBAC).

## 2. Sơ đồ kiến trúc tổng (12 service)

```mermaid
flowchart TD
    BR["Trình duyệt — doctor · nurse · admin"]

    subgraph FE["frontend · Next.js :3100"]
        AG["AuthGate + NavBar — chặn route theo role"]
        PX["proxy /api/* — server-side, gắn Bearer token"]
    end

    subgraph API["api · FastAPI :8200 to 8000"]
        RT["routers: health · auth · predict · predictions · reviews · monitoring · admin"]
        DEP["deps: JWT get_current_user / require_admin"]
        SVC["services: model_service · model_store · gradcam · storage · drift · mlflow · retrain · ingest · prefect_trigger · auto_trigger S1–S3 · kafka · auth"]
        MEM["model trong RAM (app.state)"]
    end

    subgraph STORE["Lưu trữ trạng thái"]
        PG[("postgres :5434 — predictions · reviews · users · system_config · retraining_runs · DB mlflow")]
        MN[("minio 9000/9001 — buckets: models · predictions · mlflow · dvc-store")]
    end

    subgraph EVT["Hướng sự kiện"]
        KF["kafka KRaft — topic prediction-events"]
        CS["consumer — group prediction-logger"]
        AC["alert-consumer — group drift-monitor"]
        AL["Cảnh báo drift (log)"]
    end

    subgraph MLO["Điều phối + quản model"]
        PS["prefect-server :4200 — UI/API + CRON S4"]
        PW["prefect-worker — retraining_flow"]
        MF["mlflow :5000 — tracking + Model Registry"]
    end

    subgraph MON["Giám sát"]
        PM["prometheus :9090"]
        GF["grafana :3001"]
    end

    BR -->|"http localhost:3100"| FE
    AG --- PX
    PX -->|"http api:8000 + Bearer"| RT
    RT --- DEP
    DEP --- SVC
    SVC --- MEM

    SVC -->|"SQL"| PG
    SVC -->|"S3 object"| MN
    MN -.->|"models/production/model.pt → RAM"| MEM
    SVC -->|"publish"| KF
    SVC -->|"REST trigger S1–S3"| PS
    SVC -->|"registry / gate"| MF

    KF -->|"fan-out"| CS
    KF -->|"fan-out"| AC
    CS -->|"insert prediction"| PG
    AC -->|"vượt ngưỡng"| AL

    PM -->|"scrape /metrics"| RT
    GF --> PM

    PS -->|"pickup flow run"| PW
    PW -->|"log · register · promote"| MF
    PW -->|"sync model"| MN
    MF -->|"artifacts"| MN
    MF -->|"backend store"| PG
```

**Cổng host:** frontend 3100 · api 8200 · postgres 5434 · minio 9000/9001 · prometheus 9090 · grafana 3001 · mlflow 5000 · prefect-server 4200. (kafka, consumer, alert-consumer, prefect-worker: không expose cổng.)

## 3. Trách nhiệm từng thành phần

| Service | Trách nhiệm | Trục |
|---|---|---|
| `frontend` | UI Next.js + proxy `/api/*` (không CORS, ẩn URL API); `AuthGate` chặn route khi chưa đăng nhập, ẩn link Admin theo role | giao diện |
| `api` | Serving `/predict` + Grad-CAM (model tải từ MinIO); xác thực JWT + RBAC; REST admin; **active-learning ingest** (review→`data/subset`+`dvc add/push`); đánh giá tín hiệu S1–S3; producer Kafka | serving + control |
| `postgres` | `predictions/reviews/users/system_config/retraining_runs` + **MLflow backend store** | trạng thái bền |
| `minio` | Object storage 4 bucket: `models` (**model serving**: production/staging/archive) · `predictions` (ảnh) · `mlflow` (artifacts) · `dvc-store` (DVC remote cho data) | lưu file |
| `kafka` | Message broker (KRaft) — topic `prediction-events` | đường ống sự kiện |
| `consumer` | Group `prediction-logger`: event → ghi `predictions` (async) | logging |
| `alert-consumer` | Group `drift-monitor`: event → cảnh báo drift real-time (fan-out) | monitoring |
| `mlflow` | Tracking + Model Registry + promote gate (backend Postgres) | quản model |
| `prefect-server` | Orchestration: UI/API + lịch cron (tín hiệu S4) | điều phối (lịch) |
| `prefect-worker` | Thực thi `retraining_flow`: smoke train thật (**warm-start từ Production** + luôn gom ảnh review) → **re-eval Production trên data/val** → gate → promote | điều phối (chạy) |
| `prometheus` | Thu thập metrics (scrape `api:/metrics`) | giám sát |
| `grafana` | Dashboard giám sát | giám sát |

## 3A. Xác thực & phân quyền (JWT + RBAC)

Truy cập có **đăng nhập** (JWT `Bearer`, HS256) + **phân quyền theo vai trò** (RBAC). Mật khẩu băm **bcrypt**; người dùng lưu ở bảng `users`; cấu hình `JWT_SECRET` / `JWT_EXPIRE_MINUTES` (mặc định 480 phút) qua biến môi trường.

| Vai trò | Quyền |
|---|---|
| `admin` | Toàn bộ — gồm trang Admin (control plane: promote, ingest, retrain, config) **và quản lý người dùng** |
| `doctor` | Trang lâm sàng: Dự đoán · Lịch sử · Cần review · Giám sát |
| `nurse` | Như `doctor` (lâm sàng), không vào Admin |

```mermaid
flowchart LR
    L["POST /auth/login (username + password)"] -->|"verify bcrypt"| T["JWT access_token {sub, role, exp}"]
    T --> H["mọi request gắn Authorization: Bearer"]
    H --> G1["get_current_user — bắt buộc token hợp lệ"]
    G1 --> G2{"require_admin?"}
    G2 -->|"role = admin"| OK["cho qua"]
    G2 -->|"khác"| F403["403 Cần quyền admin"]
    G1 -.->|"thiếu / hết hạn"| F401["401 → frontend chuyển về /login"]
```

**Mức bảo vệ từng endpoint** (đăng ký ở [`api/main.py`](../code/backend/app/api/main.py) + per-router):

| Nhóm endpoint | Bảo vệ |
|---|---|
| `/health` · `/metrics` (Prometheus) · `GET /predictions/{id}/image` | **public** (cố ý — health-check, scrape, hiển thị ảnh qua thẻ `<img>`) |
| `POST /auth/login` | public · `GET /auth/me` cần token |
| `/predict` · `/reviews*` · `GET /predictions` · `GET /predictions/{id}` · `/monitoring/stats` | cần token (mọi role) |
| `/admin/*` (gồm `/admin/users*`) | cần role **admin** (`require_admin`) |

> Hai tài khoản seed sẵn khi khởi động: `admin/admin123` (admin) và `doctor/doctor123` (doctor). Admin tạo thêm bác sĩ/y tá qua **Quản lý người dùng** (`/admin/users`: list/create/đổi mật khẩu/xoá; chốt: không tự xoá mình, không xoá admin cuối cùng). Đây vẫn là **demo-grade** (mật khẩu mặc định, chưa TLS) — xem [SECURITY.md](SECURITY.md).

## 4. Mô hình dữ liệu (ERD)

Database `skinlesion` (app) — 5 bảng:

```mermaid
erDiagram
    predictions ||--o| reviews : "1 — 0..1 (prediction_id)"

    predictions {
        bigserial id PK
        varchar prediction_id UK
        timestamptz created_at
        varchar image_key
        int image_width
        int image_height
        varchar predicted_class
        real confidence
        jsonb top_k
        int latency_ms
        varchar model_version
        varchar data_version "hash DVC tập train lúc dự đoán"
        boolean is_low_confidence
        boolean is_drift_suspected "drift heuristic brightness/blur"
        real brightness_score
        real blur_score
        varchar source "web | stream"
        varchar correlation_id
    }

    reviews {
        bigserial id PK
        varchar prediction_id FK "UNIQUE — 1:1 predictions"
        varchar review_label
        varchar review_status "pending | reviewed"
        varchar reviewer
        timestamptz reviewed_at
        timestamptz created_at
        varchar used_in_data_version "NULL=chưa ingest; md5 | leak_skipped | invalid"
    }

    users {
        bigserial id PK
        varchar username UK
        varchar password_hash "bcrypt"
        varchar role "admin | doctor | nurse"
        timestamptz created_at
    }

    system_config {
        varchar key PK "vd retrain_config"
        jsonb value "mode, trigger S1–S4, smoke, promote_rules, schedule_cron…"
        timestamptz updated_at
        varchar updated_by
    }

    retraining_runs {
        bigserial id PK
        timestamptz triggered_at
        varchar trigger_reason "S1+S2+S3 | S4 | manual"
        varchar mode "artifact | smoke"
        int reviewed_count
        varchar production_tag
        varchar candidate_tag
        boolean gate_passed
        boolean promoted
        jsonb detail
    }
```

- **predictions 1—1 reviews**: mỗi prediction có tối đa 1 review (FK + UNIQUE). Bảng tách: predictions bất biến (log), reviews là annotation của bác sĩ.
- **users**: tài khoản đăng nhập + vai trò (RBAC) — không có FK cứng tới predictions/reviews (`reviewer` chỉ lưu username dạng text).
- **Quan hệ logic (không FK cứng)**: `model_version`/`data_version` ↔ MLflow registry + DVC hash (governance).

Database `mlflow` (Postgres riêng) — do MLflow tự quản: `experiments`, `runs`, `registered_models`, `model_versions`, `model_version_tags`… (registry + tracking).

## 5. Sequence — Dự đoán (event-driven qua Kafka)

```mermaid
sequenceDiagram
    autonumber
    participant BR as Trình duyệt (đã đăng nhập)
    participant FE as frontend proxy
    participant API as api (FastAPI)
    participant MN as MinIO
    participant KF as Kafka
    participant CS as consumer
    participant AC as alert-consumer
    participant PG as PostgreSQL

    BR->>FE: POST /api/predict (ảnh)
    FE->>API: POST /predict + Authorization Bearer
    Note over API: deps xác thực JWT (get_current_user)
    API->>API: tiền xử lý + inference + Grad-CAM + drift
    API->>MN: upload ảnh (bucket predictions)
    API->>KF: publish event (prediction-events)
    API-->>FE: 200 JSON (top-k + Grad-CAM) — trả NGAY
    FE-->>BR: hiển thị kết quả + Grad-CAM
    KF-->>CS: fan-out (prediction-logger)
    KF-->>AC: fan-out (drift-monitor)
    CS->>PG: insert prediction (async)
    AC->>AC: tính rate, vượt ngưỡng → cảnh báo (log)
    Note over API,PG: Kafka down → API ghi thẳng PG (fallback)
    Note over API: Prometheus scrape /metrics riêng (không phải DB đẩy)
```

## 6. Sequence — Retraining (Prefect → gate → promote)

```mermaid
sequenceDiagram
    autonumber
    participant TR as Trigger (S1–S3 api loop · S4 cron · Admin Retrain Now)
    participant PS as prefect-server
    participant PW as prefect-worker
    participant DV as ingest+DVC (ở api, trước train)
    participant MF as MLflow
    participant MN as MinIO (bucket models)
    participant PG as PostgreSQL

    TR->>PS: create flow run (retraining/default)
    PS->>PW: dispatch flow run
    Note over DV: auto-ingest review → data/subset → dvc push (data version mới)
    Note over PW: retrain_service.run(reason), mode=smoke
    PW->>PW: trainer — warm-start từ Production + luôn gom ảnh review → train đa kiến trúc
    PW->>MF: eval data/val · log + register (Staging)
    PW->>PW: RE-EVAL Production trên data/val (gate cùng nguồn)
    PW->>PW: PROMOTE GATE — macro_f1 (+biên 0.005) · mel_recall (not_worse + SÀN 0.40) · acc (±0.02)
    alt Đạt gate
        PW->>MF: promote → Production
        PW->>MN: sync model → models/production/model.pt
    else Không đạt
        PW->>MF: giữ Production (candidate ở Staging)
    end
    PW->>PG: ghi retraining_runs (+detail)
    Note over TR,MN: Admin /admin/reload-model → api TẢI LẠI model production từ MinIO (không restart)
```

> Triết lý 2 tầng: **TRIGGER** (có nên thử) tách **PROMOTE GATE** (có đủ tốt để thay). Trigger rộng tay cũng an toàn vì gate luôn chặn model kém.

## 7. Active-learning — review → ingest → data version mới

```mermaid
flowchart TD
    P["/predict → ảnh ở MinIO predictions/ + bản ghi DB"] --> R["bác sĩ review (gán nhãn)<br/>reviews.review_status = reviewed"]
    R -->|"POST /admin/ingest-reviews (hoặc auto trước mỗi retrain)"| I1["1. lấy review chưa ingest (used_in_data_version IS NULL)"]
    I1 --> I2["2. tải ảnh từ MinIO predictions/ → VALIDATE (mở được + nhãn ∈ lớp hợp lệ)"]
    I2 --> I3{"3. LEAK-GUARD — md5 trùng val/test?"}
    I3 -->|"trùng"| LK["loại khỏi train · mark leak_skipped"]
    I3 -->|"sạch"| I4["4. ghi data/subset/{nhãn}/pred_{id}.jpg"]
    I4 --> I5["5. dvc add + dvc push -r minio_internal → data version mới (md5) lên dvc-store"]
    I5 --> I6["6. mark reviews.used_in_data_version = md5 (idempotent)"]
    I6 --> RT["retrain (S1/tay) → trainer đọc data/subset (đã có ảnh review) + warm-start → gate"]
```

> Bấm nút là **thủ công**; ngoài ra **mọi retrain (S1–S4/tay) tự gọi ingest này trước khi train** (xem §9) — nút chỉ để ingest sớm/độc lập.
> DVC chạy **ngay trong container api** (`dvc[s3]`, `core.no_scm=true`, remote nội bộ `minio_internal` → `minio:9000`).
> Vòng human-in-the-loop khép kín: **chỉ** ảnh bác sĩ đã duyệt **và** không trùng holdout (val/test) mới vào tập train.

## 8. Sequence — Rollback data version (DVC)

```mermaid
flowchart LR
    A["① git checkout commit-cũ -- data/subset.dvc<br/>(lấy con trỏ v1)"] --> B["② dvc checkout / dvc pull<br/>→ DVC đọc hash → dựng lại ảnh v1 (từ cache/MinIO)"]
    B --> C["③ trigger retrain<br/>→ worker đọc /app/data/subset (đang là v1) → train v1"]
```

DVC (không phải Prefect) kéo data từ MinIO theo con trỏ; Prefect chỉ chạy code sau khi data đã có trên đĩa.

## 9. Luồng tín hiệu retraining (S1–S4)

| Mã | Tín hiệu | Service đánh giá | Nguồn dữ liệu |
|---|---|---|---|
| S1 | đủ **ảnh review CHƯA ingest** | `api` (loop) | `reviews` (`used_in_data_version IS NULL` ≥ ngưỡng) |
| S2 | drift / confidence thấp | `api` (loop) | `predictions` (cờ drift/low-conf) |
| S3 | hiệu năng online giảm | `api` (loop) | `reviews`+`predictions` (accuracy) |
| S4 | định kỳ | `prefect-server` (cron) | lịch `schedule_cron` |

```mermaid
flowchart LR
    S1["S1 đủ review chưa ingest (api loop)"] --> RT
    S2["S2 drift / low-conf (api loop)"] --> RT
    S3["S3 accuracy online giảm (api loop)"] --> RT
    S4["S4 định kỳ cron (prefect-server)"] --> RT["retrain_service.trigger() → deployment retraining/default"]
    RT --> AI{"auto-ingest review + skip-guard<br/>data_version có đổi?"}
    AI -->|"có data mới / hoặc manual"| TW["prefect-worker train → promote gate"]
    AI -->|"auto + data không đổi"| SK["skip_no_new_data (không train vô ích)"]
```

S1–S3 event-driven (api → gọi Prefect REST); S4 = Prefect cron tự bắn. Tất cả hội tụ về deployment `retraining/default`, worker thực thi.

**Khép kín active-learning (mọi tín hiệu đi qua `retrain_service.trigger()` ở api):**
1. **Auto-ingest**: trước khi train, tự đưa review đang chờ (`used_in_data_version IS NULL`) vào `data/subset` + `dvc push` → train luôn trên data mới nhất. *(Ingest chạy ở `api` vì worker mount `data:ro` + không có dvc; worker đọc cùng folder host nên thấy ngay.)*
2. **Skip-guard**: nếu tín hiệu **tự động** mà **data không đổi** (`data_version` == lần train trước) → **bỏ qua** (ghi `skip_no_new_data`, không train vô ích). `manual` (Retrain Now) thì luôn train.
> Nhờ vậy S2/S3/S4 chỉ thực sự train khi **có dữ liệu review mới** (vd ảnh gây drift đã được duyệt); không có gì mới thì chỉ đóng vai "chuông báo".

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
| Auth **JWT + RBAC** (admin/doctor/nurse), mật khẩu **bcrypt** | có user/role thật, admin tự quản tài khoản; thay cho 1 token tĩnh | vẫn demo-grade: mật khẩu mặc định, chưa TLS/refresh-token/pentest (xem SECURITY.md) |

## 11. Giới hạn đã biết (trung thực)

- `/predict` không scale theo concurrency (inference CPU tuần tự) — đo trong [PERF-REPORT](performance/PERF-REPORT.md), có lộ trình tối ưu.
- Bảo mật demo-grade: **đã có** JWT + RBAC + bcrypt, nhưng **chưa** TLS/HTTPS, chưa refresh-token/rotation, mật khẩu mặc định, chưa pentest — xem [SECURITY.md](SECURITY.md).
- HA: mới bỏ SPOF MLflow; Postgres/MinIO/Kafka còn single-node.
- "Drift" gồm heuristic chất lượng ảnh (brightness/blur) + PSI phân bố lớp (chưa drift trên embedding/feature đầy đủ).
- **S3 (online accuracy) đo trên ảnh đã review** (vốn là ảnh low-conf) → thiên lệch về phía khó; chưa có tập audit ngẫu nhiên.
- Confidence chưa calibrate; `dvc pull` trước train chưa nối (chạy 1 máy nên data luôn sẵn) — chỉ cần khi train máy khác.
- CD (deploy tự động) chưa làm (đánh dấu hướng phát triển).

> **Đã siết (so với bản đầu):** gate **re-eval Production trên data/val** (so cùng nguồn) + **sàn `mel_recall ≥ 0.40`** + **biên macro_f1 0.005** (chống nhiễu); ingest có **leak-guard** (md5 vs val/test); retrain **warm-start** + luôn gom ảnh review; truy cập có **JWT + RBAC**.
