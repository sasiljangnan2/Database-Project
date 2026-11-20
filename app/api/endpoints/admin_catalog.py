"""김용우: 기준정보·운행·운임·회원 관리. 모든 경로는 AdminUser가 필요하다."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import AdminUser, DbSession
from app.schemas import catalog as schemas
from app.schemas.auth import AdminUserPatch
from app.schemas.auth import User as UserResponse
from app.schemas.common import APIModel, Error, Message, Page
from app.services import catalog, schedule

router = APIRouter(
    prefix="/admin",
    tags=["admin_catalog"],
    responses={code: {"model": Error} for code in (401, 403, 404, 409, 422, 503)},
)

PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
ItemId = Annotated[int, Path(ge=1)]


def register_crud(
    slug: str,
    out: type[APIModel],
    create: type[APIModel],
    patch: type[APIModel] | None,
    *,
    list_fn: Callable,
    create_fn: Callable,
    patch_fn: Callable | None,
    delete_fn: Callable | None,
) -> None:
    """/admin/{slug}의 목록·등록·수정·삭제를 등록한다. 운행은 삭제하지 않는다(delete_fn=None)."""
    base = slug.replace("-", "_")

    @router.get(f"/{slug}", response_model=Page[out], operation_id=f"get__admin_{base}")
    def list_items(_admin: AdminUser, db: DbSession, page: PageNumber = 1, size: PageSize = 20):
        return list_fn(db, page, size)

    @router.post(
        f"/{slug}", response_model=out, status_code=201, operation_id=f"post__admin_{base}"
    )
    def create_item(payload: create, _admin: AdminUser, db: DbSession):
        return create_fn(db, payload)

    if patch_fn is not None:

        @router.patch(
            f"/{slug}/{{id}}", response_model=out, operation_id=f"patch__admin_{base}_id_"
        )
        def patch_item(payload: patch, id: ItemId, _admin: AdminUser, db: DbSession):
            return patch_fn(db, id, payload)

    if delete_fn is not None:

        @router.delete(
            f"/{slug}/{{id}}", response_model=Message, operation_id=f"delete__admin_{base}_id_"
        )
        def delete_item(id: ItemId, _admin: AdminUser, db: DbSession):
            return delete_fn(db, id)


def generic(name: str) -> dict[str, Callable]:
    """catalog.RESOURCES에 정의된 자원의 서비스 함수 묶음."""
    return {
        "list_fn": lambda db, page, size: catalog.admin_list(db, name, page, size),
        "create_fn": lambda db, payload: catalog.admin_create(db, name, payload),
        "patch_fn": lambda db, key, payload: catalog.admin_patch(db, name, key, payload),
        "delete_fn": lambda db, key: catalog.admin_delete(db, name, key),
    }


register_crud(
    "stations", schemas.Station, schemas.StationCreate, schemas.StationPatch, **generic("stations")
)
register_crud("trains", schemas.Train, schemas.TrainCreate, schemas.TrainPatch, **generic("trains"))
register_crud("seats", schemas.Seat, schemas.SeatCreate, schemas.SeatPatch, **generic("seats"))
register_crud("routes", schemas.Route, schemas.RouteCreate, schemas.RoutePatch, **generic("routes"))
register_crud("fares", schemas.Fare, schemas.FareCreate, schemas.FarePatch, **generic("fares"))
register_crud(
    "route-stops",
    schemas.RouteStop,
    schemas.RouteStopCreate,
    schemas.RouteStopPatch,
    list_fn=lambda db, page, size: schedule.admin_list(db, "route-stops", page, size),
    create_fn=schedule.route_stop_create,
    patch_fn=schedule.route_stop_patch,
    delete_fn=schedule.route_stop_delete,
)
register_crud(
    "runs",
    schemas.Run,
    schemas.RunCreate,
    schemas.RunPatch,
    list_fn=lambda db, page, size: schedule.admin_list(db, "runs", page, size),
    create_fn=schedule.run_create,
    patch_fn=schedule.run_patch,
    delete_fn=None,
)
register_crud(
    "run-stops",
    schemas.RunStop,
    schemas.RunStopCreate,
    schemas.RunStopPatch,
    list_fn=lambda db, page, size: schedule.admin_list(db, "run-stops", page, size),
    create_fn=schedule.run_stop_create,
    patch_fn=schedule.run_stop_patch,
    delete_fn=schedule.run_stop_delete,
)


# ---- 열차종류: 기본키가 문자열 code이므로 따로 등록한다 ----
TypeCode = Annotated[str, Path(min_length=1, max_length=30)]


@router.get(
    "/train-types", response_model=Page[schemas.TrainType], operation_id="get_admin_train_types"
)
def list_train_types(_admin: AdminUser, db: DbSession, page: PageNumber = 1, size: PageSize = 20):
    return catalog.admin_list(db, "train-types", page, size)


@router.post(
    "/train-types",
    response_model=schemas.TrainType,
    status_code=201,
    operation_id="post_admin_train_types",
)
def create_train_type(payload: schemas.TrainTypeCreate, _admin: AdminUser, db: DbSession):
    return catalog.admin_create(db, "train-types", payload)


@router.patch(
    "/train-types/{code}",
    response_model=schemas.TrainType,
    operation_id="patch_admin_train_type_by_code",
)
def patch_train_type(
    payload: schemas.TrainTypePatch, code: TypeCode, _admin: AdminUser, db: DbSession
):
    """종류명만 바꾼다. 코드는 기본키라서 변경하지 않는다."""
    return catalog.admin_patch(db, "train-types", code, payload)


@router.delete(
    "/train-types/{code}", response_model=Message, operation_id="delete_admin_train_type_by_code"
)
def delete_train_type(code: TypeCode, _admin: AdminUser, db: DbSession):
    return catalog.admin_delete(db, "train-types", code)


# ---- 회원 ----
@router.get("/users", response_model=Page[UserResponse], operation_id="get__admin_users")
def list_users(
    _admin: AdminUser,
    db: DbSession,
    page: PageNumber = 1,
    size: PageSize = 20,
    keyword: Annotated[str | None, Query(max_length=100)] = None,
):
    return catalog.admin_users(db, page, size, keyword)


@router.patch(
    "/users/{user_id}", response_model=UserResponse, operation_id="patch__admin_users_user_id_"
)
def patch_user(
    payload: AdminUserPatch,
    user_id: Annotated[int, Path(ge=1)],
    admin: AdminUser,
    db: DbSession,
):
    """is_active만 바꾼다. 비활성화하면 기존 토큰이 즉시 무효가 된다."""
    return catalog.admin_patch_user(db, admin, user_id, payload)
