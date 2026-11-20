"""역·열차종류·열차·좌석·노선·운임과 회원 관리(김용우). 운행 편성은 services/schedule.py."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.principal import Principal
from app.models import (
    Fare,
    Reservation,
    Route,
    Run,
    Seat,
    Station,
    Ticket,
    Train,
    TrainType,
    User,
)
from app.schemas import catalog as schemas
from app.schemas.auth import AdminUserPatch
from app.schemas.auth import User as UserSchema
from app.schemas.common import APIModel, Message, Page
from app.services import crud


@dataclass(frozen=True)
class Resource:
    """관리 대상 하나. hooks는 쓰기 전에 업무 규칙을 검사한다."""

    model: type
    schema: type[APIModel]
    order: tuple[Any, ...]
    label: str
    before_create: Any = None
    before_patch: Any = None
    before_delete: Any = None


# ---------- 공개 조회 ----------


def public_stations(db: Session, page: int, size: int, keyword: str | None) -> Page:
    where = [Station.is_active.is_(True)]
    if keyword:
        where.append(Station.name.like(f"%{crud.escape_like(keyword)}%", escape="\\"))
    return crud.page_of(
        db, Station, schemas.Station, page, size, order=(Station.id,), where=tuple(where)
    )


def public_train_types(db: Session, page: int, size: int, keyword: str | None) -> Page:
    where = []
    if keyword:
        where.append(TrainType.name.like(f"%{crud.escape_like(keyword)}%", escape="\\"))
    return crud.page_of(
        db, TrainType, schemas.TrainType, page, size, order=(TrainType.code,), where=tuple(where)
    )


# ---------- 참조 여부 검사 ----------


def train_has_reservations(db: Session, train_id: int) -> bool:
    return bool(
        db.scalar(select(exists().where(Run.train_id == train_id, Reservation.run_id == Run.id)))
    )


def seat_in_tickets(db: Session, seat_id: int) -> bool:
    return bool(db.scalar(select(exists().where(Ticket.seat_id == seat_id))))


def fare_in_tickets(db: Session, fare_id: int) -> bool:
    return bool(db.scalar(select(exists().where(Ticket.fare_id == fare_id))))


# ---------- 자원별 규칙 ----------


def _train_patch(db: Session, row: Train, changes: dict) -> None:
    new_type = changes.get("train_type_code")
    if new_type is not None and new_type != row.train_type_code:
        if train_has_reservations(db, row.id):
            raise crud.in_use("예약이 있는 열차의 열차종류는 변경할 수 없습니다.")


def _seat_patch(db: Session, row: Seat, changes: dict) -> None:
    if changes and seat_in_tickets(db, row.id):
        raise crud.in_use("승차권이 있는 좌석은 수정할 수 없습니다.")


def _seat_delete(db: Session, row: Seat) -> None:
    if seat_in_tickets(db, row.id):
        raise crud.in_use("승차권이 있는 좌석은 삭제할 수 없습니다.")


def _check_fare_stations(departure: int, arrival: int) -> None:
    if departure == arrival:
        raise crud.invalid_input("출발역과 도착역은 달라야 합니다.", "arrival_station_id")


def _fare_create(db: Session, data: dict) -> None:
    _check_fare_stations(data["departure_station_id"], data["arrival_station_id"])


def _fare_patch(db: Session, row: Fare, changes: dict) -> None:
    departure = changes.get("departure_station_id", row.departure_station_id)
    arrival = changes.get("arrival_station_id", row.arrival_station_id)
    _check_fare_stations(departure, arrival)
    # 금액은 바꿔도 기존 승차권의 확정금액이 보존된다. 구간·종류·등급은 의미가 바뀌므로 막는다.
    key_changed = any(name != "amount" and getattr(row, name) != v for name, v in changes.items())
    if key_changed and fare_in_tickets(db, row.id):
        raise crud.in_use("승차권이 참조하는 운임의 구간·열차종류·등급은 수정할 수 없습니다.")


RESOURCES: dict[str, Resource] = {
    "stations": Resource(Station, schemas.Station, (Station.id,), "역"),
    "trains": Resource(Train, schemas.Train, (Train.id,), "열차", before_patch=_train_patch),
    "seats": Resource(
        Seat,
        schemas.Seat,
        (Seat.id,),
        "좌석",
        before_patch=_seat_patch,
        before_delete=_seat_delete,
    ),
    "routes": Resource(Route, schemas.Route, (Route.id,), "노선"),
    "fares": Resource(
        Fare,
        schemas.Fare,
        (Fare.id,),
        "운임",
        before_create=_fare_create,
        before_patch=_fare_patch,
    ),
    "train-types": Resource(TrainType, schemas.TrainType, (TrainType.code,), "열차종류"),
}


# ---------- 공통 관리 CRUD ----------


def admin_list(db: Session, name: str, page: int, size: int) -> Page:
    resource = RESOURCES[name]
    return crud.page_of(db, resource.model, resource.schema, page, size, order=resource.order)


def admin_create(db: Session, name: str, payload: APIModel) -> APIModel:
    resource = RESOURCES[name]
    data = payload.model_dump()
    with crud.write_transaction(db, "create"):
        if resource.before_create:
            resource.before_create(db, data)
        row = resource.model(**data)
        db.add(row)
        db.flush()
    return resource.schema.model_validate(row)


def admin_patch(db: Session, name: str, key: Any, payload: APIModel) -> APIModel:
    resource = RESOURCES[name]
    changes = payload.model_dump(exclude_unset=True)
    with crud.write_transaction(db, "update"):
        row = crud.get_or_404(db, resource.model, key, lock=True)
        if resource.before_patch:
            resource.before_patch(db, row, changes)
        crud.apply_changes(row, changes)
        db.flush()
    return resource.schema.model_validate(row)


def admin_delete(db: Session, name: str, key: Any) -> Message:
    resource = RESOURCES[name]
    with crud.write_transaction(db, "delete"):
        row = crud.get_or_404(db, resource.model, key, lock=True)
        if resource.before_delete:
            resource.before_delete(db, row)
        db.delete(row)
        db.flush()
    return Message(message=f"{resource.label}을(를) 삭제했습니다.")


# ---------- 회원 관리 ----------


def admin_users(db: Session, page: int, size: int, keyword: str | None) -> Page:
    where = []
    if keyword:
        pattern = f"%{crud.escape_like(keyword.strip().lower())}%"
        where.append(User.email.like(pattern, escape="\\") | User.name.like(pattern, escape="\\"))
    return crud.page_of(db, User, UserSchema, page, size, order=(User.id,), where=tuple(where))


def admin_patch_user(
    db: Session, admin: Principal, user_id: int, payload: AdminUserPatch
) -> UserSchema:
    if user_id == admin.id and payload.is_active is False:
        raise AppError(409, "INVALID_STATE", "본인 계정은 비활성화할 수 없습니다.")
    with crud.write_transaction(db, "update"):
        user = db.scalar(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None:
            raise crud.not_found("회원을 찾을 수 없습니다.")
        if user.is_active and payload.is_active is False:
            user.token_version += 1  # 비활성화 즉시 기존 토큰을 무효화한다. 예약·결제 기록은 보존.
        user.is_active = payload.is_active
        db.flush()
    return UserSchema.model_validate(user)
