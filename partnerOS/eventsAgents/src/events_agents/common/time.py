from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

DEFAULT_TZ = ZoneInfo("Asia/Kolkata")


def parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def start_of_day(day_local: str, tz: ZoneInfo = DEFAULT_TZ) -> datetime:
    d = date.fromisoformat(day_local)
    return datetime.combine(d, time.min, tzinfo=tz)


def end_of_day(day_local: str, tz: ZoneInfo = DEFAULT_TZ) -> datetime:
    return start_of_day(day_local, tz) + timedelta(days=1)


def last_complete_week_start(today: datetime | None = None, tz: ZoneInfo = DEFAULT_TZ) -> date:
    now = today.astimezone(tz) if today else datetime.now(tz)
    current_monday = (now.date() - timedelta(days=now.weekday()))
    return current_monday - timedelta(days=7)


def resolve_week_start(spec: str, tz: ZoneInfo = DEFAULT_TZ) -> date:
    if spec == "last-complete":
        return last_complete_week_start(tz=tz)
    return date.fromisoformat(spec)


def week_dates(week_start: str | date) -> list[date]:
    start = date.fromisoformat(week_start) if isinstance(week_start, str) else week_start
    return [start + timedelta(days=index) for index in range(7)]


def format_minutes(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes:02d}m"
