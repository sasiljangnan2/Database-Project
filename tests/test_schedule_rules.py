"""운행 시간표·검색일 순수 규칙. DB와 HTTP 없이 실행한다."""

from datetime import date, datetime, timedelta

from app.services.rules import (
    kst_day_bounds_utc,
    time_window,
    validate_sequence,
    validate_stop_times,
    windows_overlap,
)

T0 = datetime(2026, 12, 1, 0, 0)


def at(minutes):
    return T0 + timedelta(minutes=minutes)


def test_a_stop_needs_a_time_and_arrival_cannot_follow_departure():
    assert validate_stop_times(None, None)
    assert validate_stop_times(at(10), at(5))
    assert validate_stop_times(at(5), at(5)) is None  # 도착 = 출발은 허용
    assert validate_stop_times(None, at(5)) is None  # 시발역
    assert validate_stop_times(at(5), None) is None  # 종착역


def test_stops_must_progress_in_time_by_stop_order():
    ok = [(1, None, at(0)), (2, at(40), at(45)), (3, at(80), None)]
    assert validate_sequence(ok) is None
    assert validate_sequence(list(reversed(ok))) is None  # 입력 순서와 무관하게 순서 번호로 비교
    assert validate_sequence([(1, None, at(0)), (2, at(0), at(5))])  # 앞 출발 = 다음 도착 불가
    assert validate_sequence([(1, None, at(50)), (2, at(40), at(45))])
    assert validate_sequence([(1, None, at(0)), (2, at(40), at(45)), (3, at(44), None)])


def test_overnight_run_is_compared_by_real_datetime():
    late = [(1, None, at(23 * 60 + 50)), (2, at(24 * 60 + 20), None)]
    assert validate_sequence(late) is None


def test_run_windows_are_half_open_so_back_to_back_runs_are_allowed():
    first = time_window([None, at(0), at(60), None])
    second = time_window([at(60), at(120)])
    assert first == (at(0), at(60))
    assert not windows_overlap(first, second)
    assert not windows_overlap(second, first)
    assert windows_overlap(first, time_window([at(59), at(90)]))
    assert windows_overlap(time_window([at(10), at(20)]), first)  # 포함
    assert time_window([None, None]) is None


def test_korean_search_day_maps_to_the_previous_utc_evening():
    start, end = kst_day_bounds_utc(date(2026, 12, 1))
    assert start == datetime(2026, 11, 30, 15, 0)
    assert end == datetime(2026, 12, 1, 15, 0)
    # 한국시간 12/1 09:00 = UTC 00:00 은 12/1 검색 범위에 들어간다.
    assert start <= datetime(2026, 12, 1, 0, 0) < end
    # 한국시간 12/2 00:30 = UTC 12/1 15:30 은 12/1 범위 밖이다.
    assert not start <= datetime(2026, 12, 1, 15, 30) < end
