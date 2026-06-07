import asyncio
import logging
from datetime import datetime, timezone

from app.repositories import config_repository, monitoring_repository, run_repository
from app.services import prefect_trigger, retrain_service

logger = logging.getLogger("auto_trigger")

_last_trigger = None


def _cooldown_ok(trig):
    cooldown_min = trig.get("cooldown_minutes", 2)
    candidates = [t for t in [run_repository.last_triggered_at(), _last_trigger] if t is not None]
    if not candidates:
        return True
    elapsed_min = (datetime.now(timezone.utc) - max(candidates)).total_seconds() / 60.0
    return elapsed_min >= cooldown_min


def _should_trigger():
    config = config_repository.get_config()
    if not config.get("auto_trigger_enabled"):
        return False, "disabled"

    trig = config.get("trigger", {})
    stats = monitoring_repository.summary(trig.get("auto_window", 50))
    if stats["total"] < trig.get("min_samples", 10):
        return False, "not_enough_samples"

    low_thr = trig.get("low_confidence_rate_threshold", 0.30)
    drift_thr = trig.get("drift_rate_threshold", 0.30)
    if stats["low_confidence_rate"] <= low_thr and stats["drift_rate"] <= drift_thr:
        return False, "no_signal"

    if not _cooldown_ok(trig):
        return False, "cooldown"

    return True, f"low_conf={stats['low_confidence_rate']:.2f} drift={stats['drift_rate']:.2f}"


def _trigger():
    global _last_trigger
    _last_trigger = datetime.now(timezone.utc)
    try:
        prefect_trigger.trigger_retraining("auto")
    except Exception:
        retrain_service.run("auto")


def _interval():
    return config_repository.get_config().get("trigger", {}).get("auto_check_interval_seconds", 30)


async def loop():
    logger.info("Auto-trigger loop khoi dong.")
    while True:
        try:
            ok, reason = await asyncio.to_thread(_should_trigger)
            if ok:
                logger.warning("Auto-trigger retrain: %s", reason)
                await asyncio.to_thread(_trigger)
        except Exception as err:
            logger.warning("auto_trigger loop loi: %s", err)
        interval = await asyncio.to_thread(_interval)
        await asyncio.sleep(interval)
