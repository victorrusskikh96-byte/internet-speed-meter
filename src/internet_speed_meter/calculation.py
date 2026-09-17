from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite

REQUEST_COUNT = 10
BYTES_PER_MB = 1_000_000
BITS_PER_BYTE = 8


@dataclass(frozen=True, slots=True)
class RequestMeasurement:
    """Результат одной полностью завершённой HTTP-загрузки."""

    duration_seconds: float
    downloaded_bytes: int


@dataclass(frozen=True, slots=True)
class MeasurementSummary:
    """Агрегированный результат десяти HTTP-загрузок."""

    request_count: int
    total_duration_seconds: float
    average_duration_seconds: float
    total_bytes: int
    total_mb: float
    speed_mb_s: float
    speed_mbps: float


def calculate_summary(measurements: Iterable[RequestMeasurement]) -> MeasurementSummary:
    """Рассчитать итоговые показатели по десяти результатам без округления."""

    items = tuple(measurements)
    if len(items) != REQUEST_COUNT:
        raise ValueError(f"Для расчёта требуется ровно {REQUEST_COUNT} результатов")

    if any(not isfinite(item.duration_seconds) or item.duration_seconds <= 0 for item in items):
        raise ValueError("Длительность каждого запроса должна быть положительной")
    if any(item.downloaded_bytes < 0 for item in items):
        raise ValueError("Количество полученных байтов не может быть отрицательным")

    total_duration_seconds = sum(item.duration_seconds for item in items)
    total_bytes = sum(item.downloaded_bytes for item in items)
    total_mb = total_bytes / BYTES_PER_MB
    speed_mb_s = total_bytes / total_duration_seconds / BYTES_PER_MB

    return MeasurementSummary(
        request_count=REQUEST_COUNT,
        total_duration_seconds=total_duration_seconds,
        average_duration_seconds=total_duration_seconds / REQUEST_COUNT,
        total_bytes=total_bytes,
        total_mb=total_mb,
        speed_mb_s=speed_mb_s,
        speed_mbps=speed_mb_s * BITS_PER_BYTE,
    )
