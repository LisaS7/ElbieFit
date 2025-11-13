from datetime import date, datetime, timedelta, timezone

from app.utils.dates import date_to_iso, dt_to_iso, now


def test_dt_to_iso_converts_to_utc_and_adds_z_suffix():
    # 2025-01-01 12:00 in UTC+2 -> 10:00 UTC
    local_dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=2)))

    result = dt_to_iso(local_dt)

    assert result == "2025-01-01T10:00:00Z"


def test_dt_to_iso_keeps_utc_and_normalises_suffix():
    utc_dt = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    result = dt_to_iso(utc_dt)

    assert result == "2025-01-01T10:00:00Z"


def test_date_to_iso_returns_simple_iso_date_string():
    d = date(2025, 11, 13)

    result = date_to_iso(d)

    assert result == "2025-11-13"
    assert "T" not in result


def test_now_returns_timezone_aware_utc_datetime():
    result = now()

    assert isinstance(result, datetime)
    # tzinfo might not be exactly timezone.utc object, but .tzname() should be 'UTC'
    assert result.tzinfo is not None
    assert result.tzinfo.utcoffset(result) == timedelta(0)
