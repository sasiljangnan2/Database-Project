from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import register_error_handlers


def test_unexpected_failure_has_a_safe_error_envelope():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/failure")
    def failure():
        raise RuntimeError("internal-password-value")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/failure")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "internal-password-value" not in response.text
