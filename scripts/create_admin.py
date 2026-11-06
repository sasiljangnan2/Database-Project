"""명시적으로 실행할 때만 .env의 DB에 개발 관리자 계정을 생성한다."""

import argparse
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User
from app.repositories.users import by_email
from app.schemas.auth import Register


def main() -> None:
    parser = argparse.ArgumentParser(
        description="개발 관리자 생성. 기존 회원 권한은 변경하지 않는다."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="개발 관리자")
    parser.add_argument("--phone", default="010-0000-0000")
    args = parser.parse_args()
    password = getpass("관리자 비밀번호(10~128자): ")
    if password != getpass("비밀번호 확인: "):
        raise SystemExit("비밀번호가 일치하지 않습니다.")
    try:
        payload = Register(email=args.email, password=password, name=args.name, phone=args.phone)
    except ValidationError:
        raise SystemExit("이메일·비밀번호 길이·이름·연락처를 확인하세요.") from None
    try:
        with SessionLocal() as db:
            if by_email(db, str(payload.email)):
                raise SystemExit("같은 이메일이 이미 있습니다. 기존 권한은 변경하지 않았습니다.")
            db.add(
                User(
                    email=str(payload.email),
                    password_hash=hash_password(payload.password),
                    name=payload.name,
                    phone=payload.phone,
                    role="ADMIN",
                    is_active=True,
                    token_version=0,
                )
            )
            db.commit()
    except SQLAlchemyError:
        raise SystemExit(
            "관리자를 생성하지 못했습니다. DB 연결·스키마·중복 이메일을 확인하세요."
        ) from None
    print("개발 관리자 계정을 생성했습니다. 비밀번호는 저장하거나 출력하지 않습니다.")


if __name__ == "__main__":
    main()
