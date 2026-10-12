from django.core.management.base import BaseCommand, CommandError

from fuel_stations.models import FuelStation, GeocodingCache
from routing.services.client import RoutingProviderError
from routing.services.geocoding import Coordinates, GeocodingService


class Command(BaseCommand):
    help = "Geocode pending fuel stations in small batches."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Maximum number of pending stations to process (1-100).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview stations without API requests or database changes.",
        )
        parser.add_argument(
            "--states",
            nargs="+",
            type=str,
            help="Only geocode stations from specified US states.",
        )
        parser.add_argument(
            "--ids",
            nargs="+",
            type=int,
            help="Geocode specific fuel station database IDs.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        dry_run = options["dry_run"]

        if not 1 <= limit <= 100:
            raise CommandError("--limit must be between 1 and 100.")

        # 1. Select pending stations.
        queryset = FuelStation.objects.filter(
            geocoding_status=FuelStation.GeocodingStatus.PENDING,
        )

        # 2. Optionally filter by US states.
        states = options.get("states")

        if states:
            normalized_states = [state.strip().upper() for state in states]
            queryset = queryset.filter(state__in=normalized_states)

        # 3. Optionally filter by specific station IDs.
        station_ids = options.get("ids")

        if station_ids:
            queryset = queryset.filter(id__in=station_ids)

        # 4. Apply ordering and limit AFTER all filters.
        stations = list(queryset.order_by("id")[:limit])

        if not stations:
            self.stdout.write("No pending stations found.")
            return

        geocoder = None if dry_run else GeocodingService()

        reviewed = 0
        failed = 0
        cache_hits = 0
        api_requests = 0
        retry_later = 0

        # 5. Process selected stations.
        for station in stations:
            address = (
                f"{station.name}, {station.address}, "
                f"{station.city}, {station.state}, USA"
            )

            # Normalize capitalization and whitespace for caching.
            cache_key = " ".join(address.casefold().split())

            if dry_run:
                self.stdout.write(f"[DRY RUN] {station.id}: {address}")
                continue

            try:
                # 6. Check the persistent geocoding cache.
                cached = GeocodingCache.objects.filter(
                    query=cache_key,
                ).first()

                if cached is not None:
                    coordinates = Coordinates(
                        longitude=cached.longitude,
                        latitude=cached.latitude,
                    )
                    cache_hits += 1

                    self.stdout.write(f"[CACHE HIT] Station {station.id}")

                else:
                    # 7. Call the geocoding provider on cache misses.
                    coordinates = geocoder.geocode(address)
                    api_requests += 1

                    if coordinates is None:
                        raise RoutingProviderError("Geocoding returned no coordinates.")

                    # 8. Save coordinates in PostgreSQL cache.
                    GeocodingCache.objects.get_or_create(
                        query=cache_key,
                        defaults={
                            "latitude": coordinates.latitude,
                            "longitude": coordinates.longitude,
                        },
                    )

            except RoutingProviderError as exc:
                message = str(exc)

                # Stop on quota or authorization failures.
                if "HTTP 429" in message or "HTTP 403" in message:
                    raise CommandError(
                        f"Geocoding quota or access error: {message}"
                    ) from exc

                # Retry temporary provider/network failures later.
                if "request failed" in message.lower() or "HTTP 5" in message:
                    retry_later += 1
                    self.stderr.write(f"[RETRY LATER] {station.id}: {message}")
                    continue

                # Mark permanent geocoding failures.
                station.geocoding_status = FuelStation.GeocodingStatus.FAILED
                station.save(update_fields=["geocoding_status"])

                failed += 1

                self.stderr.write(f"[FAILED] {station.id}: {message}")
                continue

            # 9. Store coordinates for manual verification.
            station.longitude = coordinates.longitude
            station.latitude = coordinates.latitude
            station.geocoding_status = FuelStation.GeocodingStatus.REVIEW

            station.save(
                update_fields=[
                    "longitude",
                    "latitude",
                    "geocoding_status",
                ]
            )

            reviewed += 1

            self.stdout.write(
                f"[REVIEW] {station.id}: {station.latitude}, {station.longitude}"
            )

        # 10. Display processing summary.
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Previewed {len(stations)} stations.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Selected: {len(stations)} | "
                    f"Geocoded: {reviewed} | "
                    f"Failed: {failed} | "
                    f"Retry later: {retry_later} | "
                    f"Cache hits: {cache_hits} | "
                    f"API requests: {api_requests}"
                )
            )
