from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from routing.services.fuel_optimizer import (
    FuelOptimizer,
)
from routing.services.geocoding import Coordinates
from routing.services.route_planner import (
    InsufficientStationCoverageError,
    LocationNotFoundError,
    RoutePlanner,
    RoutePlanningError,
)


@pytest.fixture
def planner_dependencies():
    geocoding = Mock()
    routing = Mock()
    matcher = Mock()

    geocoding.geocode.side_effect = [
        Coordinates(longitude=-74.006, latitude=40.7128),
        Coordinates(longitude=-87.6298, latitude=41.8781),
    ]

    routing.get_route.return_value = SimpleNamespace(
        distance_miles=800.0,
        duration_minutes=750.0,
        geometry={
            "type": "LineString",
            "coordinates": [
                [-74.006, 40.7128],
                [-87.6298, 41.8781],
            ],
        },
    )

    matcher.find_nearby_stations.return_value = [
        SimpleNamespace(
            station_id=1,
            name="Test Fuel Station",
            distance_along_route=400.0,
            retail_price=Decimal("3.00"),
        ),
    ]

    return geocoding, routing, matcher


def make_planner(dependencies):
    geocoding, routing, matcher = dependencies

    return RoutePlanner(
        geocoding_service=geocoding,
        routing_service=routing,
        station_matcher=matcher,
        fuel_optimizer=FuelOptimizer(),
    )


def test_route_planner_creates_valid_fuel_plan(planner_dependencies):
    planner = make_planner(planner_dependencies)

    result = planner.plan(
        start="New York, NY",
        finish="Chicago, IL",
    )

    assert result.route.distance_miles == 800.0
    assert result.fuel_plan.total_cost == Decimal("90.00")
    assert result.fuel_plan.total_gallons_purchased == Decimal(30)
    assert len(result.fuel_plan.stops) == 1
    assert result.fuel_plan.stops[0].station_id == 1


def test_route_planner_calls_routing_service_once(planner_dependencies):
    planner = make_planner(planner_dependencies)

    planner.plan("New York, NY", "Chicago, IL")

    geocoding, routing, matcher = planner_dependencies

    matcher.find_nearby_stations.assert_called_once_with(
        geometry=routing.get_route.return_value.geometry,
        route_distance_miles=800.0,
        max_distance_miles=5.0,
    )

    assert geocoding.geocode.call_count == 2
    routing.get_route.assert_called_once()
    matcher.find_nearby_stations.assert_called_once()


def test_route_planner_handles_missing_location(planner_dependencies):
    geocoding, _, _ = planner_dependencies
    geocoding.geocode.side_effect = None
    geocoding.geocode.return_value = None

    planner = make_planner(planner_dependencies)

    with pytest.raises(
        LocationNotFoundError,
        match="Could not find coordinates",
    ):
        planner.plan("Unknown Location", "Chicago, IL")


def test_route_planner_rejects_empty_location(planner_dependencies):
    planner = make_planner(planner_dependencies)

    with pytest.raises(
        RoutePlanningError,
        match="Both start and finish",
    ):
        planner.plan("", "Chicago, IL")


def test_route_planner_handles_insufficient_coverage(
    planner_dependencies,
):
    _, _, matcher = planner_dependencies

    matcher.find_nearby_stations.return_value = []

    planner = make_planner(planner_dependencies)

    with pytest.raises(InsufficientStationCoverageError):
        planner.plan("New York, NY", "Chicago, IL")
