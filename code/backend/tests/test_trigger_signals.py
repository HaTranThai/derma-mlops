from datetime import datetime, timedelta, timezone

from app.repositories import monitoring_repository, review_repository
from app.services import auto_trigger

TRIG = {
    "min_reviewed_images": 100,
    "drift_rate_threshold": 0.30,
    "low_confidence_rate_threshold": 0.30,
    "min_samples": 10,
    "auto_window": 50,
    "perf_min_accuracy": 0.70,
    "perf_min_reviews": 20,
    "perf_window": 100,
    "cooldown_minutes": 2,
    "periodic_interval_hours": 168,
}


def test_s1_fires_when_enough_reviews(monkeypatch):
    monkeypatch.setattr(review_repository, "count_uningested_reviews", lambda: 150)
    fired, _ = auto_trigger._signal_reviewed_data(TRIG, None)
    assert fired is True


def test_s1_not_fire_when_few_reviews(monkeypatch):
    monkeypatch.setattr(review_repository, "count_uningested_reviews", lambda: 5)
    fired, _ = auto_trigger._signal_reviewed_data(TRIG, None)
    assert fired is False


def test_s2_drift_fires_above_threshold(monkeypatch):
    monkeypatch.setattr(monitoring_repository, "summary",
                        lambda w: {"total": 50, "drift_rate": 0.9, "low_confidence_rate": 0.0})
    fired, _ = auto_trigger._signal_drift(TRIG)
    assert fired is True


def test_s2_not_fire_below_min_samples(monkeypatch):
    monkeypatch.setattr(monitoring_repository, "summary",
                        lambda w: {"total": 3, "drift_rate": 0.9, "low_confidence_rate": 0.9})
    fired, detail = auto_trigger._signal_drift(TRIG)
    assert fired is False
    assert detail.get("note") == "not_enough_samples"


def test_s3_fires_on_low_online_accuracy(monkeypatch):
    monkeypatch.setattr(review_repository, "online_accuracy",
                        lambda w: {"count": 30, "accuracy": 0.4})
    fired, _ = auto_trigger._signal_performance(TRIG)
    assert fired is True


def test_s3_not_fire_when_few_reviews(monkeypatch):
    monkeypatch.setattr(review_repository, "online_accuracy",
                        lambda w: {"count": 5, "accuracy": 0.1})
    fired, detail = auto_trigger._signal_performance(TRIG)
    assert fired is False
    assert detail.get("note") == "not_enough_reviews"


# Lưu ý: S4 (định kỳ) đã chuyển sang Prefect cron schedule (xem flows/serve.py),
# không còn là hàm trong auto_trigger nên không unit-test ở đây.


def test_cooldown_blocks_recent_retrain():
    recent = datetime.now(timezone.utc) - timedelta(seconds=30)
    assert auto_trigger._cooldown_ok(TRIG, recent) is False


def test_cooldown_ok_after_interval():
    old = datetime.now(timezone.utc) - timedelta(minutes=10)
    assert auto_trigger._cooldown_ok(TRIG, old) is True


def test_cooldown_ok_when_never_retrained():
    assert auto_trigger._cooldown_ok(TRIG, None) is True
