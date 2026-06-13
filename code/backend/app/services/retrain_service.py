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


def train_candidate(trigger_reason="manual"):
    from app.services import trainer

    return _with_retry(lambda: trainer.train_smoke(config_repository.get_config(), trigger_reason), retries=1)


def trigger(trigger_reason="manual"):
    """Chạy ở API: auto-ingest review mới vào tập train + bỏ qua nếu data không đổi,
    rồi đẩy retrain (Prefect, fallback chạy thẳng). Ingest phải chạy ở api (rw data + dvc)."""
    pool.open()
    config = config_repository.get_config()
    mode = config.get("mode", "artifact")

    ingest_result = None
    if mode == "smoke":
        try:
            from app.services import ingest_service

            ingest_result = ingest_service.ingest_reviews()
            logger.warning("Auto-ingest truoc retrain: ingested=%s leaked=%s data_version=%s",
                           ingest_result.get("ingested"), ingest_result.get("leaked"), ingest_result.get("data_version"))
        except Exception as err:
            logger.warning("Auto-ingest loi: %s", err)

        current_dv = (ingest_result or {}).get("data_version")
        last_dv = config_repository.get_last_trained_data_version()
        if trigger_reason != "manual" and current_dv and current_dv == last_dv:
            detail = {"status": "skip_no_new_data", "data_version": current_dv,
                      "note": "data khong doi ke tu lan train truoc -> bo qua retrain (chi canh bao)"}
            run_repository.insert_run({
                "trigger_reason": trigger_reason, "mode": mode, "reviewed_count": gather_reviewed(),
                "production_tag": None, "candidate_tag": None, "gate_passed": None,
                "promoted": False, "detail": detail,
            })
            logger.warning("SKIP retrain (%s): data khong doi -> khong train", trigger_reason)
            return {"status": "skipped", "reason": "no_new_data", "data_version": current_dv, "ingest": ingest_result}

    from app.services import prefect_trigger

    try:
        run_info = prefect_trigger.trigger_retraining(trigger_reason)
        return {"status": "triggered", "via": "prefect", "run": run_info, "ingest": ingest_result}
    except Exception:
        result = run(trigger_reason)
        return {"status": "done", "via": "fallback", "result": result, "ingest": ingest_result}


def run(trigger_reason="manual"):
    pool.open()
    config = config_repository.get_config()
    mode = config.get("mode", "artifact")
    reviewed = gather_reviewed()

    trained = None
    if mode == "smoke":
        trained = train_candidate(trigger_reason)
        candidate = trained["best"]
        production = mlflow_service.get_production()
        config_repository.set_last_trained_data_version(trained.get("data_version"))
        logger.warning("Smoke: train %s kien truc, best=%s (macro_f1=%.3f)",
                       len(trained["candidates"]), candidate.get("arch"), candidate["metrics"]["macro_f1"])
    else:
        production, candidate = select_models()

    if production is not None:
        try:
            from app.services import model_store, trainer
            prod_ck = model_store.load_production_checkpoint()
            prod_val = trainer.evaluate_checkpoint_on_val(prod_ck)
            if prod_val:
                production = {**production, "metrics": prod_val, "metrics_source": "system_val"}
                logger.warning("Gate cung nguon: Production re-eval tren data/val = %s", prod_val)
        except Exception as err:
            logger.warning("Re-eval Production that bai, dung metric registry: %s", err)

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
