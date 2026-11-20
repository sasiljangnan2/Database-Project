"""기준정보 관리 CRUD의 공통 부분: 트랜잭션, DB 오류 변환, 페이지 조회."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.schemas.common import APIModel, ErrorDetail, Page

MYSQL_DUPLICATE = 1062
MYSQL_PARENT_REFERENCED = 1451
MYSQL_CHILD_MISSING = 1452
MYSQL_CHECK_FAILED = (3819, 4025)


def not_found(message: str = "대상을 찾을 수 없습니다.") -> AppError:
    return AppError(404, "RESOURCE_NOT_FOUND", message)


def in_use(message: str = "다른 데이터가 참조 중이라 변경하거나 삭제할 수 없습니다.") -> AppError:
    return AppError(409, "RESOURCE_IN_USE", message)


def invalid_state(message: str) -> AppError:
    return AppError(409, "INVALID_STATE", message)


def invalid_input(message: str, field: str = "request") -> AppError:
    return AppError(
        422, "VALIDATION_ERROR", message, details=[ErrorDetail(field=field, message=message)]
    )


def to_db_time(value: datetime | None) -> datetime | None:
    """API의 시간대 포함 일시를 MySQL DATETIME(6)용 시간대 없는 UTC로 바꾼다."""
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("시간대가 없는 일시는 저장할 수 없습니다.")
    return value.astimezone(UTC).replace(tzinfo=None)


def _errno(error: IntegrityError) -> int | None:
    args = getattr(error.orig, "args", ())
    return args[0] if args and isinstance(args[0], int) else None


def translate_integrity_error(error: IntegrityError, action: str) -> AppError | None:
    """MySQL(와 테스트용 SQLite)의 제약 위반을 API 오류로 바꾼다. 원문은 응답하지 않는다."""
    errno = _errno(error)
    text = str(error.orig).lower()
    foreign_key = errno in (MYSQL_PARENT_REFERENCED, MYSQL_CHILD_MISSING) or (
        "foreign key constraint failed" in text
    )
    if errno == MYSQL_DUPLICATE or "unique constraint failed" in text:
        return AppError(409, "RESOURCE_CONFLICT", "이미 같은 값의 데이터가 있습니다.")
    if errno == MYSQL_PARENT_REFERENCED or (foreign_key and action in ("delete", "update")):
        return in_use()
    if foreign_key:
        return invalid_input("존재하지 않는 대상을 참조했습니다.")
    if errno in MYSQL_CHECK_FAILED or "check constraint failed" in text:
        return invalid_input("값이 허용 범위를 벗어났습니다.")
    return None


@contextmanager
def write_transaction(db: Session, action: str) -> Iterator[None]:
    """블록을 한 트랜잭션으로 커밋한다. 실패하면 전부 롤백한다."""
    try:
        yield
        db.commit()
    except AppError:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        translated = translate_integrity_error(error, action)
        if translated is None:
            raise
        raise translated from error
    except Exception:
        db.rollback()
        raise


def page_of(
    db: Session,
    model: type,
    schema: type[APIModel],
    page: int,
    size: int,
    *,
    order: tuple[Any, ...],
    where: tuple[Any, ...] = (),
) -> Page:
    total = db.scalar(select(func.count()).select_from(model).where(*where)) or 0
    rows = db.scalars(
        select(model).where(*where).order_by(*order).limit(size).offset((page - 1) * size)
    ).all()
    return Page[schema](
        items=[schema.model_validate(row) for row in rows], page=page, size=size, total=total
    )


def escape_like(keyword: str) -> str:
    return keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_or_404(db: Session, model: type, key: Any, *, lock: bool = False):
    row = db.get(model, key, with_for_update=lock, populate_existing=lock)
    if row is None:
        raise not_found()
    return row


def apply_changes(row: Any, changes: dict[str, Any]) -> None:
    for field, value in changes.items():
        setattr(row, field, value)
