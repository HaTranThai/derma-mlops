import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import health, monitoring, reviews
from app.repositories import monitoring_repository, prediction_repository, review_repository


class StubModel:
    model_version = "efficientnet_b0_v2"
    classes = ["akiec", "bcc", "bkl", "df", "mel", "nv", "vasc"]


STATS = {
    "window": 200, "total": 0, "avg_confidence": 0.0, "avg_latency_ms": 0.0,
    "low_confidence_rate": 0.0, "drift_rate": 0.0, "input_quality_anomaly_rate": 0.0,
    "population_drift_psi": 0.0, "population_drift_level": "none",
    "class_distribution": [], "review_queue": 0,
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(review_repository, "list_queue", lambda limit, offset: [])
    monkeypatch.setattr(review_repository, "count_queue", lambda: 0)
    monkeypatch.setattr(review_repository, "list_reviews", lambda limit, offset: [])
    monkeypatch.setattr(review_repository, "count_reviews", lambda: 0)
    monkeypatch.setattr(review_repository, "submit_review", lambda *a, **k: None)
    monkeypatch.setattr(prediction_repository, "get_prediction", lambda pid: {"prediction_id": pid})
    monkeypatch.setattr(monitoring_repository, "summary", lambda window: {**STATS, "window": window})

    from app.api.deps import get_current_user

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: {"username": "test", "role": "admin"}
    app.include_router(health.router)
    app.include_router(reviews.router)
    app.include_router(monitoring.router)
    app.state.model_service = StubModel()
    return TestClient(app)


def test_health_returns_model_version(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["model_version"] == "efficientnet_b0_v2"


def test_review_queue_ok(client):
    res = client.get("/reviews/queue")
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == [] and body["total"] == 0


def test_monitoring_stats_exposes_psi(client):
    res = client.get("/monitoring/stats")
    assert res.status_code == 200
    assert "population_drift_psi" in res.json()
    assert "input_quality_anomaly_rate" in res.json()


def test_submit_review_rejects_invalid_label(client):
    res = client.post("/reviews", json={
        "prediction_id": "pred_x", "review_label": "NOT_A_CLASS", "reviewer": "t",
    })
    assert res.status_code == 400


def test_submit_review_accepts_valid_label(client):
    res = client.post("/reviews", json={
        "prediction_id": "pred_x", "review_label": "mel", "reviewer": "t",
    })
    assert res.status_code == 201
    assert res.json()["prediction_id"] == "pred_x"
