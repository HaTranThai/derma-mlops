import json
import os
import tempfile

import mlflow
from mlflow.tracking import MlflowClient

from app.core.config import settings

mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)

MODEL_NAME = settings.MLFLOW_MODEL_NAME

SEED_MODELS = [
    {
        "version_tag": "v1",
        "metrics": {"macro_f1": 0.4066, "melanoma_recall": 0.4301, "accuracy": 0.7410},
        "stage": "Production",
    },
    {
        "version_tag": "v2",
        "metrics": {"macro_f1": 0.7145, "melanoma_recall": 0.5806, "accuracy": 0.8410},
        "stage": "Staging",
    },
]

PROMOTE_RULES = [
    {"metric": "macro_f1", "rule": "not_worse"},
    {"metric": "melanoma_recall", "rule": "not_worse"},
    {"metric": "accuracy", "rule": "tolerance", "max_drop": 0.02},
]


def _client():
    return MlflowClient(tracking_uri=settings.MLFLOW_TRACKING_URI)


def _ensure_registered_model(client):
    try:
        client.get_registered_model(MODEL_NAME)
    except Exception:
        client.create_registered_model(MODEL_NAME)


def _log_artifact(version_tag, metrics):
    if version_tag == "v2" and os.path.exists(settings.MODEL_PATH):
        mlflow.log_artifact(settings.MODEL_PATH, artifact_path="model")
        return
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "metrics.json")
        with open(path, "w") as handle:
            json.dump(metrics, handle)
        mlflow.log_artifact(path, artifact_path="model")


def _seed_one(client, spec):
    mlflow.set_experiment(settings.MLFLOW_EXPERIMENT)
    with mlflow.start_run(run_name=f"seed_{spec['version_tag']}") as run:
        mlflow.log_params({"architecture": "efficientnet_b0", "version": spec["version_tag"], "image_size": 224})
        mlflow.log_metrics(spec["metrics"])
        _log_artifact(spec["version_tag"], spec["metrics"])
        run_id = run.info.run_id
    version = client.create_model_version(
        name=MODEL_NAME,
        source=f"runs:/{run_id}/model",
        run_id=run_id,
        tags={"version_tag": spec["version_tag"]},
    )
    client.transition_model_version_stage(MODEL_NAME, version.version, spec["stage"])
    return {"version": version.version, "tag": spec["version_tag"], "stage": spec["stage"]}


def seed_models():
    client = _client()
    _ensure_registered_model(client)
    existing = {mv.tags.get("version_tag"): mv for mv in client.search_model_versions(f"name='{MODEL_NAME}'")}
    result = []
    for spec in SEED_MODELS:
        tag = spec["version_tag"]
        if tag in existing:
            version = existing[tag].version
            client.transition_model_version_stage(MODEL_NAME, version, spec["stage"])
            result.append({"version": int(version), "tag": tag, "stage": spec["stage"], "created": False})
        else:
            result.append({**_seed_one(client, spec), "created": True})
    return result


def get_candidate():
    for item in reversed(list_versions()):
        if item["stage"] == "Staging":
            return item
    return None


def list_versions():
    client = _client()
    try:
        versions = client.search_model_versions(f"name='{MODEL_NAME}'")
    except Exception:
        return []
    result = []
    for mv in versions:
        metrics = {}
        try:
            metrics = client.get_run(mv.run_id).data.metrics
        except Exception:
            pass
        result.append({
            "version": int(mv.version),
            "tag": mv.tags.get("version_tag"),
            "stage": mv.current_stage,
            "metrics": metrics,
        })
    return sorted(result, key=lambda item: item["version"])


def evaluate_gate(production_metrics, candidate_metrics, rules=None):
    rules = rules or PROMOTE_RULES
    checks = []
    passed = True
    for rule in rules:
        metric = rule["metric"]
        prod = float(production_metrics.get(metric, 0.0))
        cand = float(candidate_metrics.get(metric, 0.0))
        if rule["rule"] == "tolerance":
            ok = cand >= prod - rule.get("max_drop", 0.0)
        else:
            ok = cand >= prod - 1e-9
        checks.append({"metric": metric, "production": prod, "candidate": cand, "rule": rule["rule"], "passed": ok})
        passed = passed and ok
    return {"passed": passed, "checks": checks}


def promote_version(version):
    client = _client()
    client.transition_model_version_stage(
        MODEL_NAME, str(version), "Production", archive_existing_versions=True
    )


def get_production():
    for item in list_versions():
        if item["stage"] == "Production":
            return item
    return None
