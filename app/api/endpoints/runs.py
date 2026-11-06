"""김용우: 운행 검색·좌석 조회. 구간 잔여석은 DB 업무 규칙을 따른다."""

from fastapi import APIRouter

router = APIRouter(prefix="/runs", tags=["runs"])
