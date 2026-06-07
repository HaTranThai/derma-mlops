from app.db.database import pool

QUEUE_SQL = """
SELECT p.prediction_id, p.created_at, p.image_key, p.predicted_class, p.confidence
FROM predictions p
LEFT JOIN reviews r ON r.prediction_id = p.prediction_id
WHERE p.is_low_confidence = true AND r.id IS NULL
ORDER BY p.created_at DESC
LIMIT %(limit)s OFFSET %(offset)s
"""

QUEUE_COUNT_SQL = """
SELECT count(*) AS total
FROM predictions p
LEFT JOIN reviews r ON r.prediction_id = p.prediction_id
WHERE p.is_low_confidence = true AND r.id IS NULL
"""

SUBMIT_SQL = """
INSERT INTO reviews (prediction_id, review_label, review_status, reviewer, reviewed_at)
VALUES (%(prediction_id)s, %(review_label)s, 'reviewed', %(reviewer)s, now())
ON CONFLICT (prediction_id) DO UPDATE
SET review_label = EXCLUDED.review_label,
    review_status = 'reviewed',
    reviewer = EXCLUDED.reviewer,
    reviewed_at = now()
"""

REVIEWED_SQL = """
SELECT r.prediction_id, r.review_label, r.review_status, r.reviewer, r.reviewed_at,
       p.predicted_class, p.confidence, p.image_key
FROM reviews r
JOIN predictions p ON p.prediction_id = r.prediction_id
ORDER BY r.reviewed_at DESC NULLS LAST
LIMIT %(limit)s OFFSET %(offset)s
"""

REVIEWED_COUNT_SQL = "SELECT count(*) AS total FROM reviews"


def list_queue(limit, offset):
    with pool.connection() as conn:
        return conn.execute(QUEUE_SQL, {"limit": limit, "offset": offset}).fetchall()


def count_queue():
    with pool.connection() as conn:
        row = conn.execute(QUEUE_COUNT_SQL).fetchone()
    return row["total"]


def submit_review(prediction_id, review_label, reviewer):
    with pool.connection() as conn:
        conn.execute(SUBMIT_SQL, {
            "prediction_id": prediction_id,
            "review_label": review_label,
            "reviewer": reviewer,
        })


def list_reviews(limit, offset):
    with pool.connection() as conn:
        return conn.execute(REVIEWED_SQL, {"limit": limit, "offset": offset}).fetchall()


def count_reviews():
    with pool.connection() as conn:
        row = conn.execute(REVIEWED_COUNT_SQL).fetchone()
    return row["total"]
