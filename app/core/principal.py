from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    """서버가 검증한 로그인 사용자. token_version은 API 응답에 노출하지 않는다."""

    id: int
    email: str
    name: str
    phone: str
    role: str
    is_active: bool
    token_version: int
