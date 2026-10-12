from decimal import Decimal

import pytest

from routing.services.fuel_optimizer import (
    FuelOptimizationError,
    FuelOptimizer,
    FuelStationCandidate,
)


def station(
    station_id: int,
    miles: str,
    price: str,
) -> FuelStationCandidate:
    return FuelStationCandidate(
        station_id=station_id,
        name=f"Station {station_id}",
        distance_along_route=Decimal(miles),
        retail_price=Decimal(price),
    )


def test_short_route_needs_no_fuel_stop():
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(100),
        stations=[],
    )

    assert plan.total_cost == Decimal("0.00")
    assert plan.total_gallons_purchased == 0
    assert plan.stops == ()


def test_route_at_maximum_range_needs_no_stop():
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(500),
        stations=[],
    )

    assert plan.total_cost == Decimal("0.00")
    assert plan.fuel_remaining_gallons == 0


def test_long_route_with_no_stations_is_unreachable():
    with pytest.raises(
        FuelOptimizationError,
        match="Destination cannot be reached",
    ):
        FuelOptimizer().optimize(
            distance_miles=Decimal(600),
            stations=[],
        )


def test_single_fuel_stop():
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(700),
        stations=[
            station(1, "400", "3.00"),
        ],
    )

    assert len(plan.stops) == 1
    assert plan.stops[0].station_id == 1
    assert plan.stops[0].gallons_purchased == Decimal(20)
    assert plan.total_cost == Decimal("60.00")


def test_prefers_cheaper_station():
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(900),
        stations=[
            station(1, "300", "4.00"),
            station(2, "450", "2.00"),
            station(3, "700", "5.00"),
        ],
    )

    assert plan.stops
    assert all(stop.station_id != 1 for stop in plan.stops)
    assert any(stop.station_id == 2 for stop in plan.stops)


def test_multiple_fuel_stops():
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(1200),
        stations=[
            station(1, "400", "3.00"),
            station(2, "800", "2.50"),
        ],
    )

    assert [stop.station_id for stop in plan.stops] == [1, 2]
    assert plan.total_gallons_purchased == Decimal(70)
    assert plan.total_cost == Decimal("190.00")


def test_unreachable_first_station():
    with pytest.raises(
        FuelOptimizationError,
        match="unreachable",
    ):
        FuelOptimizer().optimize(
            distance_miles=Decimal(1000),
            stations=[
                station(1, "600", "2.00"),
            ],
        )


def test_stations_can_be_unsorted():
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(900),
        stations=[
            station(2, "700", "2.50"),
            station(1, "400", "3.00"),
        ],
    )

    assert plan.stops
    assert plan.stops[0].distance_along_route <= (plan.stops[-1].distance_along_route)


def test_rejects_negative_price():
    with pytest.raises(
        FuelOptimizationError,
        match="Invalid fuel price",
    ):
        FuelOptimizer().optimize(
            distance_miles=Decimal(700),
            stations=[station(1, "400", "-1")],
        )


def test_rejects_station_outside_route():
    with pytest.raises(
        FuelOptimizationError,
        match="outside the route",
    ):
        FuelOptimizer().optimize(
            distance_miles=Decimal(400),
            stations=[station(1, "500", "3.00")],
        )


def test_does_not_purchase_unnecessary_fuel():
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(600),
        stations=[
            station(1, "450", "3.00"),
        ],
    )

    assert plan.stops[0].gallons_purchased == Decimal(10)
    assert plan.total_cost == Decimal("30.00")
    assert plan.fuel_remaining_gallons == 0


def test_same_position_prefers_cheapest_station():
    """At the same mile, refuel at the cheapest available station."""
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(700),
        stations=[
            station(1, "400", "4.00"),
            station(2, "400", "2.50"),
        ],
    )

    assert len(plan.stops) == 1
    assert plan.stops[0].station_id == 2
    assert plan.stops[0].gallons_purchased == Decimal(20)
    assert plan.total_cost == Decimal("50.00")


def test_equal_prices_should_not_affect_total_cost():
    """Equal-priced stations should produce the same minimum cost."""
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(900),
        stations=[
            station(1, "400", "3.00"),
            station(2, "600", "3.00"),
        ],
    )

    assert plan.total_gallons_purchased == Decimal(40)
    assert plan.total_cost == Decimal("120.00")


def test_station_at_exact_maximum_range():
    """A station exactly 500 miles away must be reachable."""
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(1000),
        stations=[
            station(1, "500", "3.00"),
        ],
    )

    assert len(plan.stops) == 1
    assert plan.stops[0].gallons_purchased == Decimal(50)
    assert plan.total_cost == Decimal("150.00")


def test_station_beyond_maximum_range_is_unreachable():
    """A station at mile 501 cannot be reached on a full tank."""
    with pytest.raises(
        FuelOptimizationError,
        match="unreachable",
    ):
        FuelOptimizer().optimize(
            distance_miles=Decimal(1000),
            stations=[
                station(1, "501", "2.00"),
            ],
        )


def test_chooses_cheaper_station_when_reachable():
    """Avoid expensive fuel when cheaper fuel is reachable."""
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(1000),
        stations=[
            station(1, "300", "4.50"),
            station(2, "450", "2.50"),
            station(3, "750", "3.50"),
        ],
    )

    assert all(stop.station_id != 1 for stop in plan.stops)

    assert plan.stops[0].station_id == 2
    assert plan.stops[0].gallons_purchased == Decimal(45)
    assert plan.total_cost == Decimal("130.00")
    assert [stop.station_id for stop in plan.stops] == [2, 3]
    assert plan.stops[0].gallons_purchased == Decimal(45)
    assert plan.stops[1].gallons_purchased == Decimal(5)
    assert plan.total_gallons_purchased == Decimal(50)
    assert plan.fuel_remaining_gallons == Decimal(0)


def test_no_unnecessary_purchase_near_destination():
    """Buy only the fuel needed for the final segment."""
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(550),
        stations=[
            station(1, "490", "4.00"),
        ],
    )

    assert plan.stops[0].gallons_purchased == Decimal(5)
    assert plan.total_cost == Decimal("20.00")
    assert plan.fuel_remaining_gallons == Decimal(0)


def test_zero_distance_route():
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(0),
        stations=[],
    )

    assert plan.stops == ()
    assert plan.total_cost == Decimal("0.00")
    assert plan.total_gallons_purchased == Decimal(0)


@pytest.mark.parametrize(
    "distance",
    [
        Decimal(-10),
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_invalid_route_distance(distance):
    with pytest.raises(FuelOptimizationError):
        FuelOptimizer().optimize(
            distance_miles=distance,
            stations=[],
        )


@pytest.mark.parametrize(
    "price",
    [
        "0",
        "-2",
        "NaN",
        "Infinity",
    ],
)
def test_invalid_fuel_prices(price):
    with pytest.raises(FuelOptimizationError):
        FuelOptimizer().optimize(
            distance_miles=Decimal(700),
            stations=[
                station(1, "400", price),
            ],
        )


def test_custom_vehicle_configuration():
    """The optimizer should support configurable vehicle parameters."""
    optimizer = FuelOptimizer(
        max_range_miles=Decimal(300),
        miles_per_gallon=Decimal(15),
    )

    plan = optimizer.optimize(
        distance_miles=Decimal(450),
        stations=[
            station(1, "250", "3.00"),
        ],
    )

    assert optimizer.tank_capacity == Decimal(20)
    assert plan.total_gallons_purchased == Decimal(10)
    assert plan.total_cost == Decimal("30.00")


def test_same_position_three_stations_selects_cheapest():
    plan = FuelOptimizer().optimize(
        distance_miles=Decimal(800),
        stations=[
            station(1, "400", "4.00"),
            station(2, "400", "3.50"),
            station(3, "400", "2.00"),
        ],
    )

    assert len(plan.stops) == 1
    assert plan.stops[0].station_id == 3
    assert plan.stops[0].gallons_purchased == Decimal(30)
    assert plan.total_cost == Decimal("60.00")
