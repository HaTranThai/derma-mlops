import math

from app.db.database import pool

BASELINE_DIST_SQL = """
SELECT predicted_class, count(*) AS count FROM predictions GROUP BY predicted_class
"""

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


def _proportions(rows, classes):
    total = sum(row["count"] for row in rows) or 1
    by_class = {row["predicted_class"]: row["count"] / total for row in rows}
    return {cls: by_class.get(cls, 0.0) for cls in classes}


def _psi(recent, baseline):
    psi = 0.0
    for cls in set(recent) | set(baseline):
        r = max(recent.get(cls, 0.0), 1e-4)
        b = max(baseline.get(cls, 0.0), 1e-4)
        psi += (r - b) * math.log(r / b)
    return psi


def _psi_level(psi):
    if psi < 0.1:
        return "none"
    if psi < 0.25:
        return "moderate"
    return "significant"


def summary(window):
    with pool.connection() as conn:
        stats = conn.execute(SUMMARY_SQL, {"window": window}).fetchone()
        distribution = conn.execute(CLASS_DIST_SQL, {"window": window}).fetchall()
        baseline = conn.execute(BASELINE_DIST_SQL).fetchall()
        queue = conn.execute(QUEUE_COUNT_SQL).fetchone()

    classes = {row["predicted_class"] for row in distribution} | {row["predicted_class"] for row in baseline}
    psi = _psi(_proportions(distribution, classes), _proportions(baseline, classes))

    return {
        "window": window,
        "total": stats["total"],
        "avg_confidence": float(stats["avg_confidence"]),
        "avg_latency_ms": float(stats["avg_latency_ms"]),
        "low_confidence_rate": float(stats["low_confidence_rate"]),
        "input_quality_anomaly_rate": float(stats["drift_rate"]),
        "drift_rate": float(stats["drift_rate"]),
        "population_drift_psi": round(psi, 4),
        "population_drift_level": _psi_level(psi),
        "class_distribution": [
            {"label": row["predicted_class"], "count": row["count"]} for row in distribution
        ],
        "review_queue": queue["total"],
    }
