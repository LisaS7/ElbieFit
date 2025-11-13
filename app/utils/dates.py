from datetime import datetime, timezone


def dt_to_iso(dt: datetime) -> str:
    """
    Convert a datetime to canonical DynamoDB-friendly ISO8601.
    Always returns a UTC Z-suffixed string.
    """
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def now() -> datetime:
    return datetime.now(timezone.utc)
