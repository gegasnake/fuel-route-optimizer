from decimal import Decimal

import pytest

from fuel_stations.models import FuelStation
from fuel_stations.services.station_matcher import StationMatcher


@pytest.fixture
def route_geometry():
    return {
        "type": "LineString",
        "coordinates": [
            [-75.0, 40.0],
            [-74.0, 40.0],
        ],
    }


@pytest.fixture
def create_station():
    def factory(
        name,
        longitude,
        latitude,
        status=FuelStation.GeocodingStatus.VERIFIED,
    ):
        return FuelStation.objects.create(
            opis_id=100,
            name=name,
            address="Test address",
            city="Test City",
            state="NJ",
            rack_id=1,
            retail_price=Decimal("3.25000000"),
            longitude=longitude,
            latitude=latitude,
            geocoding_status=status,
        )

    return factory


@pytest.mark.django_db
def test_finds_station_near_route(
    route_geometry,
    create_station,
):
    station = create_station("Nearby Station", -74.5, 40.01)

    results = StationMatcher().find_nearby_stations(
        route_geometry,
        route_distance_miles=100.0,
    )

    assert len(results) == 1
    assert results[0].station_id == station.id
    assert results[0].distance_along_route == pytest.approx(50.0, abs=1.0)


@pytest.mark.django_db
def test_excludes_distant_station(
    route_geometry,
    create_station,
):
    create_station("Distant Station", -74.5, 41.0)

    results = StationMatcher().find_nearby_stations(
        route_geometry,
        route_distance_miles=100.0,
    )

    assert results == []


@pytest.mark.django_db
def test_excludes_unverified_station(
    route_geometry,
    create_station,
):
    create_station(
        "Unverified Station",
        -74.5,
        40.01,
        FuelStation.GeocodingStatus.REVIEW,
    )

    results = StationMatcher().find_nearby_stations(
        route_geometry,
        route_distance_miles=100.0,
    )

    assert results == []


@pytest.mark.django_db
def test_sorts_stations_along_route(
    route_geometry,
    create_station,
):
    create_station("Later Station", -74.2, 40.0)
    create_station("Earlier Station", -74.8, 40.0)

    results = StationMatcher().find_nearby_stations(
        route_geometry,
        route_distance_miles=100.0,
    )

    assert [item.name for item in results] == [
        "Earlier Station",
        "Later Station",
    ]


def test_rejects_invalid_geometry():
    with pytest.raises(ValueError):
        StationMatcher().find_nearby_stations(
            {"type": "Point", "coordinates": [0, 0]},
            route_distance_miles=100.0,
        )
