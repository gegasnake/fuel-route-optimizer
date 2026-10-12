import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from fuel_stations.models import FuelStation


class Command(BaseCommand):
    help = "Import the fuel-station prices CSV into PostgreSQL."

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

                    stations.append(station)

        except (OSError, UnicodeError, csv.Error) as exc:
            raise CommandError(f"Failed to read CSV: {exc}") from exc

        # Atomic full refresh of the original source data.
        with transaction.atomic():
            FuelStation.objects.all().delete()
            FuelStation.objects.bulk_create(
                stations,
                batch_size=1000,
            )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully imported {len(stations)} fuel stations.")
        )
