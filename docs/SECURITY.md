# Mô hình bảo mật — trung thực

> Tài liệu này nói rõ hệ thống bảo vệ cái gì, **chỗ nào mới là demo-grade**, và cần làm gì trước khi chạy thật. Viết để không "chống chế" khi bảo vệ.

## 1. Hiện trạng (demo-grade — phải khai thật)

| Hạng mục | Hiện tại | Mức độ |
|---|---|---|
| Bí mật (mật khẩu/token) | Đưa ra biến môi trường (`code/.env`), có default trong compose | ⚠️ default demo, phải đổi |
| Xác thực người dùng | **JWT** (`Bearer`, HS256), mật khẩu băm **bcrypt**, bảng `users` | ✅ đã có (token TTL mặc định 480′, `JWT_SECRET` env) |
| Phân quyền (RBAC) | 3 vai trò `admin` / `doctor` / `nurse`; `/admin/*` cần `admin` | ✅ đã có (`require_admin`); admin tự quản tài khoản |
| Endpoint public (cố ý) | `/health`, `/metrics` (scrape), `GET /predictions/{id}/image` (thẻ `<img>`) | ✅ có chủ đích |
| Mật khẩu mặc định (app) | `admin/admin123`, `doctor/doctor123` seed sẵn | ⚠️ phải đổi trước deploy |
| Mật khẩu Postgres/MinIO/Grafana | default (`skin_pass`, `minioadmin`, `admin`) | ⚠️ phải đổi trước deploy |
| Refresh token / rotation / lockout | Chưa có (chỉ access token) | ⚠️ nên bổ sung cho production |
| TLS/HTTPS | Không (HTTP nội bộ) | ⚠️ cần reverse proxy + TLS khi public |
| Pentest / OWASP scan | Chưa chạy | ❌ chưa làm |

→ Hệ thống **đã có xác thực + phân quyền thật (JWT + RBAC)**, nhưng vẫn ở mức **demo nội bộ** (mật khẩu mặc định, chưa TLS/pentest), **chưa** dành cho internet/production.

## 2. Quản lý bí mật (đã cải thiện)

- Mọi bí mật được externalize ra biến môi trường; `docker-compose` đọc `code/.env`.
- `code/.env` bị **gitignore** (không commit bí mật thật). Template: `code/.env.example`.
- Nếu không có `.env`, compose dùng **default demo** (`${VAR:-default}`) — tiện chạy thử, **KHÔNG an toàn**.

**Trước khi deploy thật — bắt buộc:**
```bash
cd code
cp .env.example .env
# sửa .env: đặt mật khẩu mạnh cho POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD,
#            ADMIN_TOKEN, GRAFANA_ADMIN_PASSWORD
docker compose up -d   # áp dụng
```

## 3. Những gì PHẢI làm cho production (chưa làm)

1. **Đổi toàn bộ mật khẩu default** (qua `.env` + đổi mật khẩu user app `admin`/`doctor`) — quan trọng nhất. Đặt `JWT_SECRET` mạnh.
2. ~~Auth thật cho người dùng + RBAC~~ — **đã làm** (JWT + bcrypt + RBAC `admin`/`doctor`/`nurse`). Còn lại: **refresh-token + rotation**, **khoá tài khoản** sau N lần sai, **rate-limit** đăng nhập.
3. **TLS**: đặt reverse proxy (Nginx/Caddy) + Let's Encrypt; ép HTTPS.
4. **Network**: chỉ expose cổng cần thiết; Postgres/MinIO/MLflow/Prefect **không** mở ra ngoài.
5. **Rate limiting** cho endpoint public (`/predict`).
6. **OWASP ZAP scan + pentest** trên staging trước go-live (0 Critical/High).
7. **Audit log** cho thao tác admin (retrain/promote/config).
8. **Backup** Postgres (app + MLflow) + MinIO định kỳ; kiểm thử restore.

## 4. Dữ liệu nhạy cảm

- Ảnh dermoscopy là dữ liệu y tế → khi dùng dữ liệu bệnh nhân thật cần tuân thủ quy định bảo vệ dữ liệu; ẩn danh; mã hóa at-rest (MinIO SSE) + in-transit (TLS).
- Không log ảnh/PII ra log hệ thống.

## 5. Tóm tắt 1 câu
Hệ thống **đã có xác thực JWT + RBAC + bcrypt** và **externalize bí mật + tài liệu hóa** mô hình bảo mật, nhưng vẫn là **demo-grade** (mật khẩu mặc định, chưa TLS, chưa refresh-token, chưa pentest). Khai rõ điều này; coi mục 3 là việc bắt buộc cho production.
