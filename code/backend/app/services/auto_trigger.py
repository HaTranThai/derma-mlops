import asyncio
import logging
from datetime import datetime, timezone

from app.repositories import config_repository, monitoring_repository, review_repository, run_repository
from app.services import prefect_trigger, retrain_service

logger = logging.getLogger("auto_trigger")

_last_trigger = None


def _last_retrain_time():
    candidates = [t for t in [run_repository.last_triggered_at(), _last_trigger] if t is not None]
    return max(candidates) if candidates else None


def _cooldown_ok(trig, last_retrain):
    if last_retrain is None:
        return True
    elapsed_min = (datetime.now(timezone.utc) - last_retrain).total_seconds() / 60.0
    return elapsed_min >= trig.get("cooldown_minutes", 2)


def _signal_reviewed_data(trig, last_retrain):
    threshold = trig.get("min_reviewed_images", 100)
    count = review_repository.count_uningested_reviews()
    return count >= threshold, {"uningested_reviews": count, "threshold": threshold}


def _signal_drift(trig):
    stats = monitoring_repository.summary(trig.get("auto_window", 50))
    min_samples = trig.get("min_samples", 10)
    drift_thr = trig.get("drift_rate_threshold", 0.30)
    low_thr = trig.get("low_confidence_rate_threshold", 0.30)
    if stats["total"] < min_samples:
        return False, {"total": stats["total"], "min_samples": min_samples, "note": "not_enough_samples"}
    fired = stats["drift_rate"] > drift_thr or stats["low_confidence_rate"] > low_thr
    return fired, {
        "drift_rate": round(stats["drift_rate"], 3),
        "low_confidence_rate": round(stats["low_confidence_rate"], 3),
        "drift_threshold": drift_thr,
        "low_confidence_threshold": low_thr,
    }


def _signal_performance(trig):
    min_reviews = trig.get("perf_min_reviews", 20)
    min_acc = trig.get("perf_min_accuracy", 0.70)
    perf = review_repository.online_accuracy(trig.get("perf_window", 100))
    if perf["count"] < min_reviews:
        return False, {"reviewed": perf["count"], "min_reviews": min_reviews, "note": "not_enough_reviews"}
    return perf["accuracy"] < min_acc, {
        "online_accuracy": round(perf["accuracy"], 3),
        "min_accuracy": min_acc,
        "reviewed": perf["count"],
    }


def _assess(trig, last_retrain):
    signals = {
        "S1": _signal_reviewed_data(trig, last_retrain),
        "S2": _signal_drift(trig),
        "S3": _signal_performance(trig),
    }
    checks = {}
    fired = []
    for code, (ok, detail) in signals.items():
        checks[code] = {"fired": ok, **detail}
        if ok:
            fired.append(code)
    return fired, checks


def status():
    config = config_repository.get_config()
    trig = config.get("trigger", {})
    last_retrain = _last_retrain_time()
    fired, checks = _assess(trig, last_retrain)
    cooldown_ok = _cooldown_ok(trig, last_retrain)
    enabled = bool(config.get("auto_trigger_enabled"))
    would_trigger = enabled and bool(fired) and cooldown_ok
    return {
        "enabled": enabled,
        "fired": fired,
        "cooldown_ok": cooldown_ok,
        "would_trigger": would_trigger,
        "checks": checks,
    }


def evaluate():
    config = config_repository.get_config()
    if not config.get("auto_trigger_enabled"):
        return [], {"enabled": False}

    trig = config.get("trigger", {})
    last_retrain = _last_retrain_time()
    fired, checks = _assess(trig, last_retrain)

    if not fired:
        return [], {"enabled": True, "checks": checks, "note": "no_signal"}
    if not _cooldown_ok(trig, last_retrain):
        return [], {"enabled": True, "checks": checks, "fired": fired, "note": "cooldown"}
    return fired, {"enabled": True, "checks": checks, "fired": fired}


def _trigger(reason):
    global _last_trigger
    _last_trigger = datetime.now(timezone.utc)
    retrain_service.trigger(reason)


def _interval():
    return config_repository.get_config().get("trigger", {}).get("auto_check_interval_seconds", 30)


async def loop():
    logger.info("Auto-trigger loop khoi dong (S1-S3; S4 do Prefect cron).")
    while True:
        try:
            fired, detail = await asyncio.to_thread(evaluate)
            if fired:
                reason = "+".join(fired)
                logger.warning("Auto-trigger retrain: %s | %s", reason, detail.get("checks"))
                await asyncio.to_thread(_trigger, reason)
        except Exception as err:
            logger.warning("auto_trigger loop loi: %s", err)
        interval = await asyncio.to_thread(_interval)
        await asyncio.sleep(interval)
