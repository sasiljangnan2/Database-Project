"""db/001_schema.sql과 대응하는 ORM 매핑. 스키마 변경은 SQL로 적용한다."""

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SeatOccupancy(Base):
    __tablename__ = "seat_occupancies"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "segment_start_order"],
            ["run_stops.run_id", "run_stops.stop_order"],
            name="fk_occupancy_segment",
        ),
        Index("idx_occupancy_ticket", "ticket_id"),
        CheckConstraint("segment_start_order > 0"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    run_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("runs.id"),
        primary_key=True,
        autoincrement=False,
        nullable=False,
    )
    seat_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("seats.id"),
        primary_key=True,
        autoincrement=False,
        nullable=False,
    )
    segment_start_order: Mapped[int] = mapped_column(
        SmallInteger().with_variant(mysql.SMALLINT(unsigned=True), "mysql"),
        primary_key=True,
        autoincrement=False,
        nullable=False,
    )
    ticket_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("tickets.id"),
        nullable=False,
    )
