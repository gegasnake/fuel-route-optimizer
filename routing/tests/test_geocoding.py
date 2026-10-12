from unittest.mock import Mock

import pytest

from routing.services.client import RoutingProviderError
from routing.services.geocoding import (
    Coordinates,
    GeocodingService,
)


@pytest.fixture
def client():
    mock = Mock()
    mock.api_key = "test-key"
    return mock


@pytest.fixture
def service(client):
    return GeocodingService(client=client)


def test_geocode_success(service, client):
    client.request.return_value = {
        "features": [
            {
                "properties": {"country_a": "USA"},
                "geometry": {
                    "coordinates": [-73.9708, 40.68295],
                },
            }
        ]
    }

    result = service.geocode("New York, NY")

    assert result == Coordinates(
        longitude=-73.9708,
        latitude=40.68295,
    )

    client.request.assert_called_once_with(
        "GET",
        "/geocode/search",
        params={
            "api_key": "test-key",
            "text": "New York, NY",
            "boundary.country": "USA",
            "size": 1,
        },
    )


@pytest.mark.parametrize("location", ["", " ", "\n", "\t"])
def test_geocode_rejects_empty_location(service, client, location):
    with pytest.raises(ValueError, match="Location cannot be empty"):
        service.geocode(location)

    client.request.assert_not_called()


def test_geocode_no_results(service, client):
    client.request.return_value = {"features": []}

    with pytest.raises(
        RoutingProviderError,
        match="No location found",
    ):
        service.geocode("Unknown Location")


def test_geocode_rejects_non_us_location(service, client):
    client.request.return_value = {
        "features": [
            {
                "properties": {"country_a": "CAN"},
                "geometry": {
                    "coordinates": [-79.3832, 43.6532],
                },
            }
        ]
    }

    with pytest.raises(
        RoutingProviderError,
        match="inside the USA",
    ):
        service.geocode("Toronto, Canada")


@pytest.mark.parametrize(
    ("coordinates", "message"),
    [
        ([-200.0, 40.0], "Invalid longitude"),
        ([-74.0, 100.0], "Invalid latitude"),
        (["invalid", 40.0], "Invalid coordinates"),
        ([], "Invalid coordinates"),
    ],
)
def test_geocode_invalid_coordinates(
    service,
    client,
    coordinates,
    message,
):
    client.request.return_value = {
        "features": [
            {
                "properties": {"country_a": "USA"},
                "geometry": {"coordinates": coordinates},
            }
        ]
    }

    with pytest.raises(RoutingProviderError, match=message):
        service.geocode("New York, NY")


def test_geocode_trims_whitespace(service, client):
    client.request.return_value = {
        "features": [
            {
                "properties": {"country_a": "USA"},
                "geometry": {
                    "coordinates": [-73.9708, 40.68295],
                },
            }
        ]
    }

    service.geocode("  New York, NY  ")

    assert client.request.call_args.kwargs["params"]["text"] == "New York, NY"


def test_coordinates_as_list():
    coordinates = Coordinates(
        longitude=-74.006,
        latitude=40.7128,
    )

    assert coordinates.as_list() == [-74.006, 40.7128]
