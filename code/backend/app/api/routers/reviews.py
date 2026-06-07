from fastapi import APIRouter, HTTPException, Query, Request

from app.api.schemas import (
    ReviewList,
    ReviewQueueItem,
    ReviewQueueList,
    ReviewRecord,
    SubmitReviewRequest,
)
from app.repositories import prediction_repository, review_repository

router = APIRouter()


def _image_url(prediction_id):
    return f"/api/img/{prediction_id}"


@router.get("/reviews/queue", response_model=ReviewQueueList)
def review_queue(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    offset = (page - 1) * limit
    rows = review_repository.list_queue(limit, offset)
    total = review_repository.count_queue()
    items = [
        ReviewQueueItem(
            prediction_id=row["prediction_id"],
            created_at=row["created_at"],
            predicted_class=row["predicted_class"],
            confidence=float(row["confidence"]),
            image_url=_image_url(row["prediction_id"]),
        )
        for row in rows
    ]
    return ReviewQueueList(items=items, total=total, page=page, limit=limit)


@router.post("/reviews", status_code=201)
def submit_review(request: Request, payload: SubmitReviewRequest):
    model_service = request.app.state.model_service
    if model_service is not None and payload.review_label not in model_service.classes:
        raise HTTPException(status_code=400, detail="Nhãn review không hợp lệ")
    if prediction_repository.get_prediction(payload.prediction_id) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy prediction để review")
    review_repository.submit_review(payload.prediction_id, payload.review_label, payload.reviewer)
    return {"status": "ok", "prediction_id": payload.prediction_id}


@router.get("/reviews", response_model=ReviewList)
def list_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    offset = (page - 1) * limit
    rows = review_repository.list_reviews(limit, offset)
    total = review_repository.count_reviews()
    items = [
        ReviewRecord(
            prediction_id=row["prediction_id"],
            review_label=row["review_label"],
            review_status=row["review_status"],
            reviewer=row["reviewer"],
            reviewed_at=row["reviewed_at"],
            predicted_class=row["predicted_class"],
            confidence=float(row["confidence"]),
            image_url=_image_url(row["prediction_id"]),
        )
        for row in rows
    ]
    return ReviewList(items=items, total=total, page=page, limit=limit)
