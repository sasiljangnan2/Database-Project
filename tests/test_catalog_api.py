"""기준정보·운행 검색·관리 API 통합 테스트(SQLite). MySQL 잠금 동작은 대체하지 않는다.

전체 16개 테이블을 SQLite에 만들고 FK를 켠다. 열차 행 잠금(FOR UPDATE)은 SQLite가 무시하므로
동시성은 MySQL 환경에서 따로 검증한다.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
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
    User,
)

PASSWORD = "member-test-password-123"
API = "/api/v1"
# 시연 운행: 지금부터 이틀 뒤 정각에 A역 출발, 40분 B역, 80분 C역 도착(UTC).
NOW = datetime.now(UTC).replace(tzinfo=None, minute=0, second=0, microsecond=0)
BASE = NOW + timedelta(days=2)
SEARCH_DATE = (BASE + timedelta(hours=9)).date().isoformat()  # Asia/Seoul 검색일


def iso(value):
    return value.isoformat() + "Z"


@pytest.fixture
def ctx(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", SecretStr("test-key-" + "a" * 48))
    monkeypatch.setattr(settings, "enable_frontend_preview", False)
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    seed(engine)
    application = create_app()

    def sessions():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    application.dependency_overrides[get_db] = sessions
    with TestClient(application) as client:
        yield client, engine
    engine.dispose()


def seed(engine):
    """부모 행부터 단계별로 flush한다. relationship이 없어 FK 순서가 자동 보장되지 않는다."""
    with Session(engine) as db:
        levels = [
            [
                User(
                    id=1,
                    email="admin@example.com",
                    password_hash=hash_password(PASSWORD),
                    name="관리자",
                    phone="010",
                    role="ADMIN",
                ),
                User(
                    id=2,
                    email="member@example.com",
                    password_hash=hash_password(PASSWORD),
                    name="회원",
                    phone="010",
                ),
                Station(id=1, name="A역"),
                Station(id=2, name="B역"),
                Station(id=3, name="C역"),
                Station(id=4, name="폐역", is_active=False),
                TrainType(code="EXPRESS", name="급행"),
                Route(id=1, name="A~C"),
                Route(id=2, name="다른 노선"),
            ],
            [Train(id=1, identifier="TRAIN-010", train_type_code="EXPRESS")],
            [
                Seat(id=101, train_id=1, carriage_no=1, seat_number="1A", seat_class="STANDARD"),
                Seat(id=102, train_id=1, carriage_no=1, seat_number="1B", seat_class="STANDARD"),
                RouteStop(id=1, route_id=1, station_id=1, stop_order=1),
                RouteStop(id=2, route_id=1, station_id=2, stop_order=2),
                RouteStop(id=3, route_id=1, station_id=3, stop_order=3),
                RouteStop(id=4, route_id=2, station_id=1, stop_order=1),
                Fare(
                    id=901,
                    departure_station_id=1,
                    arrival_station_id=3,
                    train_type_code="EXPRESS",
                    seat_class="STANDARD",
                    amount=30000,
                ),
                Fare(
                    id=902,
                    departure_station_id=1,
                    arrival_station_id=2,
                    train_type_code="EXPRESS",
                    seat_class="STANDARD",
                    amount=15000,
                ),
                Fare(
                    id=903,
                    departure_station_id=2,
                    arrival_station_id=3,
                    train_type_code="EXPRESS",
                    seat_class="STANDARD",
                    amount=15000,
                ),
                Run(
                    id=501,
                    train_id=1,
                    route_id=1,
                    service_number="T101",
                    service_date=(BASE + timedelta(hours=9)).date(),
                    direction="A_TO_C",
                ),
            ],
            [
                RunStop(
                    id=5011,
                    run_id=501,
                    route_stop_id=1,
                    stop_order=1,
                    arrival_at=None,
                    departure_at=BASE,
                ),
                RunStop(
                    id=5012,
                    run_id=501,
                    route_stop_id=2,
                    stop_order=2,
                    arrival_at=BASE + timedelta(minutes=40),
                    departure_at=BASE + timedelta(minutes=45),
                ),
                RunStop(
                    id=5013,
                    run_id=501,
                    route_stop_id=3,
                    stop_order=3,
                    arrival_at=BASE + timedelta(minutes=80),
                    departure_at=None,
                ),
            ],
        ]
        for rows in levels:
            db.add_all(rows)
            db.flush()
        db.commit()


def token(client, email):
    response = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin(ctx):
    return token(ctx[0], "admin@example.com")


@pytest.fixture
def member(ctx):
    return token(ctx[0], "member@example.com")


def occupy(engine, *, seat_id, segments, status, expires_in):
    """승차권 하나와 그 구간 점유 행들을 직접 만든다. 예약 서비스는 다른 담당자 영역이다."""
    with Session(engine) as db:
        now = datetime.now(UTC).replace(tzinfo=None)
        reservation = Reservation(
            user_id=2,
            run_id=501,
            status="PENDING_PAYMENT" if status == "HELD" else "PAID",
            created_at=now - timedelta(minutes=30),
            expires_at=now + timedelta(minutes=expires_in),
            total_amount=30000,
        )
        db.add(reservation)
        db.flush()
        ticket = Ticket(
            reservation_id=reservation.id,
            seat_id=seat_id,
            boarding_run_stop_id=5011,
            alighting_run_stop_id=5013,
            fare_id=901,
            confirmed_amount=30000,
            status=status,
        )
        db.add(ticket)
        db.flush()
        db.add_all(
            SeatOccupancy(run_id=501, seat_id=seat_id, segment_start_order=s, ticket_id=ticket.id)
            for s in segments
        )
        db.commit()


# ---------- 공개 조회 ----------


def test_public_catalog_lists_only_active_stations(ctx):
    client, _ = ctx
    response = client.get(f"{API}/stations")
    assert response.status_code == 200
    body = response.json()
    assert [item["name"] for item in body["items"]] == ["A역", "B역", "C역"]
    assert body["total"] == 3 and body["page"] == 1
    assert client.get(f"{API}/stations", params={"keyword": "B"}).json()["total"] == 1
    assert client.get(f"{API}/train-types").json()["items"] == [{"code": "EXPRESS", "name": "급행"}]


# ---------- 권한 ----------


def test_admin_routes_require_an_administrator(ctx, member):
    client, _ = ctx
    assert client.get(f"{API}/admin/stations").status_code == 401
    forbidden = client.get(f"{API}/admin/stations", headers=member)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "ADMIN_REQUIRED"


# ---------- 기준정보 관리 ----------


def test_station_crud_and_patch_validation(ctx, admin):
    client, _ = ctx
    created = client.post(
        f"{API}/admin/stations", json={"name": "D역", "is_active": True}, headers=admin
    )
    assert created.status_code == 201
    station_id = created.json()["id"]
    empty = client.patch(f"{API}/admin/stations/{station_id}", json={}, headers=admin)
    assert empty.status_code == 422
    patched = client.patch(
        f"{API}/admin/stations/{station_id}", json={"is_active": False}, headers=admin
    )
    assert patched.json()["is_active"] is False
    assert client.delete(f"{API}/admin/stations/{station_id}", headers=admin).status_code == 200
    assert client.delete(f"{API}/admin/stations/{station_id}", headers=admin).status_code == 404


def test_duplicates_conflict_and_referenced_rows_cannot_be_deleted(ctx, admin):
    client, _ = ctx
    duplicate = client.post(
        f"{API}/admin/train-types", json={"code": "EXPRESS", "name": "또"}, headers=admin
    )
    assert (duplicate.status_code, duplicate.json()["error"]["code"]) == (409, "RESOURCE_CONFLICT")
    in_use = client.delete(f"{API}/admin/train-types/EXPRESS", headers=admin)
    assert (in_use.status_code, in_use.json()["error"]["code"]) == (409, "RESOURCE_IN_USE")
    assert (
        client.post(
            f"{API}/admin/train-types", json={"code": "KTX", "name": "KTX"}, headers=admin
        ).status_code
        == 201
    )
    assert client.delete(f"{API}/admin/train-types/KTX", headers=admin).status_code == 200


def test_train_with_unknown_type_is_rejected_as_input_error(ctx, admin):
    client, _ = ctx
    response = client.post(
        f"{API}/admin/trains",
        json={"identifier": "T-2", "train_type_code": "NOPE", "is_active": True},
        headers=admin,
    )
    assert (response.status_code, response.json()["error"]["code"]) == (422, "VALIDATION_ERROR")


def test_fare_needs_different_stations_and_keeps_keys_once_ticketed(ctx, admin):
    client, engine = ctx
    same = client.post(
        f"{API}/admin/fares",
        json={
            "departure_station_id": 1,
            "arrival_station_id": 1,
            "train_type_code": "EXPRESS",
            "seat_class": "STANDARD",
            "amount": 1,
        },
        headers=admin,
    )
    assert same.status_code == 422
    occupy(engine, seat_id=101, segments=[1, 2], status="ISSUED", expires_in=-1)
    amount_only = client.patch(f"{API}/admin/fares/901", json={"amount": 31000}, headers=admin)
    assert amount_only.status_code == 200
    blocked = client.patch(f"{API}/admin/fares/901", json={"seat_class": "FIRST"}, headers=admin)
    assert (blocked.status_code, blocked.json()["error"]["code"]) == (409, "RESOURCE_IN_USE")


def test_route_stops_are_frozen_once_the_route_has_runs(ctx, admin):
    client, _ = ctx
    response = client.post(
        f"{API}/admin/route-stops",
        json={"route_id": 1, "station_id": 4, "stop_order": 4},
        headers=admin,
    )
    assert (response.status_code, response.json()["error"]["code"]) == (409, "RESOURCE_IN_USE")
    free = client.post(
        f"{API}/admin/route-stops",
        json={"route_id": 2, "station_id": 2, "stop_order": 2},
        headers=admin,
    )
    assert free.status_code == 201


# ---------- 운행 편성 ----------


def new_run(client, admin, number="T202"):
    response = client.post(
        f"{API}/admin/runs",
        json={
            "train_id": 1,
            "route_id": 1,
            "service_number": number,
            "service_date": SEARCH_DATE,
            "status": "ON_SALE",
            "direction": "A_TO_C",
        },
        headers=admin,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def stop(client, admin, run_id, route_stop_id, order, arrival, departure):
    return client.post(
        f"{API}/admin/run-stops",
        json={
            "run_id": run_id,
            "route_stop_id": route_stop_id,
            "stop_order": order,
            "arrival_at": arrival and iso(arrival),
            "departure_at": departure and iso(departure),
        },
        headers=admin,
    )


def test_run_stops_follow_timetable_rules_and_block_train_overlap(ctx, admin):
    client, _ = ctx
    run_id = new_run(client, admin)
    inside = stop(client, admin, run_id, 1, 1, None, BASE + timedelta(minutes=30))
    assert (inside.status_code, inside.json()["error"]["code"]) == (409, "RUN_TIME_CONFLICT")
    backwards = stop(
        client, admin, run_id, 1, 1, BASE + timedelta(minutes=200), BASE + timedelta(minutes=190)
    )
    assert backwards.status_code == 422
    wrong_route = stop(client, admin, run_id, 4, 1, None, BASE + timedelta(minutes=200))
    assert wrong_route.status_code == 422
    # 앞 운행이 끝나는 80분과 같은 시각에 시작하는 운행은 허용한다(반개구간).
    back_to_back = stop(client, admin, run_id, 1, 1, None, BASE + timedelta(minutes=80))
    assert back_to_back.status_code == 201
    too_early = stop(client, admin, run_id, 2, 2, BASE + timedelta(minutes=80), None)
    assert too_early.status_code == 422  # 앞 정차 출발과 같은 시각 도착은 불가
    later = stop(client, admin, run_id, 2, 2, BASE + timedelta(minutes=120), None)
    assert later.status_code == 201


def test_runs_cannot_be_cancelled_through_general_patch(ctx, admin):
    client, _ = ctx
    run_id = new_run(client, admin)
    assert (
        client.patch(
            f"{API}/admin/runs/{run_id}", json={"status": "CANCELLED"}, headers=admin
        ).status_code
        == 422
    )
    assert (
        client.patch(f"{API}/admin/runs/{run_id}", json={"status": "CLOSED"}, headers=admin).json()[
            "status"
        ]
        == "CLOSED"
    )
    assert client.delete(f"{API}/admin/runs/{run_id}", headers=admin).status_code == 405


def test_runs_with_reservations_keep_their_schedule(ctx, admin):
    client, engine = ctx
    occupy(engine, seat_id=101, segments=[1, 2], status="ISSUED", expires_in=-1)
    changed = client.patch(f"{API}/admin/runs/501", json={"direction": "C_TO_A"}, headers=admin)
    assert (changed.status_code, changed.json()["error"]["code"]) == (409, "RESOURCE_IN_USE")
    assert (
        client.patch(f"{API}/admin/runs/501", json={"status": "CLOSED"}, headers=admin).status_code
        == 200
    )
    assert client.delete(f"{API}/admin/run-stops/5012", headers=admin).status_code == 409


# ---------- 검색·좌석 ----------


def search(client, member, **changes):
    params = {
        "departure_station_id": 1,
        "arrival_station_id": 3,
        "departure_date": SEARCH_DATE,
        "passenger_count": 1,
    } | changes
    return client.get(f"{API}/runs", params=params, headers=member)


def test_search_requires_login_and_valid_input(ctx, member):
    client, _ = ctx
    assert client.get(f"{API}/runs").status_code == 401
    assert search(client, member, arrival_station_id=1).status_code == 422
    assert search(client, member, passenger_count=10).status_code == 422
    assert search(client, member, arrival_station_id=4).status_code == 422  # 폐역


def test_search_counts_only_seats_free_for_the_whole_requested_interval(ctx, member):
    client, engine = ctx
    first = search(client, member).json()
    assert first["total"] == 1
    item = first["items"][0]
    assert (item["run_id"], item["boarding_run_stop_id"], item["alighting_run_stop_id"]) == (
        501,
        5011,
        5013,
    )
    assert item["train_type_name"] == "급행" and item["direction"] == "A_TO_C"
    assert item["fares"] == [{"seat_class": "STANDARD", "amount": 30000, "available_seats": 2}]

    occupy(engine, seat_id=101, segments=[2], status="ISSUED", expires_in=-1)  # B→C 구간만
    occupy(engine, seat_id=102, segments=[1, 2], status="HELD", expires_in=-5)  # 기한 지난 HELD
    a_to_c = search(client, member).json()["items"][0]["fares"][0]
    assert a_to_c["available_seats"] == 1  # 101은 A→C 중 B→C가 막혀 있어 제외, 102는 무시
    a_to_b = search(client, member, arrival_station_id=2).json()["items"][0]["fares"][0]
    assert a_to_b["available_seats"] == 2  # 연속 판매: B→C 점유는 A→B에 영향 없음
    assert search(client, member, passenger_count=2).json()["total"] == 0


def test_valid_held_reservation_blocks_seats_until_it_expires(ctx, member):
    client, engine = ctx
    occupy(engine, seat_id=101, segments=[1, 2], status="HELD", expires_in=5)
    assert search(client, member).json()["items"][0]["fares"][0]["available_seats"] == 1


def test_search_skips_other_dates_and_closed_runs(ctx, member, admin):
    client, _ = ctx
    other_day = (BASE + timedelta(days=3)).date().isoformat()
    assert search(client, member, departure_date=other_day).json()["total"] == 0
    client.patch(f"{API}/admin/runs/501", json={"status": "CLOSED"}, headers=admin)
    assert search(client, member).json()["total"] == 0


def test_seat_availability_for_a_selected_interval(ctx, member):
    client, engine = ctx
    occupy(engine, seat_id=101, segments=[2], status="BOARDED", expires_in=-1)
    url = f"{API}/runs/501/seats"
    full = client.get(
        url, params={"boarding_run_stop_id": 5011, "alighting_run_stop_id": 5013}, headers=member
    )
    assert full.status_code == 200
    assert [(s["seat_number"], s["available"], s["amount"]) for s in full.json()] == [
        ("1A", False, 30000),
        ("1B", True, 30000),
    ]
    first_leg = client.get(
        url, params={"boarding_run_stop_id": 5011, "alighting_run_stop_id": 5012}, headers=member
    )
    assert [s["available"] for s in first_leg.json()] == [True, True]
    assert [s["amount"] for s in first_leg.json()] == [15000, 15000]


def test_seat_query_rejects_wrong_stops_and_unknown_runs(ctx, member):
    client, _ = ctx
    url = f"{API}/runs/501/seats"
    reversed_stops = client.get(
        url, params={"boarding_run_stop_id": 5013, "alighting_run_stop_id": 5011}, headers=member
    )
    assert reversed_stops.status_code == 422
    foreign = client.get(
        url, params={"boarding_run_stop_id": 5011, "alighting_run_stop_id": 9999}, headers=member
    )
    assert foreign.status_code == 422
    assert (
        client.get(
            f"{API}/runs/999/seats",
            params={"boarding_run_stop_id": 1, "alighting_run_stop_id": 2},
            headers=member,
        ).status_code
        == 404
    )


# ---------- 회원 관리 ----------


def test_admin_deactivating_a_member_revokes_the_member_token(ctx, admin, member):
    client, _ = ctx
    users = client.get(f"{API}/admin/users", headers=admin).json()
    assert users["total"] == 2 and "password_hash" not in users["items"][0]
    response = client.patch(f"{API}/admin/users/2", json={"is_active": False}, headers=admin)
    assert response.status_code == 200 and response.json()["is_active"] is False
    assert client.get(f"{API}/users/me", headers=member).status_code == 401
    relogin = client.post(
        f"{API}/auth/login", json={"email": "member@example.com", "password": PASSWORD}
    )
    assert relogin.status_code == 401


def test_admin_cannot_deactivate_themselves_or_change_other_fields(ctx, admin):
    client, _ = ctx
    own = client.patch(f"{API}/admin/users/1", json={"is_active": False}, headers=admin)
    assert (own.status_code, own.json()["error"]["code"]) == (409, "INVALID_STATE")
    other = client.patch(f"{API}/admin/users/2", json={"role": "ADMIN"}, headers=admin)
    assert other.status_code == 422
