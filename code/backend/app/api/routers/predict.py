import base64
import io
import logging
import time
import uuid
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile

from app.api.schemas import PredictResponse, TopKItem
from app.core import metrics
from app.core.config import settings
from app.repositories import prediction_repository
from app.services import drift_service
from app.services.gradcam_service import overlay_cam

logger = logging.getLogger("predict")
router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
async def predict(request: Request, file: UploadFile = File(...), source: str = Query("web")):
    model_service = request.app.state.model_service
    gradcam = request.app.state.gradcam
    storage = request.app.state.storage
    if model_service is None:
        raise HTTPException(status_code=503, detail="Model chưa được nạp")
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File phải là ảnh")

    raw = await file.read()
    try:
        image = model_service.load_image(raw)
    except Exception:
        raise HTTPException(status_code=422, detail="Không đọc được ảnh")

    start = time.time()
    tensor = model_service.preprocess(image)
    probs = model_service.predict(tensor)
    latency_ms = int((time.time() - start) * 1000)

    pred_idx = int(probs.argmax())
    predicted_class = model_service.classes[pred_idx]
    confidence = float(probs[pred_idx])
    top_k = model_service.topk(probs)
    is_low_confidence = confidence < settings.LOW_CONFIDENCE_THRESHOLD

    brightness, blur = drift_service.image_quality(image)
    is_drift_suspected = drift_service.is_drift(
        brightness, blur,
        settings.DRIFT_BRIGHTNESS_LOW,
        settings.DRIFT_BRIGHTNESS_HIGH,
        settings.DRIFT_BLUR_THRESHOLD,
    )

    cam = gradcam.generate(tensor, pred_idx)
    overlay = overlay_cam(image, cam, model_service.image_size)
    buffer = io.BytesIO()
    overlay.save(buffer, format="PNG")
    gradcam_base64 = base64.b64encode(buffer.getvalue()).decode()

    prediction_id = f"pred_{uuid.uuid4().hex[:12]}"

    metrics.record_prediction(
        predicted_class, confidence, latency_ms / 1000.0, brightness,
        is_low_confidence, is_drift_suspected,
    )

    _persist(
        storage=storage,
        image=image,
        raw=raw,
        content_type=file.content_type,
        prediction_id=prediction_id,
        top_k=top_k,
        predicted_class=predicted_class,
        confidence=confidence,
        latency_ms=latency_ms,
        model_service=model_service,
        is_low_confidence=is_low_confidence,
        is_drift_suspected=is_drift_suspected,
        brightness=brightness,
        blur=blur,
        source=source,
    )

    return PredictResponse(
        prediction_id=prediction_id,
        predicted_class=predicted_class,
        confidence=round(confidence, 4),
        top_k=[TopKItem(**item) for item in top_k],
        is_low_confidence=is_low_confidence,
        model_version=model_service.model_version,
        data_version=model_service.data_version,
        latency_ms=latency_ms,
        gradcam_base64=gradcam_base64,
    )


def _persist(storage, image, raw, content_type, prediction_id, top_k, predicted_class,
             confidence, latency_ms, model_service, is_low_confidence, is_drift_suspected,
             brightness, blur, source):
    if storage is None:
        return
    try:
        now = datetime.now()
        ext = "png" if content_type and "png" in content_type else "jpg"
        image_key = f"{now:%Y/%m/%d}/{prediction_id}.{ext}"
        storage.upload_image(image_key, raw, content_type or "image/jpeg")
        prediction_repository.insert_prediction({
            "prediction_id": prediction_id,
            "image_key": image_key,
            "image_width": image.width,
            "image_height": image.height,
            "predicted_class": predicted_class,
            "confidence": confidence,
            "top_k": top_k,
            "latency_ms": latency_ms,
            "model_version": model_service.model_version,
            "data_version": model_service.data_version,
            "is_low_confidence": is_low_confidence,
            "is_drift_suspected": is_drift_suspected,
            "brightness_score": brightness,
            "blur_score": blur,
            "source": source,
        })
    except Exception as err:
        logger.warning("Khong luu duoc prediction %s: %s", prediction_id, err)
