from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """DB 변경은 db/의 SQL로 적용한다. 앱 시작 시 create_all을 호출하지 않는다."""
