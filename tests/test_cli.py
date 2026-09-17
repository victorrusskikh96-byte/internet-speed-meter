from collections.abc import Iterator
from typing import Any

import pytest

from internet_speed_meter import cli
from internet_speed_meter.calculation import RequestMeasurement
from internet_speed_meter.measurement import MeasurementError


class FakeClient:
    def __init__(self) -> None:
        self.entered = False
        self.closed = False

    def __enter__(self) -> "FakeClient":
        self.entered = True
        return self

    def __exit__(self, *args: Any) -> None:
        self.closed = True


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("HTTP://example.test/file#part", "http://example.test/file"),
        ("https://example.test:8443/file?q=1#part", "https://example.test:8443/file?q=1"),
    ],
)
def test_validate_url_accepts_http_and_https_without_scheme_case_sensitivity(
    value: str,
    expected: str,
) -> None:
    assert cli.validate_url(value) == expected


def test_successful_cli_prints_progress_and_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client = FakeClient()
    received: list[tuple[FakeClient, str]] = []
    measurements = tuple(
        RequestMeasurement(duration_seconds=index / 10, downloaded_bytes=index * 100_000)
        for index in range(1, 11)
    )

    def fake_measure_requests(fake_client: FakeClient, url: str) -> Iterator[RequestMeasurement]:
        received.append((fake_client, url))
        yield from measurements

    monkeypatch.setattr(cli, "create_client", lambda: client)
    monkeypatch.setattr(cli, "measure_requests", fake_measure_requests)

    exit_code = cli.main(["HTTPS://example.test/file#section"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert received == [(client, "https://example.test/file")]
    assert client.entered is True
    assert client.closed is True
    assert captured.err == ""
    lines = captured.out.splitlines()
    assert lines[:2] == [
        "Запрос 1/10: 0.100 с, 100000 байт",
        "Запрос 2/10: 0.200 с, 200000 байт",
    ]
    assert lines[9] == "Запрос 10/10: 1.000 с, 1000000 байт"
    assert lines[10:] == [
        "",
        "Итоги:",
        "Запросов: 10",
        "Среднее время запроса: 0.550 с",
        "Скачано: 5500000 байт (5.500 MB)",
        "Средняя скорость: 1.000 MB/s (8.000 Mbps)",
    ]


@pytest.mark.parametrize("help_option", ["-h", "--help"])
def test_help_is_in_russian_and_does_not_create_client(
    help_option: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "create_client",
        lambda: pytest.fail("HTTP client не должен создаваться"),
    )

    with pytest.raises(SystemExit) as error:
        cli.main([help_option])

    captured = capsys.readouterr()
    assert error.value.code == 0
    assert captured.err == ""
    assert "Использование:" in captured.out
    assert "Позиционные аргументы:" in captured.out
    assert "Параметры:" in captured.out
    assert "измеряемого ресурса" in captured.out
    assert "показать эту справку" in captured.out
    assert "usage:" not in captured.out
    assert "positional arguments:" not in captured.out
    assert "options:" not in captured.out
    assert "show this help" not in captured.out


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["https://example.test", "https://extra.test"],
        ["relative/path"],
        ["ftp://example.test/file"],
        ["https:///without-host"],
        ["https://example.test:invalid/file"],
        ["https://[broken/file"],
    ],
)
def test_invalid_arguments_are_rejected_before_client_creation(
    arguments: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "create_client",
        lambda: pytest.fail("HTTP client не должен создаваться"),
    )

    with pytest.raises(SystemExit) as error:
        cli.main(arguments)

    captured = capsys.readouterr()
    assert error.value.code == 2
    assert captured.out == ""
    assert "Использование:" in captured.err
    assert "требуется один абсолютный HTTP/HTTPS URL" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    ("message", "expected_text"),
    [
        ("HTTP status 503", "HTTP status 503"),
        ("Превышено время ожидания HTTP-запроса", "Превышено время ожидания"),
        ("Ошибка HTTP-запроса: соединение отклонено", "соединение отклонено"),
        (
            "Невозможно получить положительную длительность измерения",
            "положительную длительность",
        ),
    ],
)
def test_expected_measurement_error_is_fail_fast_without_summary(
    message: str,
    expected_text: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client = FakeClient()

    def failing_measurements(
        fake_client: FakeClient,
        url: str,
    ) -> Iterator[RequestMeasurement]:
        del fake_client, url
        yield RequestMeasurement(duration_seconds=0.125, downloaded_bytes=25)
        yield RequestMeasurement(duration_seconds=0.250, downloaded_bytes=50)
        raise MeasurementError(message)

    monkeypatch.setattr(cli, "create_client", lambda: client)
    monkeypatch.setattr(cli, "measure_requests", failing_measurements)

    exit_code = cli.main(["https://example.test/file"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert client.closed is True
    assert captured.out.splitlines() == [
        "Запрос 1/10: 0.125 с, 25 байт",
        "Запрос 2/10: 0.250 с, 50 байт",
    ]
    assert "Ошибка при выполнении запроса 3/10" in captured.err
    assert expected_text in captured.err
    assert "Итоги:" not in captured.out
    assert "Traceback" not in captured.err


def test_unexpected_error_is_not_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeClient()

    def broken_measurements(
        fake_client: FakeClient,
        url: str,
    ) -> Iterator[RequestMeasurement]:
        del fake_client, url
        raise RuntimeError("unexpected")
        yield

    monkeypatch.setattr(cli, "create_client", lambda: client)
    monkeypatch.setattr(cli, "measure_requests", broken_measurements)

    with pytest.raises(RuntimeError, match="unexpected"):
        cli.main(["https://example.test/file"])

    assert client.closed is True
