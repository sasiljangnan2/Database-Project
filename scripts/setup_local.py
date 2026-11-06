"""로컬 .env를 최초 한 번 생성한다. 기존 환경파일은 덮어쓰지 않는다."""

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    target = ROOT / ".env"
    if target.exists():
        print("기존 .env를 유지합니다. JWT_SECRET_KEY와 DB 설정을 확인하세요.")
        return
    content = (ROOT / ".env.example").read_text(encoding="utf-8")
    content = content.replace("JWT_SECRET_KEY=\n", f"JWT_SECRET_KEY={secrets.token_urlsafe(48)}\n")
    content = content.replace("ENABLE_FRONTEND_PREVIEW=false", "ENABLE_FRONTEND_PREVIEW=true")
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
    print("로컬 .env를 생성했습니다. 비밀키는 화면에 출력하지 않습니다.")
    print("Docker DB를 시작한 뒤 서버를 실행하세요. 프론트 미리보기: /dev/preview")


if __name__ == "__main__":
    main()
