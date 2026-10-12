from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APIClient

from routing.services.route_planner import (
    InsufficientStationCoverageError,
    LocationNotFoundError,
)

URL = reverse("route-optimize")


def test_rejects_missing_finish():
    client = APIClient()

    response = client.post(
        URL,
        {"start": "New York, NY"},
        format="json",
    )

    assert response.status_code == 400
    assert "finish" in response.data


@patch("routing.views.RoutePlanner")
def test_unknown_location_returns_400(mock_planner):
    mock_planner.return_value.plan.side_effect = LocationNotFoundError(
        "Could not find coordinates for: Unknown"
    )

    response = APIClient().post(
        URL,
        {"start": "Unknown", "finish": "Chicago, IL"},
        format="json",
    )

    assert response.status_code == 400


@patch("routing.views.RoutePlanner")
def test_insufficient_coverage_returns_422(mock_planner):
    mock_planner.return_value.plan.side_effect = InsufficientStationCoverageError(
        "Insufficient verified station coverage."
    )

    response = APIClient().post(
        URL,
        {"start": "New York, NY", "finish": "Chicago, IL"},
        format="json",
    )

    assert response.status_code == 422
    assert response.data["code"] == "insufficient_station_coverage"


from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from routing.services.fuel_optimizer import FuelOptimizer, FuelStationCandidate


@patch("routing.views.RoutePlanner")
def test_route_optimize_returns_successful_response(mock_planner):
    fuel_plan = FuelOptimizer().optimize(
        distance_miles=Decimal(700),
        stations=[
            FuelStationCandidate(
                station_id=1,
                name="Test Fuel Station",
                distance_along_route=Decimal(400),
                retail_price=Decimal("3.00"),
            )
        ],
    )

    mock_planner.return_value.plan.return_value = SimpleNamespace(
        start="New York, NY",
        finish="Chicago, IL",
        route=SimpleNamespace(
            distance_miles=700.0,
            duration_minutes=650.0,
            geometry={
                "type": "LineString",
                "coordinates": [
                    [-74.006, 40.7128],
                    [-87.6298, 41.8781],
                ],
            },
        ),
        fuel_plan=fuel_plan,
        matched_stations=[
            SimpleNamespace(
                station_id=1,
                latitude=41.007944,
                longitude=-76.489601,
            ),
        ],
    )

    response = APIClient().post(
        URL,
        {
            "start": "New York, NY",
            "finish": "Chicago, IL",
        },
        format="json",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["start"] == "New York, NY"
    assert data["finish"] == "Chicago, IL"
    assert data["distance_miles"] == 700.0
    assert (
        data["fuel"]["total_cost"] == 60.0 or str(data["fuel"]["total_cost"]) == "60.00"
    )
    assert len(data["fuel"]["stops"]) == 1
    assert data["fuel"]["stops"][0]["station_id"] == 1
    stop = data["fuel"]["stops"][0]

    assert stop["latitude"] == 41.007944
    assert stop["longitude"] == -76.489601

    mock_planner.return_value.plan.assert_called_once_with(
        start="New York, NY",
        finish="Chicago, IL",
    )
