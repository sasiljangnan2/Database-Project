"""Disposable MySQL checks for the supplied ERD. No business services are implemented yet."""

import os
from pathlib import Path

import pytest
from pymysql.constants import CLIENT
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

import app.models  # noqa: F401
from app.db.base import Base

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def mysql_engine():
    dsn = os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL is required for disposable MySQL checks")
    url = make_url(dsn)
    if url.drivername != "mysql+pymysql" or not (url.database or "").endswith("_test"):
        pytest.fail("Use mysql+pymysql and a dedicated empty database ending in _test")
    engine = create_engine(url, connect_args={"client_flag": CLIENT.MULTI_STATEMENTS})
    try:
        if inspect(engine).get_table_names():
            pytest.fail("Test database must be empty; existing tables will not be removed")
        with engine.begin() as connection:
            for filename in ("001_schema.sql", "002_seed.sql"):
                with connection.connection.driver_connection.cursor() as cursor:
                    cursor.execute((ROOT / "db" / filename).read_text(encoding="utf-8"))
                    while cursor.nextset():
                        pass
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(mysql_engine):
    with mysql_engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


def make_ticket(db, boarding=5011, alighting=5013):
    fare_id, amount = {
        (5011, 5012): (902, 15000),
        (5012, 5013): (903, 15000),
        (5011, 5013): (901, 30000),
    }[boarding, alighting]
    user_id = db.exec_driver_sql(
        "INSERT INTO users (email, password_hash, name, phone, created_at) "
        "VALUES (UUID(), 'test-only-hash', 'Test', '000', UTC_TIMESTAMP(6))"
    ).lastrowid
    reservation_id = db.exec_driver_sql(
        "INSERT INTO reservations (user_id, run_id, created_at, expires_at, total_amount) "
        "VALUES (%s, 501, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6) + INTERVAL 10 MINUTE, %s)",
        (user_id, amount),
    ).lastrowid
    return db.exec_driver_sql(
        "INSERT INTO tickets (reservation_id, seat_id, boarding_run_stop_id, "
        "alighting_run_stop_id, fare_id, confirmed_amount) VALUES (%s, 101, %s, %s, %s, %s)",
        (reservation_id, boarding, alighting, fare_id, amount),
    ).lastrowid


def claim(db, ticket_id, segment):
    db.exec_driver_sql(
        "INSERT INTO seat_occupancies (run_id, seat_id, segment_start_order, ticket_id) "
        "VALUES (501, 101, %s, %s)",
        (segment, ticket_id),
    )


def test_adjacent_segments_can_use_the_same_seat(db):
    claim(db, make_ticket(db, 5011, 5012), 1)
    claim(db, make_ticket(db, 5012, 5013), 2)
    assert db.exec_driver_sql("SELECT COUNT(*) FROM seat_occupancies").scalar_one() == 2


def test_overlap_rejected_without_replacing_the_owner(db):
    first = make_ticket(db)
    second = make_ticket(db, 5012, 5013)
    claim(db, first, 1)
    claim(db, first, 2)
    with pytest.raises(IntegrityError) as error:
        claim(db, second, 2)
    assert error.value.orig.args[0] == 1062
    assert (
        db.exec_driver_sql(
            "SELECT ticket_id FROM seat_occupancies WHERE run_id=501 AND seat_id=101 "
            "AND segment_start_order=2"
        ).scalar_one()
        == first
    )


def test_release_preserves_ticket_history_and_allows_resale(db):
    first = make_ticket(db, 5011, 5012)
    claim(db, first, 1)
    db.exec_driver_sql("UPDATE tickets SET status='CANCELLED' WHERE id=%s", (first,))
    db.exec_driver_sql("DELETE FROM seat_occupancies WHERE ticket_id=%s", (first,))
    second = make_ticket(db, 5011, 5012)
    claim(db, second, 1)
    assert db.exec_driver_sql("SELECT status FROM tickets WHERE id=%s", (first,)).scalar_one() == (
        "CANCELLED"
    )


def test_unknown_train_type_is_rejected(db):
    with pytest.raises(IntegrityError) as error:
        db.exec_driver_sql(
            "INSERT INTO trains (identifier, train_type_code) VALUES ('BAD-TYPE', 'MISSING')"
        )
    assert error.value.orig.args[0] == 1452


def test_shared_orm_columns_and_nullability_match_real_mysql(mysql_engine):
    inspector = inspect(mysql_engine)
    assert set(inspector.get_table_names()) == set(Base.metadata.tables)
    for name, table in Base.metadata.tables.items():
        actual = {column["name"]: column["nullable"] for column in inspector.get_columns(name)}
        assert actual == {column.name: column.nullable for column in table.columns}, name
        assert inspector.get_pk_constraint(name)["constrained_columns"] == list(
            table.primary_key.columns.keys()
        )
