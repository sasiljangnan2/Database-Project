"""db/001_schema.sql과 대응하는 ORM 매핑. 스키마 변경은 SQL로 적용한다."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("reservation_id", "seat_id"),
        Index(
            "idx_ticket_occupancy",
            "seat_id",
            "status",
            "boarding_run_stop_id",
            "alighting_run_stop_id",
        ),
        CheckConstraint("boarding_run_stop_id <> alighting_run_stop_id"),
        CheckConstraint("confirmed_amount >= 0"),
        CheckConstraint("status IN ('HELD', 'ISSUED', 'BOARDED', 'CANCELLED', 'EXPIRED')"),
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
    seat_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("seats.id"),
        nullable=False,
    )
    boarding_run_stop_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("run_stops.id"),
        nullable=False,
    )
    alighting_run_stop_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("run_stops.id"),
        nullable=False,
    )
    fare_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("fares.id"),
        nullable=False,
    )
    confirmed_amount: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=False).with_variant(Integer, "sqlite"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(15), nullable=False, default="HELD", server_default=text("'HELD'")
    )
    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=True
    )
