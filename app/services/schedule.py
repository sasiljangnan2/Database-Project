"""노선정차역·운행·운행정차일정 관리(김용우). 시간표 규칙은 docs/05-business-rules.md를 따른다.

열차 부모 행(trains)을 먼저 잠그고 운행을 재조회한다. 예약·결제와 같은 잠금 순서다.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Reservation, RouteStop, Run, RunStop, Train
from app.schemas import catalog as schemas
from app.schemas.common import Message, Page
from app.services import crud
from app.services.rules import time_window, validate_sequence, validate_stop_times, windows_overlap

# ---------- DB 보조 ----------


def lock_trains(db: Session, *train_ids: int) -> None:
    for train_id in sorted(set(train_ids)):
        db.scalar(select(Train.id).where(Train.id == train_id).with_for_update())


def locked_run(db: Session, run_id: int) -> Run | None:
    """열차 행을 잠근 뒤 운행을 다시 읽는다."""
    run = db.get(Run, run_id)
    if run is None:
        return None
    lock_trains(db, run.train_id)
    return db.get(Run, run_id, populate_existing=True)


def run_has_reservations(db: Session, run_id: int) -> bool:
    return bool(db.scalar(select(exists().where(Reservation.run_id == run_id))))


def route_has_runs(db: Session, route_id: int) -> bool:
    return bool(db.scalar(select(exists().where(Run.route_id == route_id))))


def ensure_no_time_conflict(db: Session, run: Run) -> None:
    """같은 열차의 다른 운행(취소 제외)과 첫 시각~마지막 시각이 겹치면 409."""
    own_rows = db.execute(
        select(RunStop.arrival_at, RunStop.departure_at).where(RunStop.run_id == run.id)
    ).all()
    own = time_window([time for row in own_rows for time in row])
    if own is None:
        return
    rows = db.execute(
        select(RunStop.run_id, RunStop.arrival_at, RunStop.departure_at)
        .join(Run, Run.id == RunStop.run_id)
        .where(Run.train_id == run.train_id, Run.id != run.id, Run.status != "CANCELLED")
    ).all()
    windows: dict[int, list[datetime | None]] = {}
    for other_id, arrival, departure in rows:
        windows.setdefault(other_id, []).extend([arrival, departure])
    for other_id, times in windows.items():
        other = time_window(times)
        if other is not None and windows_overlap(own, other):
            raise AppError(
                409,
                "RUN_TIME_CONFLICT",
                "같은 열차의 다른 운행과 시간이 겹칩니다.",
            )


# ---------- 노선정차역 ----------


def _route_stop_guard(db: Session, route_id: int, *, referenced: bool = False) -> None:
    if referenced or route_has_runs(db, route_id):
        raise crud.in_use("운행이 있는 노선의 정차역은 변경할 수 없습니다.")


def route_stop_create(db: Session, payload: schemas.RouteStopCreate) -> schemas.RouteStop:
    with crud.write_transaction(db, "create"):
        _route_stop_guard(db, payload.route_id)
        row = RouteStop(**payload.model_dump())
        db.add(row)
        db.flush()
    return schemas.RouteStop.model_validate(row)


def route_stop_patch(
    db: Session, row_id: int, payload: schemas.RouteStopPatch
) -> schemas.RouteStop:
    changes = payload.model_dump(exclude_unset=True)
    with crud.write_transaction(db, "update"):
        row = crud.get_or_404(db, RouteStop, row_id, lock=True)
        _route_stop_guard(db, row.route_id)
        if "route_id" in changes:
            _route_stop_guard(db, changes["route_id"])
        crud.apply_changes(row, changes)
        db.flush()
    return schemas.RouteStop.model_validate(row)


def route_stop_delete(db: Session, row_id: int) -> Message:
    with crud.write_transaction(db, "delete"):
        row = crud.get_or_404(db, RouteStop, row_id, lock=True)
        _route_stop_guard(db, row.route_id)
        db.delete(row)
        db.flush()
    return Message(message="노선정차역을 삭제했습니다.")


# ---------- 운행 ----------


def run_create(db: Session, payload: schemas.RunCreate) -> schemas.Run:
    data = payload.model_dump()
    with crud.write_transaction(db, "create"):
        lock_trains(db, data["train_id"])
        row = Run(**data)
        db.add(row)
        db.flush()
    return schemas.Run.model_validate(row)


PROTECTED_RUN_FIELDS = ("train_id", "route_id", "direction", "service_date")


def run_patch(db: Session, run_id: int, payload: schemas.RunPatch) -> schemas.Run:
    changes = payload.model_dump(exclude_unset=True)
    with crud.write_transaction(db, "update"):
        current = db.get(Run, run_id)
        if current is None:
            raise crud.not_found("운행을 찾을 수 없습니다.")
        lock_trains(db, current.train_id, changes.get("train_id", current.train_id))
        run = db.get(Run, run_id, populate_existing=True)
        if run.status == "CANCELLED":
            raise crud.invalid_state("취소된 운행은 수정할 수 없습니다.")
        protected = [
            name
            for name in PROTECTED_RUN_FIELDS
            if name in changes and changes[name] != getattr(run, name)
        ]
        if protected and run_has_reservations(db, run.id):
            raise crud.in_use("예약이 있는 운행의 열차·노선·방향·운행일은 수정할 수 없습니다.")
        if "route_id" in protected and db.scalar(select(exists().where(RunStop.run_id == run.id))):
            raise crud.in_use("정차일정이 있는 운행의 노선은 바꿀 수 없습니다.")
        crud.apply_changes(run, changes)
        db.flush()
        if "train_id" in protected:
            ensure_no_time_conflict(db, run)
    return schemas.Run.model_validate(run)


# ---------- 운행정차일정 ----------


def _check_run_stop(
    db: Session,
    run: Run,
    *,
    route_stop_id: int,
    stop_order: int,
    arrival: datetime | None,
    departure: datetime | None,
    exclude_id: int | None,
) -> None:
    if run.status == "CANCELLED":
        raise crud.invalid_state("취소된 운행의 정차일정은 변경할 수 없습니다.")
    if run_has_reservations(db, run.id):
        raise crud.in_use("예약이 있는 운행의 시간표·정차순서는 수정할 수 없습니다.")
    route_stop = db.get(RouteStop, route_stop_id)
    if route_stop is None or route_stop.route_id != run.route_id:
        raise crud.invalid_input("운행 노선에 속한 노선정차역이 아닙니다.", "route_stop_id")
    problem = validate_stop_times(arrival, departure)
    if problem:
        raise crud.invalid_input(problem, "arrival_at")
    others = [
        (order, arr, dep)
        for rid, order, arr, dep in db.execute(
            select(RunStop.id, RunStop.stop_order, RunStop.arrival_at, RunStop.departure_at).where(
                RunStop.run_id == run.id
            )
        )
        if rid != exclude_id
    ]
    problem = validate_sequence([*others, (stop_order, arrival, departure)])
    if problem:
        raise crud.invalid_input(problem, "stop_order")


def run_stop_create(db: Session, payload: schemas.RunStopCreate) -> schemas.RunStop:
    data = payload.model_dump()
    data["arrival_at"] = crud.to_db_time(data["arrival_at"])
    data["departure_at"] = crud.to_db_time(data["departure_at"])
    with crud.write_transaction(db, "create"):
        run = locked_run(db, data["run_id"])
        if run is None:
            raise crud.invalid_input("존재하지 않는 운행입니다.", "run_id")
        _check_run_stop(
            db,
            run,
            route_stop_id=data["route_stop_id"],
            stop_order=data["stop_order"],
            arrival=data["arrival_at"],
            departure=data["departure_at"],
            exclude_id=None,
        )
        row = RunStop(**data)
        db.add(row)
        db.flush()
        ensure_no_time_conflict(db, run)
    return schemas.RunStop.model_validate(row)


def run_stop_patch(db: Session, row_id: int, payload: schemas.RunStopPatch) -> schemas.RunStop:
    changes = payload.model_dump(exclude_unset=True)
    for name in ("arrival_at", "departure_at"):
        if name in changes:
            changes[name] = crud.to_db_time(changes[name])
    with crud.write_transaction(db, "update"):
        current = db.get(RunStop, row_id)
        if current is None:
            raise crud.not_found("운행정차일정을 찾을 수 없습니다.")
        if "run_id" in changes and changes["run_id"] != current.run_id:
            raise crud.invalid_input("정차일정의 운행은 바꿀 수 없습니다.", "run_id")
        run = locked_run(db, current.run_id)
        row = db.get(RunStop, row_id, populate_existing=True)
        merged: dict[str, Any] = {
            "route_stop_id": row.route_stop_id,
            "stop_order": row.stop_order,
            "arrival_at": row.arrival_at,
            "departure_at": row.departure_at,
        } | {k: v for k, v in changes.items() if k != "run_id"}
        _check_run_stop(
            db,
            run,
            route_stop_id=merged["route_stop_id"],
            stop_order=merged["stop_order"],
            arrival=merged["arrival_at"],
            departure=merged["departure_at"],
            exclude_id=row.id,
        )
        crud.apply_changes(row, {k: v for k, v in changes.items() if k != "run_id"})
        db.flush()
        ensure_no_time_conflict(db, run)
    return schemas.RunStop.model_validate(row)


def run_stop_delete(db: Session, row_id: int) -> Message:
    with crud.write_transaction(db, "delete"):
        current = db.get(RunStop, row_id)
        if current is None:
            raise crud.not_found("운행정차일정을 찾을 수 없습니다.")
        run = locked_run(db, current.run_id)
        if run_has_reservations(db, run.id):
            raise crud.in_use("예약이 있는 운행의 정차일정은 삭제할 수 없습니다.")
        row = db.get(RunStop, row_id, populate_existing=True)
        db.delete(row)
        db.flush()
    return Message(message="운행정차일정을 삭제했습니다.")


# ---------- 목록 ----------

LISTS = {
    "route-stops": (RouteStop, schemas.RouteStop),
    "runs": (Run, schemas.Run),
    "run-stops": (RunStop, schemas.RunStop),
}


def admin_list(db: Session, name: str, page: int, size: int) -> Page:
    model, schema = LISTS[name]
    return crud.page_of(db, model, schema, page, size, order=(model.id,))
