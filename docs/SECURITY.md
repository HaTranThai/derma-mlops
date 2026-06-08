# Mô hình bảo mật — trung thực

> Tài liệu này nói rõ hệ thống bảo vệ cái gì, **chỗ nào mới là demo-grade**, và cần làm gì trước khi chạy thật. Viết để không "chống chế" khi bảo vệ.

## 1. Hiện trạng (demo-grade — phải khai thật)

| Hạng mục | Hiện tại | Mức độ |
|---|---|---|
| Bí mật (mật khẩu/token) | Đưa ra biến môi trường (`code/.env`), có default trong compose | ⚠️ default demo, phải đổi |
| Xác thực admin | 1 `ADMIN_TOKEN` qua header `X-Admin-Token` | ⚠️ không RBAC, không user/role |
| Người dùng thường (predict/review) | **Không có auth** | ⚠️ ai vào được mạng cũng gọi được |
| Mật khẩu Postgres/MinIO/Grafana | default (`skin_pass`, `minioadmin`, `admin`) | ⚠️ phải đổi trước deploy |
| TLS/HTTPS | Không (HTTP nội bộ) | ⚠️ cần reverse proxy + TLS khi public |
| Pentest / OWASP scan | Chưa chạy | ❌ chưa làm |

→ Hệ thống hiện ở mức **demo nội bộ**, **chưa** dành cho internet/production.

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

1. **Đổi toàn bộ mật khẩu default** (qua `.env`) — quan trọng nhất.
2. **Auth thật cho người dùng** (JWT/OAuth) thay cho "không auth" + **RBAC** thay cho 1 token.
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
Hệ thống **đã externalize bí mật + tài liệu hóa** mô hình bảo mật, nhưng vẫn là **demo-grade** (default password, không RBAC, không TLS, chưa pentest). Khai rõ điều này; coi mục 3 là việc bắt buộc cho production.
