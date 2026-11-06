from datetime import UTC, datetime


def utc_now() -> datetime:
    """MySQL DATETIME(6)에 저장하는 시간대 없는 UTC 시각."""
    return datetime.now(UTC).replace(tzinfo=None)
