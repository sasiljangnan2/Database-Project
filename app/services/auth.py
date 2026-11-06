from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.core.errors import AppError
from app.core.principal import Principal
from app.models import User
from app.repositories import users
from app.schemas.auth import Login, PasswordChange, Register, Token, UserPatch


def register(db: Session, payload: Register) -> User:
    if users.by_email(db, str(payload.email)):
        raise AppError(409, "EMAIL_DUPLICATE", "이미 등록된 이메일입니다.")
    user = User(
        email=str(payload.email),
        password_hash=security.hash_password(payload.password),
        name=payload.name,
        phone=payload.phone,
        role="MEMBER",
        is_active=True,
        token_version=0,
    )
    try:
        db.add(user)
        db.flush()
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if getattr(error.orig, "args", (None,))[0] == 1062:
            raise AppError(409, "EMAIL_DUPLICATE", "이미 등록된 이메일입니다.") from error
        raise
    except Exception:
        db.rollback()
        raise
    return user


def login(db: Session, payload: Login) -> Token:
    security.signing_key()
    try:
        user = users.by_email(db, str(payload.email), for_update=True)
        password_hash = user.password_hash if user else security.DUMMY_PASSWORD_HASH
        password_matches = security.verify_password(payload.password, password_hash)
        if not password_matches or user is None or not user.is_active:
            raise security.authentication_error(message="이메일 또는 비밀번호를 확인해 주세요.")
        if security.password_hasher.check_needs_rehash(user.password_hash):
            user.password_hash = security.hash_password(payload.password)
        token = Token(
            access_token=security.create_access_token(user.id, user.token_version),
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )
        db.commit()
        return token
    except Exception:
        db.rollback()
        raise


def locked_user(db: Session, principal: Principal) -> User:
    user = users.by_id(db, principal.id, for_update=True)
    if user is None or not user.is_active or user.token_version != principal.token_version:
        raise security.authentication_error("TOKEN_EXPIRED", "다시 로그인해 주세요.")
    return user


def logout(db: Session, principal: Principal) -> None:
    try:
        user = locked_user(db, principal)
        user.token_version += 1
        db.commit()
    except Exception:
        db.rollback()
        raise


def update_profile(db: Session, principal: Principal, payload: UserPatch) -> User:
    try:
        user = locked_user(db, principal)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        db.commit()
        return user
    except Exception:
        db.rollback()
        raise


def change_password(db: Session, principal: Principal, payload: PasswordChange) -> None:
    try:
        user = locked_user(db, principal)
        if not security.verify_password(payload.current_password, user.password_hash):
            raise security.authentication_error(message="현재 비밀번호를 확인해 주세요.")
        user.password_hash = security.hash_password(payload.new_password)
        user.token_version += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
