from unittest.mock import Mock

import pytest

from routing.services.client import RoutingProviderError
from routing.services.geocoding import Coordinates
from routing.services.routing import RoutingService


@pytest.fixture
def client():
    return Mock()


@pytest.fixture
def service(client):
    return RoutingService(client=client)


@pytest.fixture
def valid_response():
    return {
        "features": [
            {
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-73.9708, 40.68295],
                        [-75.168428, 39.990821],
                    ],
                },
                "properties": {
                    "summary": {
                        "distance": 160934.4,
                        "duration": 7200,
                    }
                },
            }
        ]
    }


@pytest.fixture
def locations():
    return (
        Coordinates(-73.9708, 40.68295),
        Coordinates(-75.168428, 39.990821),
    )


def test_get_route_success(service, client, valid_response, locations):
    client.request.return_value = valid_response

    result = service.get_route(*locations)

    assert result.distance_miles == pytest.approx(100.0)
    assert result.duration_minutes == pytest.approx(120.0)
    assert result.geometry["type"] == "LineString"

    client.request.assert_called_once_with(
        "POST",
        "/v2/directions/driving-car/geojson",
        json={
            "coordinates": [
                [-73.9708, 40.68295],
                [-75.168428, 39.990821],
            ],
            "instructions": False,
        },
    )


def test_get_route_no_results(service, client, locations):
    client.request.return_value = {"features": []}

    with pytest.raises(
        RoutingProviderError,
        match="No driving route",
    ):
        service.get_route(*locations)


@pytest.mark.parametrize(
    ("summary", "geometry", "expected"),
    [
        (
            {"distance": -100, "duration": 120},
            {
                "type": "LineString",
                "coordinates": [[0, 0], [1, 1]],
            },
            "Invalid route response",
        ),
        (
            {"distance": 100, "duration": -20},
            {
                "type": "LineString",
                "coordinates": [[0, 0], [1, 1]],
            },
            "Invalid route response",
        ),
        (
            {"distance": 100, "duration": 120},
            {
                "type": "Point",
                "coordinates": [0, 0],
            },
            "Invalid route response",
        ),
        (
            {"distance": 100, "duration": 120},
            {
                "type": "LineString",
                "coordinates": [[0, 0]],
            },
            "Invalid route response",
        ),
    ],
)
def test_get_route_invalid_data(
    service,
    client,
    locations,
    summary,
    geometry,
    expected,
):
    client.request.return_value = {
        "features": [
            {
                "geometry": geometry,
                "properties": {
                    "summary": summary,
                },
            }
        ]
    }

    with pytest.raises(RoutingProviderError, match=expected):
        service.get_route(*locations)


def test_get_route_converts_meters_to_miles(
    service,
    client,
    valid_response,
    locations,
):
    valid_response["features"][0]["properties"]["summary"]["distance"] = 804672
    client.request.return_value = valid_response

    result = service.get_route(*locations)

    assert result.distance_miles == pytest.approx(500.0)


def test_get_route_returns_geometry(
    service,
    client,
    valid_response,
    locations,
):
    client.request.return_value = valid_response

    result = service.get_route(*locations)

    assert result.geometry == valid_response["features"][0]["geometry"]
