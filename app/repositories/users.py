from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def by_email(db: Session, email: str, *, for_update: bool = False) -> User | None:
    statement = select(User).where(User.email == email)
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return db.scalar(statement)


def by_id(db: Session, user_id: int, *, for_update: bool = False) -> User | None:
    statement = select(User).where(User.id == user_id)
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return db.scalar(statement)
