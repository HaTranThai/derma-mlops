import logging
import time

from app.db.database import pool
from app.repositories import config_repository, review_repository, run_repository
from app.services import mlflow_service

logger = logging.getLogger("retraining")


def _with_retry(func, retries=2, delay=2):
    last_error = None
    for attempt in range(retries + 1):
        try:
            return func()
        except Exception as err:
            last_error = err
            logger.warning("Task that bai (lan %s): %s", attempt + 1, err)
            time.sleep(delay)
    raise last_error


def gather_reviewed():
    return _with_retry(review_repository.count_reviews)


def select_models():
    return mlflow_service.get_production(), mlflow_service.get_candidate()


def run_gate(production, candidate, rules):
    return mlflow_service.evaluate_gate(production["metrics"], candidate["metrics"], rules)


def promote(version):
    _with_retry(lambda: mlflow_service.promote_version(version))


def train_candidate():
    from app.services import trainer

    return _with_retry(lambda: trainer.train_smoke(config_repository.get_config()), retries=1)


def run(trigger_reason="manual"):
    pool.open()
    config = config_repository.get_config()
    mode = config.get("mode", "artifact")
    reviewed = gather_reviewed()

    trained = None
    if mode == "smoke":
        trained = train_candidate()
        logger.warning("Smoke da train candidate moi: %s", trained)

    production, candidate = select_models()

    if production is None or candidate is None:
        result = {
            "status": "no_candidate",
            "reviewed_count": reviewed,
            "production": production,
            "candidate": candidate,
        }
        run_repository.insert_run({
            "trigger_reason": trigger_reason,
            "mode": mode,
            "reviewed_count": reviewed,
            "production_tag": production["tag"] if production else None,
            "candidate_tag": candidate["tag"] if candidate else None,
            "gate_passed": None,
            "promoted": False,
            "detail": result,
        })
        return result

    gate = run_gate(production, candidate, config.get("promote_rules"))
    promoted = False
    if gate["passed"]:
        promote(candidate["version"])
        promoted = True

    result = {
        "status": "done",
        "reviewed_count": reviewed,
        "production": production,
        "candidate": candidate,
        "gate": gate,
        "promoted": promoted,
        "trained": trained,
    }
    run_repository.insert_run({
        "trigger_reason": trigger_reason,
        "mode": mode,
        "reviewed_count": reviewed,
        "production_tag": production["tag"],
        "candidate_tag": candidate["tag"],
        "gate_passed": gate["passed"],
        "promoted": promoted,
        "detail": result,
    })
    return result
