from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from app.api.deps import get_current_user
from app.api.schemas import PredictionList, PredictionRecord
from app.repositories import prediction_repository

router = APIRouter()


def image_path(prediction_id):
    return f"/api/img/{prediction_id}"


@router.get("/predictions", response_model=PredictionList, dependencies=[Depends(get_current_user)])
def list_predictions(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    offset = (page - 1) * limit
    rows = prediction_repository.list_predictions(limit, offset)
    total = prediction_repository.count_predictions()
    items = [_to_record(row) for row in rows]
    return PredictionList(items=items, total=total, page=page, limit=limit)


@router.get("/predictions/{prediction_id}", response_model=PredictionRecord, dependencies=[Depends(get_current_user)])
def get_prediction(prediction_id: str):
    row = prediction_repository.get_prediction(prediction_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy prediction")
    return _to_record(row)


@router.get("/predictions/{prediction_id}/image")
def prediction_image(request: Request, prediction_id: str):
    storage = request.app.state.storage
    row = prediction_repository.get_prediction(prediction_id)
    if row is None or storage is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh")
    try:
        data, content_type = storage.get_object(row["image_key"])
    except Exception:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh")
    return Response(content=data, media_type=content_type)


def _to_record(row):
    return PredictionRecord(
        prediction_id=row["prediction_id"],
        created_at=row["created_at"],
        predicted_class=row["predicted_class"],
        confidence=float(row["confidence"]),
        top_k=row["top_k"],
        latency_ms=row["latency_ms"],
        model_version=row["model_version"],
        data_version=row["data_version"],
        is_low_confidence=row["is_low_confidence"],
        image_url=image_path(row["prediction_id"]),
    )
