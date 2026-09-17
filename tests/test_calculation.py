from dataclasses import FrozenInstanceError

import pytest

from internet_speed_meter.calculation import (
    RequestMeasurement,
    calculate_summary,
)


def test_calculate_summary_uses_decimal_units_and_aggregate_values() -> None:
    measurements = tuple(
        RequestMeasurement(duration_seconds=float(index), downloaded_bytes=index * 100_000)
        for index in range(1, 11)
    )

    summary = calculate_summary(measurements)

    assert summary.request_count == 10
    assert summary.total_duration_seconds == 55.0
    assert summary.average_duration_seconds == 5.5
    assert summary.total_bytes == 5_500_000
    assert summary.total_mb == 5.5
    assert summary.speed_mb_s == pytest.approx(0.1)
    assert summary.speed_mbps == pytest.approx(0.8)


def test_speed_is_not_average_of_individual_request_speeds() -> None:
    measurements = (
        RequestMeasurement(duration_seconds=1.0, downloaded_bytes=10_000_000),
        *(RequestMeasurement(duration_seconds=10.0, downloaded_bytes=1_000_000) for _ in range(9)),
    )
    individual_speed_average = sum(
        item.downloaded_bytes / item.duration_seconds / 1_000_000 for item in measurements
    ) / len(measurements)

    summary = calculate_summary(measurements)

    assert summary.speed_mb_s == pytest.approx(19_000_000 / 91 / 1_000_000)
    assert summary.speed_mb_s != pytest.approx(individual_speed_average)


def test_zero_downloaded_bytes_produce_zero_volume_and_speed() -> None:
    measurements = tuple(
        RequestMeasurement(duration_seconds=0.25, downloaded_bytes=0) for _ in range(10)
    )

    summary = calculate_summary(measurements)

    assert summary.total_bytes == 0
    assert summary.total_mb == 0.0
    assert summary.speed_mb_s == 0.0
    assert summary.speed_mbps == 0.0


@pytest.mark.parametrize("request_count", [0, 9, 11])
def test_calculate_summary_requires_exactly_ten_measurements(request_count: int) -> None:
    measurements = tuple(
        RequestMeasurement(duration_seconds=1.0, downloaded_bytes=1) for _ in range(request_count)
    )

    with pytest.raises(ValueError, match="ровно 10"):
        calculate_summary(measurements)


@pytest.mark.parametrize("duration_seconds", [0.0, -0.01])
def test_calculate_summary_rejects_non_positive_duration(duration_seconds: float) -> None:
    measurements = [RequestMeasurement(duration_seconds=1.0, downloaded_bytes=1) for _ in range(10)]
    measurements[4] = RequestMeasurement(
        duration_seconds=duration_seconds,
        downloaded_bytes=1,
    )

    with pytest.raises(ValueError, match="положительной"):
        calculate_summary(measurements)


def test_calculate_summary_rejects_negative_downloaded_bytes() -> None:
    measurements = [RequestMeasurement(duration_seconds=1.0, downloaded_bytes=1) for _ in range(10)]
    measurements[4] = RequestMeasurement(duration_seconds=1.0, downloaded_bytes=-1)

    with pytest.raises(ValueError, match="отрицательным"):
        calculate_summary(measurements)


def test_models_are_immutable() -> None:
    measurement = RequestMeasurement(duration_seconds=1.0, downloaded_bytes=1)
    summary = calculate_summary((measurement,) * 10)

    with pytest.raises(FrozenInstanceError):
        measurement.downloaded_bytes = 2
    with pytest.raises(FrozenInstanceError):
        summary.total_bytes = 2
