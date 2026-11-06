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
    assert "회원·인증 공통 기반" in response.text
    assert "운행 검색·예약·결제 API는 담당자별로 개발" in response.text
