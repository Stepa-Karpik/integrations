from fastapi.testclient import TestClient

from app.main import app


def test_healthz_reports_service_name():
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"]


def test_cors_allows_documents_frontend_origin():
    response = TestClient(app).options(
        "/api/v1/watched-sources",
        headers={
            "Origin": "http://localhost:3200",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3200"
