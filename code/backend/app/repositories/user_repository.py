import logging

from app.db.database import pool
from app.services import auth_service

logger = logging.getLogger("users")

# Tài khoản mặc định seed khi khởi động (đổi mật khẩu ở môi trường thật).
DEFAULT_USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "doctor", "password": "doctor123", "role": "doctor"},
]


def get_user(username):
    with pool.connection() as conn:
        return conn.execute(
            "SELECT username, password_hash, role FROM users WHERE username = %s", (username,)
        ).fetchone()


def create_user(username, password, role):
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) "
            "ON CONFLICT (username) DO NOTHING",
            (username, auth_service.hash_password(password), role),
        )


def seed_users():
    for u in DEFAULT_USERS:
        if get_user(u["username"]) is None:
            create_user(u["username"], u["password"], u["role"])
            logger.warning("Seed user mac dinh: %s (role=%s)", u["username"], u["role"])
