from datetime import date, datetime, timezone


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


def format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0s"

    minutes, secs = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
