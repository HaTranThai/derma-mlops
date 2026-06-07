from psycopg.types.json import Jsonb

from app.db.database import pool

INSERT_SQL = """
INSERT INTO predictions
    (prediction_id, image_key, image_width, image_height, predicted_class, confidence,
     top_k, latency_ms, model_version, data_version, is_low_confidence, is_drift_suspected,
     brightness_score, blur_score, source)
VALUES
    (%(prediction_id)s, %(image_key)s, %(image_width)s, %(image_height)s, %(predicted_class)s,
     %(confidence)s, %(top_k)s, %(latency_ms)s, %(model_version)s, %(data_version)s,
     %(is_low_confidence)s, %(is_drift_suspected)s, %(brightness_score)s, %(blur_score)s,
     %(source)s)
"""

SELECT_COLUMNS = """
prediction_id, created_at, image_key, predicted_class, confidence, top_k,
latency_ms, model_version, data_version, is_low_confidence
"""

LIST_SQL = f"""
SELECT {SELECT_COLUMNS}
FROM predictions
ORDER BY created_at DESC
LIMIT %(limit)s OFFSET %(offset)s
"""

GET_SQL = f"""
SELECT {SELECT_COLUMNS}
FROM predictions
WHERE prediction_id = %(prediction_id)s
"""


def insert_prediction(record):
    params = dict(record)
    params["top_k"] = Jsonb(record["top_k"])
    with pool.connection() as conn:
        conn.execute(INSERT_SQL, params)


def list_predictions(limit, offset):
    with pool.connection() as conn:
        return conn.execute(LIST_SQL, {"limit": limit, "offset": offset}).fetchall()


def count_predictions():
    with pool.connection() as conn:
        row = conn.execute("SELECT count(*) AS total FROM predictions").fetchone()
    return row["total"]


def get_prediction(prediction_id):
    with pool.connection() as conn:
        return conn.execute(GET_SQL, {"prediction_id": prediction_id}).fetchone()
