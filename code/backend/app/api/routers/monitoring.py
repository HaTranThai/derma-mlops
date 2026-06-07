from fastapi import APIRouter, Query
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.schemas import MonitoringStats
from app.repositories import monitoring_repository

router = APIRouter()


@router.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/monitoring/stats", response_model=MonitoringStats)
def monitoring_stats(window: int = Query(200, ge=1, le=5000)):
    return monitoring_repository.summary(window)
