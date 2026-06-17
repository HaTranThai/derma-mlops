from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.deps import require_admin
from app.core.config import settings
from app.repositories import config_repository, run_repository, user_repository
from app.services import auto_trigger, eval_service, ingest_service, mlflow_service, prefect_trigger, retrain_service
from app.services.gradcam_service import GradCAM
from app.services.model_service import ModelService

router = APIRouter(prefix="/admin")

ROLES = {"admin", "doctor", "nurse"}


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "doctor"


class PasswordRequest(BaseModel):
    password: str


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


@router.post("/ingest-reviews", dependencies=[Depends(require_admin)])
def ingest_reviews():
    return ingest_service.ingest_reviews()


@router.post("/retrain", dependencies=[Depends(require_admin)])
def retrain():
    return retrain_service.trigger("manual")


@router.post("/promote/{version}", dependencies=[Depends(require_admin)])
def promote(version: int):
    mlflow_service.promote_version(version)
    return {"status": "ok", "promoted_version": version}


@router.post("/eval-production-val", dependencies=[Depends(require_admin)])
def eval_production_val(request: Request):
    model_service = request.app.state.model_service
    if model_service is None:
        raise HTTPException(status_code=503, detail="Model chưa được nạp")
    production = mlflow_service.get_production()
    if production is None:
        raise HTTPException(status_code=404, detail="Chưa có model Production")
    metrics = eval_service.evaluate_on_val(model_service, settings.DATASET_VAL_PATH)
    mlflow_service.update_run_metrics(production["version"], metrics)
    return {
        "version": production["version"],
        "tag": production["tag"],
        "model_version": model_service.model_version,
        "val_metrics": metrics,
    }


@router.get("/gate", dependencies=[Depends(require_admin)])
def gate_preview():
    production = mlflow_service.get_production()
    candidate = mlflow_service.get_candidate()
    if production is None or candidate is None:
        return {"production": production, "candidate": candidate, "gate": None}
    config = config_repository.get_config()
    gate = mlflow_service.evaluate_gate(production["metrics"], candidate["metrics"], config.get("promote_rules"))
    return {"production": production, "candidate": candidate, "gate": gate}


@router.get("/trigger-status", dependencies=[Depends(require_admin)])
def trigger_status():
    return auto_trigger.status()


@router.get("/runs", dependencies=[Depends(require_admin)])
def list_runs():
    rows = run_repository.list_runs()
    return {"runs": [dict(row) for row in rows]}


@router.get("/users", dependencies=[Depends(require_admin)])
def list_users():
    return {"users": user_repository.list_users()}


@router.post("/users", status_code=201)
def create_user(payload: CreateUserRequest, _admin=Depends(require_admin)):
    username = payload.username.strip()
    if not username or not payload.password:
        raise HTTPException(status_code=400, detail="Thiếu tài khoản hoặc mật khẩu")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu tối thiểu 6 ký tự")
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Role không hợp lệ (cho phép: {', '.join(sorted(ROLES))})")
    if user_repository.get_user(username) is not None:
        raise HTTPException(status_code=409, detail="Tài khoản đã tồn tại")
    user_repository.create_user(username, payload.password, payload.role)
    return {"username": username, "role": payload.role}


@router.put("/users/{username}/password")
def reset_password(username: str, payload: PasswordRequest, _admin=Depends(require_admin)):
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu tối thiểu 6 ký tự")
    if not user_repository.set_password(username, payload.password):
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    return {"status": "ok", "username": username}


@router.delete("/users/{username}")
def delete_user(username: str, admin=Depends(require_admin)):
    target = user_repository.get_user(username)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    if username == admin["username"]:
        raise HTTPException(status_code=400, detail="Không thể tự xoá tài khoản đang đăng nhập")
    if target["role"] == "admin" and user_repository.count_admins() <= 1:
        raise HTTPException(status_code=400, detail="Không thể xoá admin cuối cùng")
    user_repository.delete_user(username)
    return {"status": "ok", "deleted": username}


@router.post("/reload-model", dependencies=[Depends(require_admin)])
def reload_model(
    request: Request,
    model_path: str = Body(default=None, embed=True),
    model_key: str = Body(default=None, embed=True),
):
    try:
        model_service = ModelService(model_path=model_path, model_key=model_key)
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Không nạp được model: {err}")
    request.app.state.model_service = model_service
    request.app.state.gradcam = GradCAM(model_service.model, model_service.target_layer)
    return {"status": "ok", "model_version": model_service.model_version}
