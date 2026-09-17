from importlib import import_module


def test_package_is_importable() -> None:
    package = import_module("internet_speed_meter")

    assert package.__name__ == "internet_speed_meter"
