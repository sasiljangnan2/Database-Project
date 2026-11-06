"""회원 HTTP 로직 단위 테스트. SQLite users만 사용하며 MySQL 잠금 검증을 대체하지 않는다."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import AdminUser
from app.core.config import settings
from app.core.security import decode_access_token, verify_password
from app.db.session import get_db
from app.main import create_app
from app.models import User

SPEC = json.loads((Path(__file__).resolve().parents[1] / "docs/openapi.json").read_text("utf-8"))
PASSWORD = "member-test-password-123"


@pytest.fixture
def context(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", SecretStr("test-key-" + "a" * 48))
    monkeypatch.setattr(settings, "enable_frontend_preview", False)
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    # 회원 로직만 검증한다. 전체 DDL·FK·구간 점유 검증은 MySQL 테스트에서 수행한다.
    User.__table__.create(engine)
    application = create_app()

    def sessions():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    application.dependency_overrides[get_db] = sessions

    @application.get("/__test/admin")
    def admin_only(user: AdminUser):
        return {"id": user.id}

    with TestClient(application) as client:
        yield client, engine
    engine.dispose()


def register(client, email="member@example.com", **changes):
    payload = {"email": email, "password": PASSWORD, "name": "회원", "phone": "010-0000-0000"}
    return client.post("/api/v1/auth/register", json=payload | changes)


def login(client, email="member@example.com", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def validate(payload, schema):
    Draft202012Validator(
        {"$ref": f"#/components/schemas/{schema}", "components": SPEC["components"]},
        format_checker=FormatChecker(),
    ).validate(payload)


def test_registration_normalizes_email_and_stores_only_a_hash(context):
    client, engine = context
    response = register(client, "  MEMBER@EXAMPLE.COM  ")
    assert response.status_code == 201
    validate(response.json(), "User")
    assert response.json()["email"] == "member@example.com"
    assert response.json()["role"] == "MEMBER"
    assert set(response.json()) == {"id", "email", "name", "phone", "role", "is_active"}
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user.password_hash != PASSWORD
        assert verify_password(PASSWORD, user.password_hash)


def test_client_cannot_inject_privileges_or_server_fields(context):
    client, _ = context
    response = register(client, role="ADMIN", token_version=0)
    assert response.status_code == 422
    validate(response.json(), "Error")
    assert PASSWORD not in response.text
    assert '"input"' not in response.text


def test_duplicate_email_is_reported_without_creating_a_second_account(context):
    client, _ = context
    assert register(client).status_code == 201
    response = register(client, "MEMBER@example.com")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_DUPLICATE"


def test_login_and_current_user_match_the_shared_contract(context):
    client, _ = context
    register(client)
    response = login(client)
    assert response.status_code == 200
    validate(response.json(), "Token")
    me = client.get("/api/v1/users/me", headers=headers(response.json()["access_token"]))
    assert me.status_code == 200
    validate(me.json(), "User")
    assert me.json()["email"] == "member@example.com"


@pytest.mark.parametrize("authorization", [None, "Basic abc", "Bearer invalid"])
def test_missing_or_invalid_authentication_has_a_consistent_error(context, authorization):
    client, _ = context
    response = client.get(
        "/api/v1/users/me", headers={"Authorization": authorization} if authorization else {}
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    validate(response.json(), "Error")


def test_failed_login_does_not_reveal_whether_the_account_exists(context):
    client, _ = context
    register(client)
    wrong_password = login(client, password="wrong-password")
    missing_account = login(client, email="missing@example.com")
    assert wrong_password.status_code == missing_account.status_code == 401
    assert wrong_password.json() == missing_account.json()


def test_logout_revokes_all_previously_issued_tokens(context):
    client, _ = context
    register(client)
    first = login(client).json()["access_token"]
    second = login(client).json()["access_token"]
    assert client.post("/api/v1/auth/logout", headers=headers(first)).status_code == 200
    for token in (first, second):
        response = client.get("/api/v1/users/me", headers=headers(token))
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "TOKEN_EXPIRED"
    fresh = login(client).json()["access_token"]
    assert client.get("/api/v1/users/me", headers=headers(fresh)).status_code == 200


def test_password_change_requires_current_password_and_revokes_tokens(context):
    client, _ = context
    register(client)
    token = login(client).json()["access_token"]
    body = {"current_password": "wrong-password", "new_password": "new-member-password-123"}
    assert (
        client.post("/api/v1/users/me/password", json=body, headers=headers(token)).status_code
        == 401
    )
    body["current_password"] = PASSWORD
    assert (
        client.post("/api/v1/users/me/password", json=body, headers=headers(token)).status_code
        == 200
    )
    assert client.get("/api/v1/users/me", headers=headers(token)).status_code == 401
    assert login(client).status_code == 401
    assert login(client, password=body["new_password"]).status_code == 200


def test_profile_patch_rejects_empty_null_and_unknown_fields(context):
    client, _ = context
    register(client)
    token = login(client).json()["access_token"]
    for body in ({}, {"name": None}, {"email": "other@example.com"}):
        assert (
            client.patch("/api/v1/users/me", json=body, headers=headers(token)).status_code == 422
        )
    response = client.patch("/api/v1/users/me", json={"name": "수정 회원"}, headers=headers(token))
    assert response.status_code == 200
    assert response.json()["name"] == "수정 회원"


def test_admin_dependency_uses_current_db_role_and_active_flag(context):
    client, engine = context
    register(client)
    token = login(client).json()["access_token"]
    assert client.get("/__test/admin", headers=headers(token)).status_code == 403
    with Session(engine) as db:
        user = db.scalar(select(User))
        user.role = "ADMIN"
        db.commit()
    assert client.get("/__test/admin", headers=headers(token)).status_code == 200
    with Session(engine) as db:
        user = db.scalar(select(User))
        user.is_active = False
        db.commit()
    assert client.get("/api/v1/users/me", headers=headers(token)).status_code == 401


@pytest.mark.parametrize("change", ["expired", "audience", "algorithm", "version"])
def test_signed_but_invalid_claims_are_rejected(context, change):
    client, _ = context
    register(client)
    now = datetime.now(UTC)
    claims = {
        "sub": "1",
        "token_version": 0,
        "iat": now - timedelta(minutes=10),
        "exp": now + timedelta(minutes=10),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    algorithm = "HS256"
    if change == "expired":
        claims["exp"] = now - timedelta(seconds=1)
    elif change == "audience":
        claims["aud"] = "another-application"
    elif change == "algorithm":
        algorithm = "HS384"
    else:
        claims["token_version"] = True
    token = jwt.encode(claims, settings.jwt_secret_key.get_secret_value(), algorithm=algorithm)
    assert client.get("/api/v1/users/me", headers=headers(token)).status_code == 401


def test_stale_principal_cannot_revoke_tokens_issued_after_logout(context):
    client, engine = context
    register(client)
    old = login(client).json()["access_token"]
    claims = decode_access_token(old)
    with Session(engine) as db:
        user = db.get(User, claims.user_id)
        from app.core.principal import Principal
        from app.services.auth import logout

        principal = Principal(
            user.id, user.email, user.name, user.phone, user.role, True, claims.token_version
        )
        user.token_version += 1
        db.commit()
        from app.core.errors import AppError

        with pytest.raises(AppError) as error:
            logout(db, principal)
        assert error.value.status == 401
        assert db.get(User, claims.user_id).token_version == 1


def test_missing_secret_disables_token_issuance_without_breaking_health(context, monkeypatch):
    client, _ = context
    monkeypatch.setattr(settings, "jwt_secret_key", SecretStr(""))
    response = login(client)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_NOT_CONFIGURED"
    assert client.get("/api/v1/health").status_code == 200
