from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TopKItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    label: str = Field(alias="class")
    probability: float


class PredictResponse(BaseModel):
    prediction_id: str
    predicted_class: str
    confidence: float
    top_k: List[TopKItem]
    is_low_confidence: bool
    model_version: str
    data_version: str
    latency_ms: int
    gradcam_base64: str


class HealthResponse(BaseModel):
    status: str
    model_version: str


class PredictionRecord(BaseModel):
    prediction_id: str
    created_at: datetime
    predicted_class: str
    confidence: float
    top_k: List[Any]
    latency_ms: Optional[int] = None
    model_version: str
    data_version: Optional[str] = None
    is_low_confidence: bool
    image_url: Optional[str] = None


class PredictionList(BaseModel):
    items: List[PredictionRecord]
    total: int
    page: int
    limit: int


class ReviewQueueItem(BaseModel):
    prediction_id: str
    created_at: datetime
    predicted_class: str
    confidence: float
    image_url: Optional[str] = None


class ReviewQueueList(BaseModel):
    items: List[ReviewQueueItem]
    total: int
    page: int
    limit: int


class SubmitReviewRequest(BaseModel):
    prediction_id: str
    review_label: str
    reviewer: str = "simulated"


class ReviewRecord(BaseModel):
    prediction_id: str
    review_label: Optional[str] = None
    review_status: str
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    predicted_class: str
    confidence: float
    image_url: Optional[str] = None


class ReviewList(BaseModel):
    items: List[ReviewRecord]
    total: int
    page: int
    limit: int


class ClassCount(BaseModel):
    label: str
    count: int


class MonitoringStats(BaseModel):
    window: int
    total: int
    avg_confidence: float
    avg_latency_ms: float
    low_confidence_rate: float
    drift_rate: float
    input_quality_anomaly_rate: float
    population_drift_psi: float
    population_drift_level: str
    class_distribution: List[ClassCount]
    review_queue: int
