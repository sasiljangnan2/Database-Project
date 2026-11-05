from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_is_process_only():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "scope": "process"}


def test_home_explains_implementation_scope():
    response = client.get("/")
    assert response.status_code == 200
    assert "기본 화면과 서버 상태 확인만" in response.text
