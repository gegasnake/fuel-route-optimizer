from dataclasses import dataclass
from itertools import pairwise
from math import asin, cos, radians, sin, sqrt

from fuel_stations.models import FuelStation

EARTH_RADIUS_MILES = 3958.7613
MILES_PER_LATITUDE_DEGREE = 69.0


@dataclass(frozen=True, slots=True)
class StationMatch:
    station_id: int
    name: str
    retail_price: float
    distance_along_route: float
    distance_from_route: float
    latitude: float
    longitude: float


def haversine(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Return great-circle distance in miles."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )

    return 2 * EARTH_RADIUS_MILES * asin(min(1.0, sqrt(a)))


def nearest_point_on_segment(
    point: tuple[float, float],
    start: tuple[float, float],
    finish: tuple[float, float],
) -> tuple[float, float]:
    """
    Return (distance in miles, position along segment).

    Coordinates are (longitude, latitude).
    Position is between 0 and 1.
    """
    reference_lat = radians((point[1] + start[1] + finish[1]) / 3)

    scale_x = MILES_PER_LATITUDE_DEGREE * cos(reference_lat)
    scale_y = MILES_PER_LATITUDE_DEGREE

    ax = (start[0] - point[0]) * scale_x
    ay = (start[1] - point[1]) * scale_y

    bx = (finish[0] - point[0]) * scale_x
    by = (finish[1] - point[1]) * scale_y

    dx = bx - ax
    dy = by - ay

    length_squared = dx * dx + dy * dy

    if length_squared == 0:
        return sqrt(ax * ax + ay * ay), 0.0

    t = max(
        0.0,
        min(1.0, -(ax * dx + ay * dy) / length_squared),
    )

    nearest_x = ax + t * dx
    nearest_y = ay + t * dy

    return sqrt(nearest_x**2 + nearest_y**2), t


class StationMatcher:
    def find_nearby_stations(
        self,
        geometry: dict,
        route_distance_miles: float,
        max_distance_miles: float = 5.0,
    ) -> list[StationMatch]:
        if route_distance_miles <= 0:
            raise ValueError("Route distance must be positive.")

        if max_distance_miles <= 0:
            raise ValueError("Maximum distance must be positive.")

        if geometry.get("type") != "LineString":
            raise ValueError("Expected LineString geometry.")

        points = geometry.get("coordinates", [])

        if len(points) < 2:
            raise ValueError("Route requires at least two points.")

        # Route coordinates use [longitude, latitude].
        longitudes = [p[0] for p in points]
        latitudes = [p[1] for p in points]

        # Conservative database bounding-box filter.
        latitude_padding = max_distance_miles / 69.0
        longitude_padding = max_distance_miles / 35.0

        stations = FuelStation.objects.filter(
            geocoding_status=FuelStation.GeocodingStatus.VERIFIED,
            latitude__isnull=False,
            longitude__isnull=False,
            latitude__gte=min(latitudes) - latitude_padding,
            latitude__lte=max(latitudes) + latitude_padding,
            longitude__gte=min(longitudes) - longitude_padding,
            longitude__lte=max(longitudes) + longitude_padding,
        )

        # Compute cumulative geometry distances.
        cumulative = [0.0]

        for start, finish in pairwise(points):
            segment_length = haversine(
                start[1],
                start[0],
                finish[1],
                finish[0],
            )
            cumulative.append(cumulative[-1] + segment_length)

        total_geometry_distance = cumulative[-1]

        if total_geometry_distance == 0:
            raise ValueError("Route geometry has zero length.")

        matches = []

        for station in stations:
            point = (station.longitude, station.latitude)

            best_distance = float("inf")
            best_position = 0.0

            for index, (start, finish) in enumerate(pairwise(points)):
                distance, fraction = nearest_point_on_segment(point, start, finish)

                if distance < best_distance:
                    best_distance = distance

                    segment_length = cumulative[index + 1] - cumulative[index]

                    best_position = cumulative[index] + fraction * segment_length

            if best_distance > max_distance_miles:
                continue

            route_position = (
                best_position / total_geometry_distance * route_distance_miles
            )

            matches.append(
                StationMatch(
                    station_id=station.id,
                    name=station.name,
                    retail_price=float(station.retail_price),
                    distance_along_route=round(route_position, 2),
                    distance_from_route=round(best_distance, 2),
                    latitude=station.latitude,
                    longitude=station.longitude,
                )
            )

        return sorted(
            matches,
            key=lambda item: item.distance_along_route,
        )
