from psycopg.types.json import Jsonb

from app.db.database import pool

RETRAIN_CONFIG_KEY = "retrain_config"

DEFAULT_RETRAIN_CONFIG = {
    "mode": "artifact",
    "auto_trigger_enabled": False,
    "trigger": {
        "min_reviewed_images": 100,
        "low_confidence_rate_threshold": 0.30,
        "drift_rate_threshold": 0.30,
        "min_samples": 10,
        "auto_window": 50,
        "perf_min_accuracy": 0.70,
        "perf_min_reviews": 20,
        "perf_window": 100,
        "schedule_cron": "0 2 1 * *",
        "auto_check_interval_seconds": 30,
        "cooldown_minutes": 2,
    },
    "smoke": {
        "epochs": 3,
        "batch_size": 16,
        "learning_rate": 0.001,
        "freeze_backbone": True,
        "val_fraction": 0.3,
        "seed": 42,
        "version_tag": "smoke",
    },
    "promote_rules": [
        {"metric": "macro_f1", "rule": "not_worse"},
        {"metric": "melanoma_recall", "rule": "not_worse"},
        {"metric": "accuracy", "rule": "tolerance", "max_drop": 0.02},
    ],
}


def get_config(key=RETRAIN_CONFIG_KEY):
    with pool.connection() as conn:
        row = conn.execute("SELECT value FROM system_config WHERE key = %s", (key,)).fetchone()
    if row is None:
        return DEFAULT_RETRAIN_CONFIG
    return row["value"]


def set_config(value, key=RETRAIN_CONFIG_KEY, updated_by="admin"):
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO system_config (key, value, updated_by)
            VALUES (%s, %s, %s)
            ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value, updated_at = now(), updated_by = EXCLUDED.updated_by
            """,
            (key, Jsonb(value), updated_by),
        )
    return value
