from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.auth import PasswordChange, UserPatch
from app.schemas.auth import User as UserResponse
from app.schemas.common import Error, Message
from app.services import auth

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={code: {"model": Error} for code in (401, 422, 503)},
)


@router.get("/me", response_model=UserResponse, operation_id="get__users_me")
def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserResponse, operation_id="patch__users_me")
def update_me(payload: UserPatch, user: CurrentUser, db: DbSession):
    return auth.update_profile(db, user, payload)


@router.post("/me/password", response_model=Message, operation_id="post__users_me_password")
def change_password(payload: PasswordChange, user: CurrentUser, db: DbSession):
    auth.change_password(db, user, payload)
    return Message(message="비밀번호가 변경되었습니다. 다시 로그인해 주세요.")
