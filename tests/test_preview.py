from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app


def test_preview_is_not_registered_without_explicit_enablement(monkeypatch):
    monkeypatch.setattr(settings, "enable_frontend_preview", False)
    with TestClient(create_app()) as client:
        assert client.get("/dev/preview").status_code == 404


def test_preview_and_static_samples_work_without_database_calls(monkeypatch):
    monkeypatch.setattr(settings, "enable_frontend_preview", True)
    with TestClient(create_app()) as client:
        page = client.get("/dev/preview")
        assert page.status_code == 200
        assert "실제 예약·결제를 생성하지 않습니다" in page.text
        assert client.get("/static/js/api-client.js").status_code == 200
        assert client.get("/static/samples/seats.json").json()[0]["seat_id"] == 101
