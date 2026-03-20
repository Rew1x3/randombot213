from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def parse_end_time_utc(value: str) -> datetime:
    """
    Парсит строку времени в UTC.
    Поддерживаем форматы:
      - YYYY-MM-DD HH:MM
      - YYYY-MM-DDTHH:MM
      - YYYY-MM-DD HH:MM:SS
      - YYYY-MM-DDTHH:MM:SS
    """
    v = value.strip()
    if not v:
        raise ValueError("Empty end time")

    # Нормализуем разделитель
    v = v.replace("T", " ")

    # Поддерживаем несколько вариантов
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(v, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise ValueError("Invalid format. Expected: YYYY-MM-DD HH:MM (UTC)")


def to_human_datetime_utc(dt: datetime) -> str:
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%d %H:%M UTC")

