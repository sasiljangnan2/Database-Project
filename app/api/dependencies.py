from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.principal import Principal
from app.core.security import authentication_error, decode_access_token
from app.db.session import get_db
from app.repositories import users

DbSession = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False, scheme_name="BearerAuth")


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    if credentials is None:
        raise authentication_error()
    claims = decode_access_token(credentials.credentials)
    user = users.by_id(db, claims.user_id)
    if user is None or not user.is_active:
        raise authentication_error()
    if user.token_version != claims.token_version:
        raise authentication_error("TOKEN_EXPIRED", "다시 로그인해 주세요.")
    return Principal(
        id=user.id,
        email=user.email,
        name=user.name,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active,
        token_version=user.token_version,
    )


CurrentUser = Annotated[Principal, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> Principal:
    if user.role != "ADMIN":
        raise AppError(403, "ADMIN_REQUIRED", "관리자 권한이 필요합니다.")
    return user


AdminUser = Annotated[Principal, Depends(require_admin)]
