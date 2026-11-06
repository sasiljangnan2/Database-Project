"""db/001_schema.sql과 대응하는 ORM 매핑. 스키마 변경은 SQL로 적용한다."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TrainType(Base):
    __tablename__ = "train_types"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    code: Mapped[str] = mapped_column(
        String(30), primary_key=True, autoincrement=False, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
