from psycopg.types.json import Jsonb

from app.db.database import pool

INSERT_SQL = """
INSERT INTO retraining_runs
    (trigger_reason, mode, reviewed_count, production_tag, candidate_tag, gate_passed, promoted, detail)
VALUES
    (%(trigger_reason)s, %(mode)s, %(reviewed_count)s, %(production_tag)s, %(candidate_tag)s,
     %(gate_passed)s, %(promoted)s, %(detail)s)
RETURNING id, triggered_at
"""

LIST_SQL = """
SELECT id, triggered_at, trigger_reason, mode, reviewed_count,
       production_tag, candidate_tag, gate_passed, promoted
FROM retraining_runs
ORDER BY triggered_at DESC
LIMIT %(limit)s
"""


def insert_run(record):
    params = dict(record)
    params["detail"] = Jsonb(record.get("detail", {}))
    with pool.connection() as conn:
        return conn.execute(INSERT_SQL, params).fetchone()


def list_runs(limit=50):
    with pool.connection() as conn:
        return conn.execute(LIST_SQL, {"limit": limit}).fetchall()


def last_triggered_at():
    with pool.connection() as conn:
        row = conn.execute("SELECT max(triggered_at) AS t FROM retraining_runs").fetchone()
    return row["t"]
