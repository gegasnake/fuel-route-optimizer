import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from fuel_stations.models import FuelStation


def station_identity(station: FuelStation) -> tuple:
    """Return fields that uniquely describe a source station record."""
    return (
        station.opis_id,
        station.name,
        station.address,
        station.city,
        station.state,
        station.rack_id,
    )


class Command(BaseCommand):
    help = "Import fuel prices while preserving existing station coordinates."

    REQUIRED_COLUMNS = frozenset(
        {
            "OPIS Truckstop ID",
            "Truckstop Name",
            "Address",
            "City",
            "State",
            "Rack ID",
            "Retail Price",
        }
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=Path,
            help="Path to the fuel prices CSV.",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]

        if not csv_path.is_file():
            raise CommandError(f"File not found: {csv_path}")

        stations = []

        try:
            with csv_path.open(
                encoding="utf-8-sig",
                newline="",
            ) as file:
                reader = csv.DictReader(file)

                missing = self.REQUIRED_COLUMNS - set(reader.fieldnames or [])

                if missing:
                    raise CommandError(f"Missing CSV columns: {sorted(missing)}")

                for line_number, row in enumerate(reader, start=2):
                    try:
                        station = FuelStation(
                            source_row_number=line_number,
                            opis_id=int(row["OPIS Truckstop ID"]),
                            name=row["Truckstop Name"].strip(),
                            address=row["Address"].strip(),
                            city=row["City"].strip(),
                            state=row["State"].strip().upper(),
                            rack_id=int(row["Rack ID"]),
                            retail_price=Decimal(row["Retail Price"]),
                        )

                    except (
                        ValueError,
                        TypeError,
                        InvalidOperation,
                        AttributeError,
                        KeyError,
                    ) as exc:
                        raise CommandError(
                            f"Invalid data at CSV line {line_number}: {exc}"
                        ) from exc

                    # Important: append INSIDE the loop.
                    stations.append(station)

        except (OSError, UnicodeError, csv.Error) as exc:
            raise CommandError(f"Failed to read CSV: {exc}") from exc

        # Preserve coordinates and geocoding statuses.

        # Validate station identities before updating existing records.
        with transaction.atomic():
            existing = FuelStation.objects.filter(
                source_row_number__in=[
                    station.source_row_number for station in stations
                ]
            )

            existing_by_row = {
                station.source_row_number: station for station in existing
            }

            for station in stations:
                previous = existing_by_row.get(station.source_row_number)

                if previous is None:
                    continue

                if station_identity(previous) != station_identity(station):
                    raise CommandError(
                        "Station identity changed at CSV row "
                        f"{station.source_row_number}. "
                        "Import aborted to protect geocoded coordinates."
                    )

            FuelStation.objects.bulk_create(
                stations,
                batch_size=1000,
                update_conflicts=True,
                unique_fields=["source_row_number"],
                update_fields=[
                    "opis_id",
                    "name",
                    "address",
                    "city",
                    "state",
                    "rack_id",
                    "retail_price",
                ],
            )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed {len(stations)} fuel stations.")
        )
