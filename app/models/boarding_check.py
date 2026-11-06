"""db/001_schema.sql과 대응하는 ORM 매핑. 스키마 변경은 SQL로 적용한다."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BoardingCheck(Base):
    __tablename__ = "boarding_checks"
    __table_args__ = (
        UniqueConstraint("ticket_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    ticket_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("tickets.id"),
        nullable=False,
    )
    checked_by: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("users.id"),
        nullable=False,
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=False
    )
