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
    assert "예매 체험은 예시 열차와 좌석으로 진행" in response.text
    assert "결제는 모의로 처리됩니다" in response.text
