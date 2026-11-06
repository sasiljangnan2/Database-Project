from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.auth import Login, Register, Token
from app.schemas.auth import User as UserResponse
from app.schemas.common import Error, Message
from app.services import auth

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={code: {"model": Error} for code in (401, 409, 422, 503)},
)


@router.post(
    "/register", response_model=UserResponse, status_code=201, operation_id="post__auth_register"
)
def register(payload: Register, db: DbSession):
    return auth.register(db, payload)


@router.post("/login", response_model=Token, operation_id="post__auth_login")
def login(payload: Login, db: DbSession):
    """JSON 로그인. Swagger Authorize에는 반환된 access_token을 입력한다."""
    return auth.login(db, payload)


@router.post("/logout", response_model=Message, operation_id="post__auth_logout")
def logout(user: CurrentUser, db: DbSession):
    auth.logout(db, user)
    return Message(message="모든 기기에서 로그아웃했습니다.")
