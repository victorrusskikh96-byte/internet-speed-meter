import argparse
import sys
from collections.abc import Sequence
from typing import NoReturn
from urllib.parse import urlsplit, urlunsplit

from internet_speed_meter.calculation import (
    REQUEST_COUNT,
    MeasurementSummary,
    RequestMeasurement,
    calculate_summary,
)
from internet_speed_meter.measurement import (
    MeasurementError,
    create_client,
    measure_requests,
)


class RussianArgumentParser(argparse.ArgumentParser):
    """Парсер аргументов с русскоязычными служебными сообщениями."""

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "Использование:", 1)

    def format_help(self) -> str:
        return (
            super()
            .format_help()
            .replace("usage:", "Использование:", 1)
            .replace("positional arguments:", "Позиционные аргументы:", 1)
            .replace("options:", "Параметры:", 1)
            .replace("optional arguments:", "Параметры:", 1)
        )

    def error(self, message: str) -> NoReturn:
        del message
        self.print_usage(sys.stderr)
        self.exit(2, "Ошибка: требуется один абсолютный HTTP/HTTPS URL.\n")


def create_parser() -> argparse.ArgumentParser:
    """Создать русскоязычный парсер аргументов CLI."""

    parser = RussianArgumentParser(
        prog="internet-speed-meter",
        description="Измеряет скорость последовательной загрузки HTTP-ресурса.",
        add_help=False,
    )
    parser.add_argument(
        "url",
        metavar="URL",
        help="абсолютный HTTP/HTTPS URL измеряемого ресурса",
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="показать эту справку и завершить работу",
    )
    return parser


def validate_url(value: str) -> str:
    """Проверить URL и удалить fragment, который не передаётся серверу."""

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        parsed.port
    except ValueError as error:
        raise ValueError("Некорректный URL") from error

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or hostname is None:
        raise ValueError("Некорректный URL")

    return urlunsplit((scheme, parsed.netloc, parsed.path, parsed.query, ""))


def print_progress(request_number: int, measurement: RequestMeasurement) -> None:
    """Вывести результат одной успешно завершённой загрузки."""

    print(
        f"Запрос {request_number}/{REQUEST_COUNT}: "
        f"{measurement.duration_seconds:.3f} с, "
        f"{measurement.downloaded_bytes} байт",
        flush=True,
    )


def print_summary(summary: MeasurementSummary) -> None:
    """Вывести итоговые показатели успешного замера."""

    print()
    print("Итоги:")
    print(f"Запросов: {summary.request_count}")
    print(f"Среднее время запроса: {summary.average_duration_seconds:.3f} с")
    print(f"Скачано: {summary.total_bytes} байт ({summary.total_mb:.3f} MB)")
    print(f"Средняя скорость: {summary.speed_mb_s:.3f} MB/s ({summary.speed_mbps:.3f} Mbps)")


def configure_output_encoding() -> None:
    """Настроить стабильный UTF-8 вывод для русскоязычного CLI."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """Запустить CLI и вернуть код завершения."""

    configure_output_encoding()
    parser = create_parser()
    arguments = parser.parse_args(argv)
    try:
        url = validate_url(arguments.url)
    except ValueError:
        parser.error("Некорректный URL")

    measurements: list[RequestMeasurement] = []
    try:
        with create_client() as client:
            for request_number, measurement in enumerate(
                measure_requests(client, url),
                start=1,
            ):
                measurements.append(measurement)
                print_progress(request_number, measurement)
    except MeasurementError as error:
        failed_request_number = len(measurements) + 1
        print(
            f"Ошибка при выполнении запроса {failed_request_number}/{REQUEST_COUNT}: {error}",
            file=sys.stderr,
        )
        return 1

    print_summary(calculate_summary(measurements))
    return 0
