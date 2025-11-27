from __future__ import annotations

from typing import Any

from ti89.webapp import create_app


def perform_request(client: Any, payload: dict[str, object]) -> dict[str, object]:
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    return data


def test_evaluate_endpoint_handles_substitutions() -> None:
    app = create_app()
    client = app.test_client()

    payload: dict[str, object] = {
        "operation": "evaluate",
        "expression": "sin(x)^2 + cos(x)^2",
        "variables": {"x": "pi/3"},
    }
    data = perform_request(client, payload)
    assert data["result"] == "1"
    assert data["approximation"] == 1.0


def test_derivative_and_limit_modes() -> None:
    app = create_app()
    client = app.test_client()

    derivative_payload: dict[str, object] = {
        "operation": "derivative",
        "expression": "exp(x)",
        "variable": "x",
    }
    derivative = perform_request(client, derivative_payload)
    assert derivative["result"] == "exp(x)"

    limit_payload: dict[str, object] = {
        "operation": "limit",
        "expression": "sin(x)/x",
        "variable": "x",
        "value": "0",
    }
    limit_result = perform_request(client, limit_payload)
    assert str(limit_result["approximation"]) == "1.0"


def test_manifest_and_service_worker_routes() -> None:
    app = create_app()
    client = app.test_client()

    assert client.get("/manifest.webmanifest").status_code == 200
    assert client.get("/service-worker.js").status_code == 200
