import json
import urllib.request

from app.core.config import settings


def _request(method, path, body=None):
    url = f"{settings.PREFECT_API_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=10) as resp:
        return json.loads(resp.read())


def trigger_retraining(trigger_reason="manual"):
    deployment = _request("GET", "/deployments/name/retraining/default")
    deployment_id = deployment["id"]
    run = _request(
        "POST",
        f"/deployments/{deployment_id}/create_flow_run",
        {"parameters": {"trigger_reason": trigger_reason}},
    )
    return {"flow_run_id": run.get("id"), "name": run.get("name")}
