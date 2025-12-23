# tests/unit/utils/test_units.py

from decimal import Decimal

import pytest

from app.utils.units import kg_to_lb, lb_to_kg


def test_kg_to_lb_zero() -> None:
    assert kg_to_lb(Decimal(0.0)) == Decimal(0.0)


def test_lb_to_kg_zero() -> None:
    assert lb_to_kg(Decimal(0.0)) == 0.0


def test_kg_to_lb_known_value() -> None:
    assert kg_to_lb(Decimal("1")) == Decimal("2.2046226218")


def test_lb_to_kg_known_value() -> None:
    # 2.2046226218 lb = 1 kg
    assert lb_to_kg(Decimal("2.2046226218")) == Decimal("1")


@pytest.mark.parametrize("kg", ["0.1", "1", "2.5", "10", "123.456"])
def test_round_trip_kg_lb_kg_is_close(kg: str) -> None:
    value = Decimal(kg)
    # Converting kg -> lb -> kg should return approximately the original value.
    assert lb_to_kg(kg_to_lb(value)) == pytest.approx(value, rel=0, abs=1e-10)


@pytest.mark.parametrize("lb", ["0.1", "1", "5", "25", "200.5"])
def test_round_trip_lb_kg_lb_is_close(lb: str) -> None:
    value = Decimal(lb)
    # Converting lb -> kg -> lb should return approximately the original value.
    assert kg_to_lb(lb_to_kg(value)) == pytest.approx(value, rel=0, abs=1e-10)
