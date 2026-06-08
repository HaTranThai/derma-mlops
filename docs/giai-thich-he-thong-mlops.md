# Giải thích hệ thống MLOps — DVC · Prefect · MLflow · MinIO

> Tài liệu này viết để **đọc lại cho dễ hiểu**: giải thích cơ chế từng thành phần, quan hệ giữa chúng, và trả lời các câu hỏi đã đặt ra trong quá trình tìm hiểu. Mọi ví dụ/hash/đường dẫn đều lấy từ hệ thống thật trong repo này.

## Mục lục
1. [Bức tranh tổng — ai làm gì](#1-bức-tranh-tổng--ai-làm-gì)
2. [MinIO — kho chứa file](#2-minio--kho-chứa-file)
3. [DVC — version dữ liệu (phần khó nhất)](#3-dvc--version-dữ-liệu)
4. [DVC ↔ Git — quan hệ cộng sinh](#4-dvc--git--quan-hệ-cộng-sinh)
5. [Prefect — điều phối/chạy](#5-prefect--điều-phốichạy)
6. [MLflow — ghi kết quả & quản model](#6-mlflow--ghi-kết-quả--quản-model)
7. [Prefect vs MLflow — phân biệt](#7-prefect-vs-mlflow--phân-biệt)
8. [Các luồng chạy (predict, retrain, rollback)](#8-các-luồng-chạy)
9. [FAQ — những câu đã hỏi](#9-faq--những-câu-đã-hỏi)

---

## 1. Bức tranh tổng — ai làm gì

Bốn thành phần, **bốn trục khác nhau, không chồng vai**:

| Thành phần | Vai trò 1 câu | Trục |
|---|---|---|
| **MinIO** | KHO chứa file (object storage) | *nơi lưu* |
| **DVC** | version DỮ LIỆU + kéo data lên đĩa | *data nào* |
| **Prefect** | điều phối: KHI NÀO train, chạy, retry | *thời gian / thực thi* |
| **MLflow** | ghi KẾT QUẢ train + quản model/version | *kết quả / model* |

Câu thần chú:
> **MinIO** = ở đâu · **DVC** = data nào · **Prefect** = chạy lúc nào · **MLflow** = ra model gì, model nào tốt.

Còn **`trainer.py`** = code train thật (thợ làm việc), chạy trong container **prefect-worker**.

---

## 2. MinIO — kho chứa file

**Bản chất:** 1 server nói giao thức S3 (HTTP). Chỉ biết 2 việc:
- **PUT** `(bucket, key, bytes)` → cất đống byte dưới 1 "key" (chuỗi giống đường dẫn).
- **GET** `(bucket, key)` → trả lại đúng đống byte đó.

MinIO **không hiểu** "version", "model", "ảnh" là gì — với nó tất cả chỉ là *key → bytes*. Mọi sự thông minh (version, gate…) do DVC/MLflow áp lên trên.

**3 bucket trong hệ thống:**
```
dvc-store    ← DVC để các phiên bản data + model (file theo hash)
mlflow       ← MLflow để artifact model mỗi lần train
predictions  ← api để ảnh người dùng upload khi predict
```
→ MinIO bị **3 thứ khác nhau dùng cho 3 mục đích**. MinIO ≠ DVC; DVC chỉ *mượn* 1 ngăn của MinIO.

> **Ví dụ:** MinIO = cái **tủ khóa khổng lồ**. Đưa đồ + dán nhãn (key) → cất; đọc nhãn → lấy ra. Hết.

---

## 3. DVC — version dữ liệu

Chìa khóa: **DVC lưu file theo HASH của NỘI DUNG (content-addressed), không theo tên gốc.**

### Khi gõ `dvc add data/subset`, DVC làm 4 việc:
1. **Băm từng file**: đọc nội dung ảnh → tính `md5` → chuỗi 32 ký tự (vân tay nội dung).
2. **Chép vào cache theo hash**: `.dvc/cache/files/md5/<2 ký tự đầu>/<phần còn lại>`. Tên file = hash, **bỏ đuôi `.jpg`**.
3. **Tạo bản kê `.dir`**: 1 file JSON liệt kê *tên gốc ↔ hash* của mọi ảnh, rồi băm chính bản kê → ra **dir-hash**.
4. **Ghi cuống vé `data/subset.dvc`** (text bé tí, đây là thứ Git giữ) trỏ tới dir-hash, + thêm `/subset` vào `data/.gitignore`.

### 3 lớp dữ liệu (rất quan trọng)
```
data/subset.dvc   (git giữ; mỗi commit = 1 dir-hash)
      │ trỏ tới
.dir              (bản kê: [{md5, "mel/ISIC_001.jpg"}, …])   ← mỗi VERSION có 1 .dir riêng
      │ mỗi dòng trỏ tới
blob              (file ảnh JPEG THẬT, đặt tên = md5, bỏ đuôi)  ← lưu ở cache + MinIO
```

### Bằng chứng thật trong repo
- Cuống vé `data/subset.dvc`:
  ```
  md5: af03189d01f52aee2146088f373a037f.dir   nfiles: 280   size: 81MB
  ```
- Blob trong cache **chính là ảnh JPEG**, chỉ đổi tên:
  ```
  file .dvc/cache/files/md5/db/d7e265a401b1eeb3d55b15b3930690
    → "JPEG image data, 600x450"
  md5 của blob = md5 của ảnh thật = tên của chính blob (dbd7e265…)
  ```
- Mỗi version 1 `.dir` (có 2 version → 2 file `.dir`):
  ```
  b46b1f68…dir  ← version 1 (subset cũ)
  af03189…dir   ← version 2 (subset train hiện tại)
  ```

### `dvc push` / `dvc pull` / `dvc checkout`
- **push**: tải blob (tên = hash) + bản kê `.dir` lên MinIO `dvc-store`.
- **pull**: tải blob **còn thiếu** từ MinIO về cache (= fetch) **+ checkout**.
- **checkout**: dựng lại folder `data/subset` từ **cache** theo bản kê `.dir` (không cần mạng nếu cache đủ).

### Hồi phục ảnh hoạt động thế nào
```
data/subset.dvc → dir-hash → mở .dir → [{hash, "mel/ISIC_001.jpg"}, …]
   với mỗi mục: lấy blob (tên=hash) từ cache (hoặc pull MinIO) → copy/đặt lại đúng tên+thư mục
   .dvc/cache/files/md5/db/d7e265…  ──►  data/subset/akiec/ISIC_0024562.jpg
```
**Không "giải mã hash"** (bất khả). DVC **tra bản kê** để biết "blob hash X chính là file tên Y".

### Vì sao dùng hash? (cái hay)
- **Version**: đổi nội dung → đổi hash → đổi cuống vé → git commit = 1 phiên bản mới.
- **Không trùng lặp**: 2 ảnh giống hệt → cùng hash → kho chỉ giữ 1 bản; nhiều version share blob.
- **Toàn vẹn**: tải về băm lại, lệch hash = phát hiện hỏng.

> **Ví dụ quầy giữ đồ:** đưa áo (file), nhân viên dán mã theo *đặc điểm cái áo* (hash) rồi cất theo mã (không theo tên bạn). Bạn cầm **cuống vé** (`.dvc` trong git). Muốn lấy đúng áo "phiên bản hôm qua" → đưa cuống vé hôm qua → nhận đúng áo đó.

---

## 4. DVC ↔ Git — quan hệ cộng sinh

- **Git giỏi giữ file text, có dòng thời gian (commit); nhưng dở với file nặng (ảnh/model).**
- Nên DVC: lôi ảnh **ra khỏi git** (`.gitignore`), thay bằng **cuống vé text bé** (`.dvc`) mà git giữ được.

```
Git   → giữ CUỐNG VÉ (text, có lịch sử commit)
DVC   → giữ FILE NẶNG (blob theo hash, ở cache + MinIO)
.dvc  → cây cầu nối 2 bên
```

**Bằng chứng:** git chỉ track `data/.gitignore` + `data/subset.dvc`; ảnh bị gitignore. Và `git log` cho thấy 2 commit = 2 version data, mỗi commit 1 hash:
```
commit f564b0c → af03189…dir   (40 ảnh train/lớp)
commit a5c9b05 → b46b1f68…dir  (10 ảnh test/lớp)
```

**Phép màu — tái lập cùng nhau:**
```
git checkout <commit-cũ> -- data/subset.dvc   → git trả lại cuống vé CŨ
dvc checkout (hoặc dvc pull)                   → DVC dựng lại ĐÚNG ảnh CŨ
```
→ Checkout commit cũ thì được cả **code cũ LẪN data cũ**, vì cuống vé data nằm trong git. Không có git thì cuống vé `.dvc` chỉ là tờ giấy rời, không biết của thí nghiệm nào.

| | Git | DVC | MLflow |
|---|---|---|---|
| Version cái gì | code | **data** (+ file artifact) | model (governance) |
| Trả lời | "code lúc đó thế nào" | "**data** lúc đó thế nào, lấy lại y hệt" | "model nào tốt, đang Production" |

---

## 5. Prefect — điều phối/chạy

Prefect tách 2 tiến trình, nói chuyện qua HTTP (`PREFECT_API_URL`):

### Prefect **server** (cổng 4200) = bộ não
Database + API + UI + **bộ lập lịch**. Lưu: danh sách **deployment** (flow nào chạy được, lịch ra sao) + các **flow run** và **trạng thái** (`Scheduled → Running → Completed/Failed`).

### `retraining_flow.serve(...)` chạy trong **prefect-worker** = cơ bắp
1. **Đăng ký deployment** lên server (kèm cron + tham số).
2. **Hỏi server liên tục** (poll): "có flow run nào tới lượt tôi?"
3. Thấy có → **chạy hàm Python `retraining_flow()` ngay trong worker** → gọi `retrain_service` → `trainer.py` → báo trạng thái về server.

### Bộ lập lịch (trong server) = đồng hồ
Đọc cron deployment → **tạo sẵn các flow run tương lai** ở trạng thái `Scheduled`. Tới giờ, worker (đang poll) nhặt lên chạy. **Đó là cơ chế S4.**

> **Ví dụ bếp nhà hàng:** server = bảng order + đồng hồ + sổ trạng thái; deployment = công thức đã đăng ký kèm "tự lên đơn 2h sáng ngày 1"; worker = đầu bếp canh bảng, tới giờ thì nấu (chạy code), hỏng thì làm lại (retry), xong ghi "đã xong".

### 4 tín hiệu trigger retrain
| Mã | Tín hiệu | Ai đánh giá | Cơ chế |
|---|---|---|---|
| **S1** | đủ review mới | `api` (loop) | đếm review từ lần retrain trước ≥ ngưỡng |
| **S2** | drift / confidence thấp | `api` (loop) | drift_rate/low_confidence_rate cửa sổ gần nhất vượt ngưỡng |
| **S3** | hiệu năng online giảm | `api` (loop) | accuracy (dự đoán vs nhãn bác sĩ) < ngưỡng |
| **S4** | định kỳ | `prefect-server` (cron) | lịch `schedule_cron` (mặc định `0 2 1 * *`) tự bắn |

- S1/S2/S3: event-driven, **đánh giá trong `api`** (background loop), vượt ngưỡng → gọi Prefect.
- S4: **lịch Prefect cron thật**, server tự bắn, worker chạy.
- Cả 4 đổ về 1 deployment `retraining/default`; **worker** luôn thực thi gate+promote.

> **Quan trọng:** Prefect KHÔNG bao giờ đụng data/MinIO/DVC. Nó chỉ quyết định *khi nào* và *gọi code*. Việc đọc ảnh, train là của `trainer.py`.

---

## 6. MLflow — ghi kết quả & quản model

MLflow **không chạy gì cả** — nó **ghi nhận + quản trị**:
- **Tracking**: mỗi lần train log lại metrics (accuracy, macro_f1…), params (epochs, **data_version**), file `.pt` (artifact → MinIO bucket `mlflow`).
- **Model Registry**: quản các **version model** + **stage** (`Staging` / `Production` / `Archived`).
- **Promote gate** dựa trên metrics trong registry để quyết định model mới có thay model cũ không.

> **Ví dụ:** MLflow = **sổ kết quả thí nghiệm + tủ trưng bày model**: "lần thử #5 đạt accuracy 0.84; model đang dùng (Production) là cái này."

---

## 7. Prefect vs MLflow — phân biệt

| | **Prefect** | **MLflow** |
|---|---|---|
| Trả lời | **KHI NÀO** chạy / chạy thế nào | **KẾT QUẢ** gì / model nào tốt |
| Bản chất | điều phối + **chạy** (động cơ) | **ghi nhận** + quản trị (sổ sách) |
| Có chạy code không? | **CÓ** (execute flow) | **KHÔNG** (chỉ ghi lại) |
| Lưu metric/model không? | **KHÔNG** | **CÓ** |
| "Lịch sử" của nó | các **lần CHẠY** (Scheduled→Running→Completed) | các **thí nghiệm + version model** (stage) |
| Ví dụ | "2h sáng ngày 1 train, lỗi retry 2 lần" | "model v2 macro_f1 0.71, đang Production" |

**Trong 1 lần retrain, chúng phối hợp:**
```
① Prefect: tới giờ/được trigger → khởi động flow → gọi trainer    (điều phối)
② trainer: train → GHI vào MLflow: metrics, params, .pt, đăng ký version  (ghi nhận)
③ MLflow: cất run + model version (Staging); promote gate so với Production  (quản trị)
④ Prefect: đánh dấu flow run = Completed                          (điều phối)
```
→ **Prefect bọc ngoài** (chạy đúng lúc + theo dõi trạng thái chạy); **MLflow nằm trong** (nhận kết quả + giữ catalog model).

---

## 8. Các luồng chạy

### 8.1. Dự đoán (predict)
```
Browser → frontend(proxy) → api
   api: model(.pt) → top-k + Grad-CAM; tính drift; upload ảnh → MinIO(predictions)
   api → bắn event vào Kafka(prediction-events) → consumer ghi 1 dòng → Postgres (async)
        (Kafka down → api ghi thẳng Postgres, fallback)
   ảnh hiển thị: Browser → frontend → api → stream từ MinIO
```

### 8.2. Smoke retrain (train thật trên subset)
```
Prefect (S1/S2/S3 từ api · hoặc S4 cron · hoặc Admin bấm)
   → prefect-worker chạy retraining_flow → retrain_service → trainer.py
       trainer ĐỌC ảnh từ /app/data/subset (mount của data/subset)
       train EfficientNet-B0 thật (vài epoch CPU)
       tính metric → lưu .pt + log MLflow + đăng ký version (Staging)
       ghi data_version = hash DVC (đọc từ data/subset.dvc)
   → promote gate so candidate vs Production → yếu thì TỪ CHỐI (giữ v2)
```
- **Train chạy ở container `prefect-worker`** (fallback: `api` nếu Prefect chết).
- `trainer` đọc đường dẫn **trong container** `/app/data/subset` = bind mount của host `/home/bbsw/headloader/data/subset`.

### 8.3. Rollback về data version cũ
```
① git checkout <commit-v1> -- data/subset.dvc   ← BẠN: lấy cuống vé v1
② dvc checkout (hoặc dvc pull)                   ← DVC: đọc hash v1 → dựng lại ảnh v1 lên đĩa
③ trigger train                                  ← Prefect: chạy trainer; trainer đọc đĩa (đang là v1) → train v1
```
- **DVC** kéo data từ MinIO/cache theo cuống vé (bước ②), **KHÔNG phải Prefect**.
- **Prefect** chỉ vào ở bước ③, chạy code trên data đang có sẵn trên đĩa.

---

## 9. FAQ — những câu đã hỏi

**Hỏi: DVC dùng trong dự án này có tác dụng gì?**
Version dữ liệu train (trụ cột data versioning), giữ git nhẹ (không nhét ảnh y tế vào git), liên kết "code↔data" trong 1 commit (tái lập), và data lineage cho retraining ("model nào sinh từ data version nào"). Lưu ý trung thực: full data thật ở Kaggle; DVC ở đây version subset nhỏ + model; phần model có trùng vai MLflow → giá trị riêng của DVC là **data**.

**Hỏi: DVC liên quan Git thế nào?**
Git giữ *cuống vé* (`.dvc`, text, có lịch sử); DVC giữ *file nặng* (blob theo hash). `git checkout` commit cũ → cuống vé cũ → `dvc checkout` → data cũ. Git cho data một dòng thời gian.

**Hỏi: `dvc push` xong có tự train không?**
KHÔNG. `dvc add/push` chỉ version + cất data. Train chỉ chạy bởi 4 tín hiệu (S1–S4) hoặc Admin bấm. DVC và trigger train **tách rời** (muốn "data mới → tự train" phải nối thêm).

**Hỏi: Đang ở version data nào thì train dùng version đó chứ?**
ĐÚNG. `trainer` đọc `data/subset` trên đĩa = đúng version đang checkout, không thể khác. Việc đã bổ sung: **ghi lại** hash version đó vào MLflow/checkpoint/run (`data_version`) để truy ngược.

**Hỏi: Prefect có kéo data từ MinIO theo cuống vé không?**
KHÔNG. Kéo data từ MinIO là việc của **DVC** (`dvc pull/checkout`). Prefect chỉ chạy code train sau khi data đã có trên đĩa.

**Hỏi: trainer chạy trong container nào?**
**`prefect-worker`** (đường thường). Fallback: `api`. KHÔNG chạy trong `mlflow`/`prefect-server`.

**Hỏi: Xóa folder `data/subset` rồi `dvc pull` có dựng lại được không?**
CÓ — đã test thật: chỉ cần còn cuống vé `data/subset.dvc` (trong git) → `dvc checkout`/`pull` dựng lại đủ 280 ảnh + 7 folder (blob lấy từ cache, hoặc từ MinIO nếu cache trống).

**Hỏi: File `.dir` để ở đâu? Mỗi version có 1 `.dir` riêng?**
`.dir` lưu ở cache (`.dvc/cache/files/md5/<2>/<rest>.dir`) **và** MinIO (bucket `dvc-store`), cũng là 1 blob theo hash. Mỗi version data = 1 `.dir` riêng (2 version → 2 file `.dir`).

**Hỏi: Blob trong cache/MinIO không giống ảnh, sao hồi phục được ảnh?**
Blob **chính là ảnh JPEG thật**, chỉ **đổi tên thành md5** (bỏ đuôi `.jpg`). Đã chứng minh: `file <blob>` → "JPEG image data 600x450", md5 blob = md5 ảnh gốc. Hồi phục = copy blob + đặt lại đúng tên (lấy từ `.dir`).

---

> **Tóm tắt 1 hình:**
> ```
> Kaggle(full) → subset → DVC ──version──► MinIO[dvc-store] (blob+,.dir theo hash)
>                          │ git giữ .dvc          ▲ dvc pull/checkout dựng lại
>                          ▼ worker đọc (mount /app/data/subset)
>   Prefect ──điều phối──► trainer.py ──train──► .pt + metrics + data_version
>                                          │
>                                          ▼
>                              MLflow ──► MinIO[mlflow] + Registry (gate/stage)
> ```
> **DVC** lo *data nào* · **Prefect** lo *chạy lúc nào* · **MLflow** lo *ra model gì, model nào tốt* · **MinIO** = kho chung.
