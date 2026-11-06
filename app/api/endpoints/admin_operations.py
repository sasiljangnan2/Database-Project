"""김준하: 운영 조회·운행 취소·환불·탑승. AdminUser를 사용한다. 업무 API는 담당자가 구현한다."""

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin_operations"])
