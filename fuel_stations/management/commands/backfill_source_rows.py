import csv
from collections import defaultdict, deque
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from fuel_stations.models import FuelStation


def station_key(values):
    """Identify a station using normalized source values."""
    return (
        int(values["opis_id"]),
        values["name"].strip(),
        values["address"].strip(),
        values["city"].strip(),
        values["state"].strip().upper(),
        int(values["rack_id"]),
        Decimal(str(values["retail_price"])),
    )


class Command(BaseCommand):
    help = "Associate existing fuel stations with original CSV rows."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=Path)
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist changes after validation.",
        )

    def handle(self, *args, **options):
        path = options["csv_path"]

        if not path.is_file():
            raise CommandError(f"File not found: {path}")

        with path.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))

        candidates = defaultdict(deque)

        for station in FuelStation.objects.order_by("id"):
            key = station_key(
                {
                    "opis_id": station.opis_id,
                    "name": station.name,
                    "address": station.address,
                    "city": station.city,
                    "state": station.state,
                    "rack_id": station.rack_id,
                    "retail_price": station.retail_price,
                }
            )
            candidates[key].append(station)

        updates = []
        unmatched_rows = []

        for row_number, row in enumerate(rows, start=2):
            key = station_key(
                {
                    "opis_id": row["OPIS Truckstop ID"],
                    "name": row["Truckstop Name"],
                    "address": row["Address"],
                    "city": row["City"],
                    "state": row["State"],
                    "rack_id": row["Rack ID"],
                    "retail_price": row["Retail Price"],
                }
            )

            if not candidates[key]:
                unmatched_rows.append(row_number)
                continue

            station = candidates[key].popleft()
            station.source_row_number = row_number
            updates.append(station)

        remaining = sum(len(group) for group in candidates.values())

        self.stdout.write(
            f"Matched: {len(updates)} | "
            f"Unmatched CSV rows: {len(unmatched_rows)} | "
            f"Unmatched DB records: {remaining}"
        )

        if unmatched_rows or remaining:
            raise CommandError("Backfill aborted: source and database do not match.")

        if not options["apply"]:
            self.stdout.write("Dry run complete. Use --apply to save changes.")
            return

        with transaction.atomic():
            FuelStation.objects.bulk_update(
                updates,
                ["source_row_number"],
                batch_size=1000,
            )

        self.stdout.write(self.style.SUCCESS(f"Backfilled {len(updates)} records."))
