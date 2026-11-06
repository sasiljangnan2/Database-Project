"""db/001_schema.sql과 대응하는 ORM 매핑. 스키마 변경은 SQL로 적용한다."""

from datetime import datetime

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("reservation_id", "idempotency_key"),
        UniqueConstraint("successful_reservation_id"),
        CheckConstraint("amount >= 0"),
        CheckConstraint("method IN ('DEMO_CARD', 'DEMO_TRANSFER')"),
        CheckConstraint("status IN ('SUCCEEDED', 'FAILED')"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    reservation_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("reservations.id"),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=False).with_variant(Integer, "sqlite"), nullable=False
    )
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(64).with_variant(mysql.VARCHAR(64, charset="ascii", collation="ascii_bin"), "mysql"),
        nullable=False,
    )
    request_hash: Mapped[str] = mapped_column(
        CHAR(64).with_variant(mysql.CHAR(64, charset="ascii", collation="ascii_bin"), "mysql"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=False, default=utc_now
    )
    successful_reservation_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        Computed(
            "CASE WHEN status = 'SUCCEEDED' THEN reservation_id ELSE NULL END", persisted=True
        ),
        nullable=True,
    )
