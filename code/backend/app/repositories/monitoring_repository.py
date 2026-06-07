from app.db.database import pool

SUMMARY_SQL = """
WITH recent AS (
    SELECT confidence, latency_ms, is_low_confidence, is_drift_suspected
    FROM predictions ORDER BY created_at DESC LIMIT %(window)s
)
SELECT
    count(*) AS total,
    coalesce(avg(confidence), 0) AS avg_confidence,
    coalesce(avg(latency_ms), 0) AS avg_latency_ms,
    coalesce(avg(CASE WHEN is_low_confidence THEN 1.0 ELSE 0.0 END), 0) AS low_confidence_rate,
    coalesce(avg(CASE WHEN is_drift_suspected THEN 1.0 ELSE 0.0 END), 0) AS drift_rate
FROM recent
"""

CLASS_DIST_SQL = """
WITH recent AS (
    SELECT predicted_class FROM predictions ORDER BY created_at DESC LIMIT %(window)s
)
SELECT predicted_class, count(*) AS count
FROM recent GROUP BY predicted_class ORDER BY count DESC
"""

QUEUE_COUNT_SQL = """
SELECT count(*) AS total
FROM predictions p
LEFT JOIN reviews r ON r.prediction_id = p.prediction_id
WHERE p.is_low_confidence = true AND r.id IS NULL
"""


def summary(window):
    with pool.connection() as conn:
        stats = conn.execute(SUMMARY_SQL, {"window": window}).fetchone()
        distribution = conn.execute(CLASS_DIST_SQL, {"window": window}).fetchall()
        queue = conn.execute(QUEUE_COUNT_SQL).fetchone()
    return {
        "window": window,
        "total": stats["total"],
        "avg_confidence": float(stats["avg_confidence"]),
        "avg_latency_ms": float(stats["avg_latency_ms"]),
        "low_confidence_rate": float(stats["low_confidence_rate"]),
        "drift_rate": float(stats["drift_rate"]),
        "class_distribution": [
            {"label": row["predicted_class"], "count": row["count"]} for row in distribution
        ],
        "review_queue": queue["total"],
    }
