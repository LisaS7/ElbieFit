from datetime import date as DateType
from datetime import datetime, timedelta, timezone

import pytest

from app.utils import dates

# ─────────────────────────────────────────
# ISO
# ─────────────────────────────────────────


def test_iso_to_dt_parses_z_suffix_as_utc():
    dt = dates.iso_to_dt("2025-01-01T10:00:00Z")

    assert isinstance(dt, datetime)
    assert dt.tzinfo is not None
    assert dt.tzinfo.utcoffset(dt) == timedelta(0)
    assert dt == datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


# ─────────────────────────────────────────
# Timezone
# ─────────────────────────────────────────


def test_safe_zoneinfo_returns_utc_when_tz_missing():
    tz = dates._safe_zoneinfo(None)

    # ZoneInfo("UTC") is a specific object; easiest is to check key/offset behavior
    assert tz.key == "UTC"
    dt = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc).astimezone(tz)
    assert dt.utcoffset() == timedelta(0)


def test_safe_zoneinfo_returns_utc_when_tz_invalid():
    tz = dates._safe_zoneinfo("Not/A_Real_Timezone")

    assert tz.key == "UTC"


def test_today_in_tz_uses_timezone_and_falls_back_to_utc(monkeypatch):
    # Freeze "now" at a known UTC moment near midnight edge-cases.
    frozen = datetime(2025, 1, 1, 23, 30, tzinfo=timezone.utc)

    monkeypatch.setattr(dates, "now", lambda: frozen)

    # UTC date should be 2025-01-01
    assert dates.today_in_tz("UTC") == DateType(2025, 1, 1)

    # London in winter is UTC+0, so same date here
    assert dates.today_in_tz("Europe/London") == DateType(2025, 1, 1)

    # Invalid tz should fall back to UTC (hits the exception branch via today_in_tz -> now_in_tz -> _safe_zoneinfo)
    assert dates.today_in_tz("Nope/DefinitelyNot") == DateType(2025, 1, 1)


# ─────────────────────────────────────────
# Formatting
# ─────────────────────────────────────────


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, "0s"),  # <= 0 branch
        (-5, "0s"),  # <= 0 branch
        (7, "7s"),  # minutes == 0 branch (hits divmod, returns secs only)
        (61, "1m 1s"),  # minutes > 0 branch
    ],
)
def test_format_duration(seconds, expected):
    assert dates.format_duration(seconds) == expected
