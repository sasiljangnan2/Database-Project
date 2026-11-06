"""김준하: 본인 승차권. 타인 승차권은 404로 처리한다. 업무 API는 담당자가 구현한다."""

from fastapi import APIRouter

router = APIRouter(prefix="/tickets", tags=["tickets"])
