"""김준하: 예약·시연 결제·취소. CurrentUser.id를 예약자로 사용한다. 업무 API는 담당자가 구현한다."""

from fastapi import APIRouter

router = APIRouter(prefix="/reservations", tags=["reservations"])
