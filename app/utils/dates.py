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
    DynamoDB and JSON both expect strings, not date objects.
    """
    return d.isoformat()


def now() -> datetime:
    return datetime.now(timezone.utc)
