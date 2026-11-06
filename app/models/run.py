"""db/001_schema.sql과 대응하는 ORM 매핑. 스키마 변경은 SQL로 적용한다."""

from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
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


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        UniqueConstraint("service_number", "service_date"),
        Index("idx_runs_train_date", "train_id", "service_date"),
        CheckConstraint("status IN ('ON_SALE', 'CLOSED', 'CANCELLED')"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    train_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("trains.id"),
        nullable=False,
    )
    route_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("routes.id"),
        nullable=False,
    )
    service_number: Mapped[str] = mapped_column(String(30), nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(15), nullable=False, default="ON_SALE", server_default=text("'ON_SALE'")
    )
    direction: Mapped[str] = mapped_column(String(50), nullable=False)
