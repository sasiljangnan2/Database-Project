from fastapi import APIRouter

from app.schemas.common import Health

router = APIRouter(tags=["system"])


@router.get("/health", response_model=Health, operation_id="get__health")
def health():
    """프로세스 생존 확인. DB 연결 상태를 의미하지 않는다."""
    return Health(status="ok", scope="process")
