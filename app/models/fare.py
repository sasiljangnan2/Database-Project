"""db/001_schema.sql과 대응하는 ORM 매핑. 스키마 변경은 SQL로 적용한다."""

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Fare(Base):
    __tablename__ = "fares"
    __table_args__ = (
        UniqueConstraint(
            "departure_station_id", "arrival_station_id", "train_type_code", "seat_class"
        ),
        CheckConstraint("departure_station_id <> arrival_station_id"),
        CheckConstraint("amount >= 0"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    departure_station_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("stations.id"),
        nullable=False,
    )
    arrival_station_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        ForeignKey("stations.id"),
        nullable=False,
    )
    train_type_code: Mapped[str] = mapped_column(
        String(30), ForeignKey("train_types.code", name="fk_fares_type"), nullable=False
    )
    seat_class: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=False).with_variant(Integer, "sqlite"), nullable=False
    )
