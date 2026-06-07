from pathlib import Path

from app.db.database import pool

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def init_db():
    statements = [s.strip() for s in SCHEMA_PATH.read_text().split(";") if s.strip()]
    with pool.connection() as conn:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
        conn.commit()
