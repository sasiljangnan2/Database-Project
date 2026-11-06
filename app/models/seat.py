"""db/001_schema.sql과 대응하는 ORM 매핑. 스키마 변경은 SQL로 적용한다."""

from sqlalchemy import CheckConstraint, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("train_id", "carriage_no", "seat_number"),
        CheckConstraint("carriage_no > 0"),
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
    carriage_no: Mapped[int] = mapped_column(
        SmallInteger().with_variant(mysql.SMALLINT(unsigned=True), "mysql"), nullable=False
    )
    seat_number: Mapped[str] = mapped_column(String(10), nullable=False)
    seat_class: Mapped[str] = mapped_column(String(20), nullable=False)
