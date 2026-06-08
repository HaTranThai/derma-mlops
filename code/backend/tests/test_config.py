from app.repositories.config_repository import DEFAULT_RETRAIN_CONFIG


def test_config_has_core_keys():
    cfg = DEFAULT_RETRAIN_CONFIG
    assert cfg["mode"] in ("artifact", "smoke")
    assert "auto_trigger_enabled" in cfg
    for key in (
        "min_reviewed_images",
        "drift_rate_threshold",
        "low_confidence_rate_threshold",
        "perf_min_accuracy",
        "schedule_cron",
        "cooldown_minutes",
    ):
        assert key in cfg["trigger"], key


def test_smoke_block_present():
    smoke = DEFAULT_RETRAIN_CONFIG["smoke"]
    for key in ("epochs", "batch_size", "learning_rate", "freeze_backbone", "val_fraction"):
        assert key in smoke, key


def test_promote_rules_cover_key_metrics():
    metrics = {rule["metric"] for rule in DEFAULT_RETRAIN_CONFIG["promote_rules"]}
    assert {"macro_f1", "melanoma_recall", "accuracy"} <= metrics
