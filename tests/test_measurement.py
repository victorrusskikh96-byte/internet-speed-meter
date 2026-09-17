from collections.abc import Iterator
from typing import NoReturn

import httpx
import pytest

from internet_speed_meter.measurement import (
    MeasurementError,
    create_client,
    measure_requests,
)


class RecordingStream(httpx.SyncByteStream):
    def __init__(self, chunks: tuple[bytes, ...], events: list[str], name: str) -> None:
        self._chunks = chunks
        self._events = events
        self._name = name

    def __iter__(self) -> Iterator[bytes]:
        self._events.append(f"read-start:{self._name}")
        yield from self._chunks
        self._events.append(f"read-finish:{self._name}")


class BrokenStream(httpx.SyncByteStream):
    def __iter__(self) -> Iterator[bytes]:
        yield b"partial"
        raise httpx.ReadError("поток оборван")


class Timer:
    def __init__(self, values: list[float]) -> None:
        self._values = iter(values)

    def __call__(self) -> float:
        return next(self._values)


def test_measure_requests_performs_ten_sequential_gets_and_counts_raw_chunks() -> None:
    events: list[str] = []
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        if request_count:
            assert events[-1] == f"read-finish:response-{request_count}"
        request_count += 1
        events.append(f"request:{request_count}")
        assert request.method == "GET"
        assert request.content == b""
        return httpx.Response(
            200,
            headers={"Content-Length": "999999"},
            stream=RecordingStream(
                (b"abc", b"de"),
                events,
                f"response-{request_count}",
            ),
        )

    timer = Timer([float(value) for value in range(20)])
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        results = tuple(measure_requests(client, "https://example.test/file", timer=timer))

    assert request_count == 10
    assert len(results) == 10
    assert [result.duration_seconds for result in results] == [1.0] * 10
    assert [result.downloaded_bytes for result in results] == [5] * 10


def test_timer_wraps_request_and_full_body_read() -> None:
    events: list[str] = []
    timer_values = iter([10.0, 12.5])

    def timer() -> float:
        events.append("timer")
        return next(timer_values)

    def handler(request: httpx.Request) -> httpx.Response:
        assert events == ["timer"]
        events.append("request")
        return httpx.Response(
            200,
            stream=RecordingStream((b"one", b"two"), events, "body"),
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        results = measure_requests(client, "https://example.test/file", timer=timer)
        result = next(results)

    assert result.duration_seconds == 2.5
    assert events == [
        "timer",
        "request",
        "read-start:body",
        "read-finish:body",
        "timer",
    ]


def test_measure_requests_counts_encoded_bytes_before_decoding() -> None:
    encoded_body = b"\x1f\x8braw-transfer-bytes"
    events: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Encoding": "gzip"},
            stream=RecordingStream((encoded_body,), events, "encoded"),
            request=request,
        )

    timer = Timer([float(value) for value in range(20)])
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        results = tuple(measure_requests(client, "https://example.test/file", timer=timer))

    assert {result.downloaded_bytes for result in results} == {len(encoded_body)}


def test_measure_requests_accepts_empty_body() -> None:
    timer = Timer([float(value) for value in range(20)])
    events: list[str] = []
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            204,
            stream=RecordingStream((), events, "empty"),
            request=request,
        )
    )

    with httpx.Client(transport=transport) as client:
        results = tuple(measure_requests(client, "https://example.test/empty", timer=timer))

    assert len(results) == 10
    assert all(result.downloaded_bytes == 0 for result in results)


def test_redirect_bodies_are_consumed_before_next_exchange_and_not_counted() -> None:
    events: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        events.append(f"request:{path}")
        if path == "/start":
            return httpx.Response(
                302,
                headers={"Location": "/middle"},
                stream=RecordingStream((b"redirect-one",), events, "start"),
            )
        if path == "/middle":
            assert events[-2:] == ["read-finish:start", "request:/middle"]
            return httpx.Response(
                307,
                headers={"Location": "/final"},
                stream=RecordingStream((b"redirect-two",), events, "middle"),
            )
        assert path == "/final"
        assert events[-2:] == ["read-finish:middle", "request:/final"]
        return httpx.Response(
            200,
            stream=RecordingStream((b"final", b"-body"), events, "final"),
        )

    timer = Timer([float(value) for value in range(20)])
    with httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    ) as client:
        results = tuple(measure_requests(client, "https://example.test/start", timer=timer))

    assert len(results) == 10
    assert all(result.downloaded_bytes == len(b"final-body") for result in results)
    assert events.count("read-finish:start") == 10
    assert events.count("read-finish:middle") == 10
    assert events.count("read-finish:final") == 10


def test_http_error_is_reported_only_after_body_is_consumed() -> None:
    events: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            stream=RecordingStream((b"error", b" body"), events, "error"),
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        results = measure_requests(
            client,
            "https://example.test/failure",
            timer=Timer([2.0, 3.0]),
        )
        with pytest.raises(MeasurementError, match="HTTP status 503"):
            next(results)

    assert "read-finish:error" in events


@pytest.mark.parametrize("finished_at", [5.0, 4.0])
def test_non_positive_duration_is_rejected_after_full_body(finished_at: float) -> None:
    events: list[str] = []
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            stream=RecordingStream((b"body",), events, "body"),
            request=request,
        )
    )

    with httpx.Client(transport=transport) as client:
        results = measure_requests(
            client,
            "https://example.test/file",
            timer=Timer([5.0, finished_at]),
        )
        with pytest.raises(MeasurementError, match="положительную длительность"):
            next(results)

    assert "read-finish:body" in events


@pytest.mark.parametrize(
    ("exception", "message"),
    [
        (httpx.ReadTimeout("таймаут"), "Превышено время ожидания"),
        (httpx.ConnectError("нет соединения"), "Ошибка HTTP-запроса"),
    ],
)
def test_request_errors_are_converted(
    exception: httpx.RequestError,
    message: str,
) -> None:
    def handler(request: httpx.Request) -> NoReturn:
        exception.request = request
        raise exception

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        results = measure_requests(
            client,
            "https://example.test/file",
            timer=Timer([1.0]),
        )
        with pytest.raises(MeasurementError, match=message):
            next(results)


def test_broken_response_stream_is_converted_to_measurement_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, stream=BrokenStream(), request=request)
    )

    with httpx.Client(transport=transport) as client:
        results = measure_requests(
            client,
            "https://example.test/file",
            timer=Timer([1.0]),
        )
        with pytest.raises(MeasurementError, match="Ошибка HTTP-запроса"):
            next(results)


@pytest.mark.parametrize("location", ["ftp://example.test/file", "/loop"])
def test_invalid_redirect_is_converted_to_measurement_error(location: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": location}, request=request)

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
        max_redirects=20,
    ) as client:
        results = measure_requests(
            client,
            "https://example.test/loop",
            timer=Timer([1.0]),
        )
        with pytest.raises(MeasurementError, match="Ошибка HTTP-запроса"):
            next(results)


def test_create_client_uses_required_http_settings() -> None:
    client = create_client()

    try:
        assert client.follow_redirects is True
        assert client.max_redirects == 20
        assert client.timeout.connect == 30.0
        assert client.timeout.read == 30.0
        assert client.timeout.write == 30.0
        assert client.timeout.pool == 30.0
    finally:
        client.close()
