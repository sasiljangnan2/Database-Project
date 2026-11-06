from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import settings
from app.core.errors import AppError

password_hasher = PasswordHasher()
DUMMY_PASSWORD_HASH = password_hasher.hash("not-an-account-password")


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    token_version: int


def authentication_error(code="AUTH_REQUIRED", message="로그인이 필요합니다.") -> AppError:
    return AppError(401, code, message, headers={"WWW-Authenticate": "Bearer"})


def signing_key() -> str:
    key = settings.jwt_secret_key.get_secret_value()
    if not key:
        raise AppError(503, "AUTH_NOT_CONFIGURED", "서버의 JWT_SECRET_KEY를 설정해 주세요.")
    return key


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int, token_version: int) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "token_version": token_version,
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        signing_key(),
        algorithm="HS256",
    )


def decode_access_token(token: str) -> TokenClaims:
    key = signing_key()
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "token_version", "iat", "exp", "iss", "aud"]},
        )
        subject = payload["sub"]
        version = payload["token_version"]
        if not isinstance(subject, str) or not subject.isascii() or not subject.isdigit():
            raise InvalidTokenError("Invalid subject")
        if int(subject) < 1 or type(version) is not int or version < 0:
            raise InvalidTokenError("Invalid identity claims")
        return TokenClaims(user_id=int(subject), token_version=version)
    except ExpiredSignatureError as error:
        raise authentication_error("TOKEN_EXPIRED", "로그인이 만료되었습니다.") from error
    except InvalidTokenError as error:
        raise authentication_error() from error
