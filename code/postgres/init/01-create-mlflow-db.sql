-- Tạo database riêng cho MLflow backend store (chạy khi postgres init lần đầu).
-- Với instance đã init sẵn, tạo thủ công: CREATE DATABASE mlflow;
SELECT 'CREATE DATABASE mlflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mlflow')\gexec
