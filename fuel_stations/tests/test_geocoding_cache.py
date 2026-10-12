from unittest.mock import patch

import pytest
from django.core.management import call_command

from fuel_stations.models import FuelStation, GeocodingCache
from routing.services.geocoding import Coordinates


@pytest.fixture
def station_factory():
    def create(opis_id, name="Test Station"):
        return FuelStation.objects.create(
            opis_id=opis_id,
            name=name,
            address="123 Main Street",
            city="Dallas",
            state="TX",
            rack_id=1,
            retail_price="3.25000000",
        )

    return create


@pytest.mark.django_db
def test_geocoding_creates_persistent_cache(station_factory):
    station = station_factory(101)

    with patch(
        "fuel_stations.management.commands.geocode_fuel_stations.GeocodingService"
    ) as mock_service:
        mock_service.return_value.geocode.return_value = Coordinates(
            longitude=-96.797,
            latitude=32.7767,
        )

        call_command("geocode_fuel_stations", limit=1)

        mock_service.return_value.geocode.assert_called_once()

    station.refresh_from_db()

    assert station.geocoding_status == FuelStation.GeocodingStatus.REVIEW
    assert station.latitude == 32.7767
    assert station.longitude == -96.797
    assert GeocodingCache.objects.count() == 1


@pytest.mark.django_db
def test_identical_addresses_reuse_cache(station_factory):
    station_factory(101)
    station_factory(102)

    with patch(
        "fuel_stations.management.commands.geocode_fuel_stations.GeocodingService"
    ) as mock_service:
        mock_service.return_value.geocode.return_value = Coordinates(
            longitude=-96.797,
            latitude=32.7767,
        )

        call_command("geocode_fuel_stations", limit=1)
        call_command("geocode_fuel_stations", limit=1)

        assert mock_service.return_value.geocode.call_count == 1

    assert GeocodingCache.objects.count() == 1
    assert (
        FuelStation.objects.filter(
            geocoding_status=FuelStation.GeocodingStatus.REVIEW
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_dry_run_does_not_modify_database(station_factory):
    station = station_factory(101)

    with patch(
        "fuel_stations.management.commands.geocode_fuel_stations.GeocodingService"
    ) as mock_service:
        call_command("geocode_fuel_stations", limit=1, dry_run=True)
        mock_service.assert_not_called()

    station.refresh_from_db()

    assert station.geocoding_status == FuelStation.GeocodingStatus.PENDING
    assert station.latitude is None
    assert station.longitude is None
    assert GeocodingCache.objects.count() == 0
