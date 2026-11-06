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

from app.core.time import utc_now
from app.db.base import Base


class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = (
        Index("idx_refund_status", "status"),
        CheckConstraint("amount >= 0"),
        CheckConstraint("reason IN ('USER_CANCELLED', 'RUN_CANCELLED')"),
        CheckConstraint("status IN ('PENDING', 'SUCCEEDED', 'FAILED')"),
        UniqueConstraint("ticket_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    payment_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("payments.id"),
        nullable=False,
    )
    ticket_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("tickets.id"),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=False).with_variant(Integer, "sqlite"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(15), nullable=False, default="PENDING", server_default=text("'PENDING'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=False, default=utc_now
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=True
    )
