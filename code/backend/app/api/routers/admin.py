from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request

from app.core.config import settings
from app.repositories import config_repository, run_repository
from app.services import mlflow_service, prefect_trigger, retrain_service
from app.services.gradcam_service import GradCAM
from app.services.model_service import ModelService

router = APIRouter(prefix="/admin")


def require_admin(x_admin_token: str = Header(default="")):
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Sai admin token")


@router.post("/seed-models", dependencies=[Depends(require_admin)])
def seed_models():
    return {"created": mlflow_service.seed_models()}


@router.get("/models", dependencies=[Depends(require_admin)])
def list_models():
    return {"model_name": settings.MLFLOW_MODEL_NAME, "versions": mlflow_service.list_versions()}


@router.get("/config", dependencies=[Depends(require_admin)])
def get_config():
    return config_repository.get_config()


@router.put("/config", dependencies=[Depends(require_admin)])
def update_config(value: dict = Body(...)):
    return config_repository.set_config(value)


@router.post("/retrain", dependencies=[Depends(require_admin)])
def retrain():
    try:
        run = prefect_trigger.trigger_retraining("manual")
        return {"status": "triggered", "via": "prefect", "run": run}
    except Exception:
        result = retrain_service.run("manual")
        return {"status": "done", "via": "fallback", "result": result}


@router.post("/promote/{version}", dependencies=[Depends(require_admin)])
def promote(version: int):
    mlflow_service.promote_version(version)
    return {"status": "ok", "promoted_version": version}


@router.get("/gate", dependencies=[Depends(require_admin)])
def gate_preview():
    production = mlflow_service.get_production()
    candidate = mlflow_service.get_candidate()
    if production is None or candidate is None:
        return {"production": production, "candidate": candidate, "gate": None}
    config = config_repository.get_config()
    gate = mlflow_service.evaluate_gate(production["metrics"], candidate["metrics"], config.get("promote_rules"))
    return {"production": production, "candidate": candidate, "gate": gate}


@router.get("/runs", dependencies=[Depends(require_admin)])
def list_runs():
    rows = run_repository.list_runs()
    return {"runs": [dict(row) for row in rows]}


@router.post("/reload-model", dependencies=[Depends(require_admin)])
def reload_model(request: Request, model_path: str = Body(default=None, embed=True)):
    try:
        model_service = ModelService(model_path) if model_path else ModelService()
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Không nạp được model: {err}")
    request.app.state.model_service = model_service
    request.app.state.gradcam = GradCAM(model_service.model, model_service.target_layer)
    return {"status": "ok", "model_version": model_service.model_version}
