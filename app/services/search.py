"""직통 운행 검색과 구간 좌석 조회(김용우). 읽기 전용이며 좌석을 잡지 않는다."""

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models import Run, Train
from app.repositories import runs as repo
from app.schemas.catalog import FareSummary, RunSearchItem, SeatAvailability
from app.schemas.common import Page
from app.services import crud
from app.services.rules import kst_day_bounds_utc


def search_runs(
    db: Session,
    departure_station_id: int,
    arrival_station_id: int,
    departure_date: date,
    passenger_count: int,
    page: int,
    size: int,
    *,
    now: datetime | None = None,
) -> Page:
    if departure_station_id == arrival_station_id:
        raise crud.invalid_input("출발역과 도착역은 달라야 합니다.", "arrival_station_id")
    if repo.active_station_ids(db, departure_station_id, arrival_station_id) != {
        departure_station_id,
        arrival_station_id,
    }:
        raise crud.invalid_input("운영 중인 역을 선택해 주세요.", "departure_station_id")
    now = now or utc_now()
    start, end = kst_day_bounds_utc(departure_date)
    items: list[RunSearchItem] = []
    fare_cache: dict[str, dict[str, int]] = {}
    seat_cache: dict[int, list] = {}
    for run, train, train_type, boarding, alighting in repo.candidate_runs(
        db, departure_station_id, arrival_station_id, start, end, now
    ):
        if train.train_type_code not in fare_cache:
            fare_cache[train.train_type_code] = repo.fares_by_class(
                db, departure_station_id, arrival_station_id, train.train_type_code
            )
        fares = fare_cache[train.train_type_code]
        if not fares:
            continue  # 운임이 없는 구간은 판매할 수 없다.
        if train.id not in seat_cache:
            seat_cache[train.id] = repo.train_seats(db, train.id)
        occupied = repo.occupied_seat_ids(
            db, run.id, boarding.stop_order, alighting.stop_order, now
        )
        summaries = []
        for seat_class in sorted(fares):
            available = sum(
                1
                for seat in seat_cache[train.id]
                if seat.seat_class == seat_class and seat.id not in occupied
            )
            summaries.append(
                FareSummary(
                    seat_class=seat_class, amount=fares[seat_class], available_seats=available
                )
            )
        if not any(summary.available_seats >= passenger_count for summary in summaries):
            continue
        items.append(
            RunSearchItem(
                run_id=run.id,
                service_number=run.service_number,
                train_type_code=train_type.code,
                train_type_name=train_type.name,
                direction=run.direction,
                boarding_run_stop_id=boarding.id,
                alighting_run_stop_id=alighting.id,
                departure_at=boarding.departure_at,
                arrival_at=alighting.arrival_at,
                fares=summaries,
            )
        )
    # 시연 규모(하루·한 구간)의 결과를 모두 계산한 뒤 페이지로 자른다.
    first = (page - 1) * size
    return Page[RunSearchItem](
        items=items[first : first + size], page=page, size=size, total=len(items)
    )


def run_seats(
    db: Session,
    run_id: int,
    boarding_run_stop_id: int,
    alighting_run_stop_id: int,
    *,
    now: datetime | None = None,
) -> list[SeatAvailability]:
    now = now or utc_now()
    run = db.get(Run, run_id)
    if run is None:
        raise crud.not_found("운행을 찾을 수 없습니다.")
    if run.status == "CANCELLED":
        raise crud.invalid_state("취소된 운행입니다.")
    pair = {
        stop.id: (stop, station_id)
        for stop, station_id in repo.run_stop_pair(
            db, run_id, boarding_run_stop_id, alighting_run_stop_id
        )
    }
    if boarding_run_stop_id == alighting_run_stop_id or len(pair) != 2:
        raise crud.invalid_input("이 운행의 서로 다른 승·하차 정차를 선택해 주세요.", "run_stop")
    boarding, departure_station = pair[boarding_run_stop_id]
    alighting, arrival_station = pair[alighting_run_stop_id]
    if not boarding.stop_order < alighting.stop_order:
        raise crud.invalid_input("승차 정차는 하차 정차보다 앞이어야 합니다.", "run_stop")
    train = db.get(Train, run.train_id)
    fares = repo.fares_by_class(db, departure_station, arrival_station, train.train_type_code)
    if not fares:
        raise crud.invalid_input("선택한 구간의 운임이 없습니다.", "run_stop")
    occupied = repo.occupied_seat_ids(db, run.id, boarding.stop_order, alighting.stop_order, now)
    for_sale = (
        run.status == "ON_SALE"
        and boarding.departure_at is not None
        and boarding.departure_at > now
    )
    return [
        SeatAvailability(
            seat_id=seat.id,
            carriage_no=seat.carriage_no,
            seat_number=seat.seat_number,
            seat_class=seat.seat_class,
            available=for_sale and seat.id not in occupied,
            amount=fares[seat.seat_class],
        )
        for seat in repo.train_seats(db, train.id)
        if seat.seat_class in fares
    ]
