"""운행 시간표·검색일 규칙. DB에 접근하지 않는 순수 함수라 단독으로 테스트한다."""

from datetime import UTC, date, datetime, time, timedelta, timezone


def validate_stop_times(arrival: datetime | None, departure: datetime | None) -> str | None:
    """한 정차의 도착·출발 시각 규칙. 위반하면 사유를 반환한다."""
    if arrival is None and departure is None:
        return "도착 시각과 출발 시각 중 하나는 있어야 합니다."
    if arrival is not None and departure is not None and arrival > departure:
        return "도착 시각은 출발 시각보다 늦을 수 없습니다."
    return None


def validate_sequence(stops: list[tuple[int, datetime | None, datetime | None]]) -> str | None:
    """(정차순서, 도착, 출발) 목록이 진행 순서대로 시간이 흐르는지 확인한다.

    앞역을 떠난 시각(출발, 없으면 도착)은 다음역에 닿는 시각(도착, 없으면 출발)보다 빨라야 한다.
    자정을 넘기는 운행은 날짜가 증가한 일시로 입력하면 그대로 비교된다.
    """
    ordered = sorted(stops, key=lambda stop: stop[0])
    for previous, following in zip(ordered, ordered[1:], strict=False):
        # 앞 정차에 출발이 없으면 도착, 다음 정차에 도착이 없으면 출발로 대신 비교한다.
        leaves = previous[2] if previous[2] is not None else previous[1]
        reaches = following[1] if following[1] is not None else following[2]
        if leaves is not None and reaches is not None and not leaves < reaches:
            return f"{following[0]}번 정차의 시각이 앞 정차({previous[0]}번)보다 늦어야 합니다."
    return None


def time_window(times: list[datetime | None]) -> tuple[datetime, datetime] | None:
    present = [value for value in times if value is not None]
    return (min(present), max(present)) if present else None


def windows_overlap(first: tuple[datetime, datetime], second: tuple[datetime, datetime]) -> bool:
    """반개구간 [시작, 끝)이 겹치는지. 앞 운행 끝과 다음 운행 시작이 같으면 겹치지 않는다."""
    return first[0] < second[1] and second[0] < first[1]


# 한국은 일광절약시간이 없으므로 고정 +09:00으로 검색일을 계산한다.
KST = timezone(timedelta(hours=9))


def kst_day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    """한국시간 하루 [00:00, 다음날 00:00)를 DB 저장 형식(시간대 없는 UTC)으로 바꾼다."""
    start = datetime.combine(day, time.min, tzinfo=KST)
    end = start + timedelta(days=1)
    return (
        start.astimezone(UTC).replace(tzinfo=None),
        end.astimezone(UTC).replace(tzinfo=None),
    )
