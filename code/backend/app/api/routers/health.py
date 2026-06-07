from fastapi import APIRouter, Request

from app.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request):
    model_service = request.app.state.model_service
    if model_service is None:
        return HealthResponse(status="model_not_loaded", model_version="none")
    return HealthResponse(status="ok", model_version=model_service.model_version)
