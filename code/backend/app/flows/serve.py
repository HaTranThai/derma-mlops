import logging

from app.flows.retraining_flow import retraining_flow

logger = logging.getLogger("serve")

DEFAULT_CRON = "0 2 1 * *"


def _load_cron():
    try:
        from app.db.database import pool
        from app.repositories import config_repository

        pool.open()
        cron = config_repository.get_config().get("trigger", {}).get("schedule_cron")
        return cron or DEFAULT_CRON
    except Exception as err:
        logger.warning("Khong doc duoc schedule_cron, dung mac dinh %s: %s", DEFAULT_CRON, err)
        return DEFAULT_CRON


if __name__ == "__main__":
    cron = _load_cron()
    logger.warning("Serve retraining flow voi cron=%s (tin hieu S4)", cron)
    retraining_flow.serve(
        name="default",
        cron=cron,
        parameters={"trigger_reason": "S4"},
    )
