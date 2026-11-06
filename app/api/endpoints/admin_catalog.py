"""김용우: 기준정보·운행·운임 관리. AdminUser를 사용한다. 업무 API는 담당자가 구현한다."""

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin_catalog"])
