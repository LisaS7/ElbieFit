from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# ----------- ISO -----------


def dt_to_iso(dt: datetime) -> str:
    """
    Convert a datetime to canonical DynamoDB-friendly ISO8601.
    Always returns a UTC Z-suffixed string.
    """
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def date_to_iso(d: date) -> str:
    """
    Convert a date object (YYYY-MM-DD) to ISO8601 string.
    """
    return d.isoformat()


def iso_to_dt(d: str) -> datetime:
    """
    Convert an ISO8601 string to a date object.
    """
    return datetime.fromisoformat(d.replace("Z", "+00:00"))


def now() -> datetime:
    return datetime.now(timezone.utc)


# ----------- Timezone -----------


def _safe_zoneinfo(tz_name: str | None) -> ZoneInfo:
    """
    Return a ZoneInfo for tz_name, falling back to UTC if tz_name is missing/invalid.
    """
    if not tz_name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def now_in_tz(tz_name: str | None) -> datetime:
    """
    Current moment in the user's timezone (falls back to UTC).
    """
    tz = _safe_zoneinfo(tz_name)
    return now().astimezone(tz)


def today_in_tz(tz_name: str | None) -> date:
    """
    User-local 'today' as a date (falls back to UTC).
    """
    return now_in_tz(tz_name).date()


# ----------- Formatting -----------


def format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0s"

    minutes, secs = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
