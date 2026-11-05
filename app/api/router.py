from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """프로세스 생존 확인. DB 연결 상태를 의미하지 않는다."""
    return {"status": "ok", "scope": "process"}
