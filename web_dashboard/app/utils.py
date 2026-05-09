from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def format_datetime_for_timezone(dt: datetime | None, timezone_name: str | None = None) -> str:
    if not dt:
        return "-"

    source_dt = dt
    if source_dt.tzinfo is None:
        source_dt = source_dt.replace(tzinfo=timezone.utc)

    try:
        target_timezone = ZoneInfo(timezone_name or "UTC")
    except ZoneInfoNotFoundError:
        target_timezone = timezone.utc

    return source_dt.astimezone(target_timezone).strftime("%Y-%m-%d %H:%M")
