import csv
from decimal import Decimal

import pytest
from django.core.management import call_command

from fuel_stations.models import FuelStation


@pytest.fixture
def csv_file(tmp_path):
    path = tmp_path / "fuel_prices.csv"

    rows = [
        {
            "OPIS Truckstop ID": "100",
            "Truckstop Name": "Station A",
            "Address": "123 Main St",
            "City": "Dallas",
            "State": "TX",
            "Rack ID": "10",
            "Retail Price": "3.25000000",
        },
        {
            "OPIS Truckstop ID": "100",
            "Truckstop Name": "Station B",
            "Address": "456 Main St",
            "City": "Dallas",
            "State": "TX",
            "Rack ID": "11",
            "Retail Price": "3.45000000",
        },
    ]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    return path


@pytest.mark.django_db
def test_import_creates_stations(csv_file):
    call_command("import_fuel_prices", str(csv_file))

    assert FuelStation.objects.count() == 2
    assert list(
        FuelStation.objects.order_by("source_row_number").values_list(
            "source_row_number", flat=True
        )
    ) == [2, 3]


@pytest.mark.django_db
def test_reimport_does_not_duplicate_stations(csv_file):
    call_command("import_fuel_prices", str(csv_file))
    call_command("import_fuel_prices", str(csv_file))

    assert FuelStation.objects.count() == 2


@pytest.mark.django_db
def test_reimport_preserves_coordinates(csv_file):
    call_command("import_fuel_prices", str(csv_file))

    station = FuelStation.objects.get(source_row_number=2)
    station.latitude = 32.7767
    station.longitude = -96.7970
    station.geocoding_status = FuelStation.GeocodingStatus.VERIFIED
    station.save()

    call_command("import_fuel_prices", str(csv_file))

    station.refresh_from_db()

    assert station.latitude == 32.7767
    assert station.longitude == -96.7970
    assert station.geocoding_status == (FuelStation.GeocodingStatus.VERIFIED)


@pytest.mark.django_db
def test_reimport_updates_price(csv_file):
    call_command("import_fuel_prices", str(csv_file))

    contents = csv_file.read_text()
    csv_file.write_text(contents.replace("3.25000000", "3.99000000"))

    call_command("import_fuel_prices", str(csv_file))

    station = FuelStation.objects.get(source_row_number=2)

    assert station.retail_price == Decimal("3.99000000")


@pytest.mark.django_db
def test_duplicate_opis_ids_are_preserved(csv_file):
    call_command("import_fuel_prices", str(csv_file))

    stations = FuelStation.objects.filter(opis_id=100)

    assert stations.count() == 2
    assert set(stations.values_list("name", flat=True)) == {
        "Station A",
        "Station B",
    }


@pytest.mark.django_db
def test_reimport_rejects_changed_station_identity(csv_file):
    from django.core.management.base import CommandError

    call_command("import_fuel_prices", str(csv_file))

    station = FuelStation.objects.get(source_row_number=2)
    station.latitude = 32.7767
    station.longitude = -96.7970
    station.save(update_fields=["latitude", "longitude"])

    original = csv_file.read_text()
    csv_file.write_text(original.replace("Station A", "Different Station"))

    with pytest.raises(CommandError, match="Station identity changed"):
        call_command("import_fuel_prices", str(csv_file))

    station.refresh_from_db()

    assert station.name == "Station A"
    assert station.latitude == 32.7767
    assert station.longitude == -96.7970
