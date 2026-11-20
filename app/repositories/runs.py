"""운행 검색·좌석 조회용 읽기 쿼리. 쓰기와 잠금은 서비스에서 처리한다."""

from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Fare,
    Reservation,
    Route,
    RouteStop,
    Run,
    RunStop,
    Seat,
    SeatOccupancy,
    Station,
    Ticket,
    Train,
    TrainType,
)


def active_station_ids(db: Session, *station_ids: int) -> set[int]:
    return set(
        db.scalars(
            select(Station.id).where(Station.id.in_(station_ids), Station.is_active.is_(True))
        )
    )


def candidate_runs(
    db: Session,
    departure_station_id: int,
    arrival_station_id: int,
    start: datetime,
    end: datetime,
    now: datetime,
):
    """승차역 출발이 [start, end) 안이고 아직 출발 전인 직통 운행과 승·하차 정차 쌍.

    정렬: 출발시각, 운행 ID, 승차 정차 ID, 하차 정차 ID.
    """
    boarding, alighting = aliased(RunStop), aliased(RunStop)
    boarding_stop, alighting_stop = aliased(RouteStop), aliased(RouteStop)
    statement = (
        select(Run, Train, TrainType, boarding, alighting)
        .join(Train, Train.id == Run.train_id)
        .join(TrainType, TrainType.code == Train.train_type_code)
        .join(Route, Route.id == Run.route_id)
        .join(boarding, boarding.run_id == Run.id)
        .join(alighting, alighting.run_id == Run.id)
        .join(boarding_stop, boarding_stop.id == boarding.route_stop_id)
        .join(alighting_stop, alighting_stop.id == alighting.route_stop_id)
        .where(
            Run.status == "ON_SALE",
            Train.is_active.is_(True),
            Route.is_active.is_(True),
            boarding_stop.station_id == departure_station_id,
            alighting_stop.station_id == arrival_station_id,
            boarding.stop_order < alighting.stop_order,
            boarding.departure_at.is_not(None),
            alighting.arrival_at.is_not(None),
            boarding.departure_at >= start,
            boarding.departure_at < end,
            boarding.departure_at > now,
        )
        .order_by(boarding.departure_at, Run.id, boarding.id, alighting.id)
    )
    return db.execute(statement).all()


def fares_by_class(
    db: Session, departure_station_id: int, arrival_station_id: int, train_type_code: str
) -> dict[str, int]:
    rows = db.execute(
        select(Fare.seat_class, Fare.amount).where(
            Fare.departure_station_id == departure_station_id,
            Fare.arrival_station_id == arrival_station_id,
            Fare.train_type_code == train_type_code,
        )
    )
    return {seat_class: amount for seat_class, amount in rows}


def train_seats(db: Session, train_id: int) -> list[Seat]:
    return list(
        db.scalars(
            select(Seat)
            .where(Seat.train_id == train_id)
            .order_by(Seat.carriage_no, Seat.seat_number, Seat.id)
        )
    )


def occupied_seat_ids(
    db: Session, run_id: int, first_order: int, alighting_order: int, now: datetime
) -> set[int]:
    """[first_order, alighting_order) 구간 중 하나라도 유효하게 점유된 좌석.

    발권·탑승 승차권과 기한이 남은 결제대기(HELD)만 유효하다. 취소·만료 승차권은 제외한다.
    구간별 잔여 수의 최솟값이 아니라, 요청 구간 전체에서 비어 있는 좌석만 가용으로 센다.
    """
    statement = (
        select(SeatOccupancy.seat_id)
        .join(Ticket, Ticket.id == SeatOccupancy.ticket_id)
        .join(Reservation, Reservation.id == Ticket.reservation_id)
        .where(
            SeatOccupancy.run_id == run_id,
            SeatOccupancy.segment_start_order >= first_order,
            SeatOccupancy.segment_start_order < alighting_order,
            or_(
                Ticket.status.in_(("ISSUED", "BOARDED")),
                and_(Ticket.status == "HELD", Reservation.expires_at > now),
            ),
        )
        .distinct()
    )
    return set(db.scalars(statement))


def run_stop_pair(db: Session, run_id: int, boarding_id: int, alighting_id: int):
    """운행에 속한 두 정차와 각 정차의 역 ID. 하나라도 이 운행의 정차가 아니면 빈 목록."""
    return db.execute(
        select(RunStop, RouteStop.station_id)
        .join(RouteStop, RouteStop.id == RunStop.route_stop_id)
        .where(RunStop.run_id == run_id, RunStop.id.in_((boarding_id, alighting_id)))
    ).all()
