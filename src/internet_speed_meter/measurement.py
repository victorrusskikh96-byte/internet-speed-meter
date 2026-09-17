from collections.abc import Callable, Iterator
from math import isfinite
from time import perf_counter

import httpx

from internet_speed_meter.calculation import REQUEST_COUNT, RequestMeasurement

Timer = Callable[[], float]


class MeasurementError(Exception):
    """Ожидаемая ошибка HTTP-измерения."""


def create_client() -> httpx.Client:
    """Создать синхронный HTTP client с настройками из спецификации."""

    return httpx.Client(
        follow_redirects=True,
        max_redirects=20,
        timeout=httpx.Timeout(30.0),
    )


def measure_requests(
    client: httpx.Client,
    url: str,
    *,
    timer: Timer = perf_counter,
) -> Iterator[RequestMeasurement]:
    """Последовательно выполнить и вернуть результаты десяти HTTP-загрузок."""

    for _ in range(REQUEST_COUNT):
        yield _measure_request(client, url, timer)


def _measure_request(client: httpx.Client, url: str, timer: Timer) -> RequestMeasurement:
    started_at = timer()

    try:
        with client.stream("GET", url) as response:
            downloaded_bytes = sum(len(chunk) for chunk in response.iter_raw())
            finished_at = timer()
            status_code = response.status_code
    except httpx.TimeoutException as error:
        raise MeasurementError("Превышено время ожидания HTTP-запроса") from error
    except httpx.RequestError as error:
        raise MeasurementError(f"Ошибка HTTP-запроса: {error}") from error

    duration_seconds = finished_at - started_at
    if not isfinite(duration_seconds) or duration_seconds <= 0:
        raise MeasurementError("Невозможно получить положительную длительность измерения")
    if 400 <= status_code <= 599:
        raise MeasurementError(f"HTTP status {status_code}")

    return RequestMeasurement(
        duration_seconds=duration_seconds,
        downloaded_bytes=downloaded_bytes,
    )
