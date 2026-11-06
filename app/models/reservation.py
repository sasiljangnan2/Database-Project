"""db/001_schema.sql과 대응하는 ORM 매핑. 스키마 변경은 SQL로 적용한다."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        Index("idx_reservation_user", "user_id", "created_at"),
        Index("idx_reservation_expiry", "status", "expires_at"),
        CheckConstraint("total_amount >= 0"),
        CheckConstraint("expires_at > created_at"),
        CheckConstraint(
            "status IN ('PENDING_PAYMENT', 'PAID', 'PARTIALLY_CANCELLED', 'CANCELLED', 'EXPIRED')"
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("users.id"),
        nullable=False,
    )
    run_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("runs.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
        default="PENDING_PAYMENT",
        server_default=text("'PENDING_PAYMENT'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=False, default=utc_now
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=False
    )
    total_amount: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=False).with_variant(Integer, "sqlite"), nullable=False
    )
