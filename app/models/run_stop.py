"""db/001_schema.sql과 대응하는 ORM 매핑. 스키마 변경은 SQL로 적용한다."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RunStop(Base):
    __tablename__ = "run_stops"
    __table_args__ = (
        UniqueConstraint("run_id", "stop_order"),
        UniqueConstraint("run_id", "route_stop_id"),
        Index("idx_stops_departure", "departure_at"),
        CheckConstraint("stop_order > 0"),
        CheckConstraint("arrival_at IS NOT NULL OR departure_at IS NOT NULL"),
        CheckConstraint("arrival_at IS NULL OR departure_at IS NULL OR arrival_at <= departure_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    run_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("runs.id"),
        nullable=False,
    )
    route_stop_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("route_stops.id"),
        nullable=False,
    )
    stop_order: Mapped[int] = mapped_column(
        SmallInteger().with_variant(mysql.SMALLINT(unsigned=True), "mysql"), nullable=False
    )
    arrival_at: Mapped[datetime | None] = mapped_column(
        DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=True
    )
    departure_at: Mapped[datetime | None] = mapped_column(
        DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=True
    )
