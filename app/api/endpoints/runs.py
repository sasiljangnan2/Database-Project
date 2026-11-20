"""김용우: 운행 검색·좌석 조회. 구간 잔여석은 요청 구간 전체가 비어 있는 좌석만 센다."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.catalog import RunSearchItem, SeatAvailability
from app.schemas.common import Error, Page
from app.services import search

router = APIRouter(
    prefix="/runs",
    tags=["runs"],
    responses={code: {"model": Error} for code in (401, 404, 409, 422, 503)},
)


@router.get("", response_model=Page[RunSearchItem], operation_id="get__runs")
def search_runs(
    user: CurrentUser,
    db: DbSession,
    departure_station_id: Annotated[int, Query(ge=1)],
    arrival_station_id: Annotated[int, Query(ge=1)],
    departure_date: Annotated[date, Query(description="승차역 출발일(Asia/Seoul)")],
    passenger_count: Annotated[int, Query(ge=1, le=9)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """직통 운행 검색. 판매중이고 아직 출발 전이며 필요 인원 이상 남은 운행만 반환한다."""
    return search.search_runs(
        db,
        departure_station_id,
        arrival_station_id,
        departure_date,
        passenger_count,
        page,
        size,
    )


@router.get(
    "/{run_id}/seats",
    response_model=list[SeatAvailability],
    operation_id="get__runs_run_id_seats",
)
def run_seats(
    user: CurrentUser,
    db: DbSession,
    run_id: Annotated[int, Path(ge=1)],
    boarding_run_stop_id: Annotated[int, Query(ge=1)],
    alighting_run_stop_id: Annotated[int, Query(ge=1)],
):
    """선택 구간 전체에서 비어 있는 좌석을 표시한다. 좌석을 임시로 잡지는 않는다."""
    return search.run_seats(db, run_id, boarding_run_stop_id, alighting_run_stop_id)
