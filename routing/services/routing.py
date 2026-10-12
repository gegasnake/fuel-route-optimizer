from dataclasses import dataclass
from typing import Any

from routing.services.client import (
    OpenRouteServiceClient,
    RoutingProviderError,
)
from routing.services.geocoding import Coordinates

METERS_PER_MILE = 1609.344


@dataclass(frozen=True, slots=True)
class RouteResult:
    distance_miles: float
    duration_minutes: float
    geometry: dict[str, Any]


class RoutingService:
    def __init__(
        self,
        client: OpenRouteServiceClient | None = None,
    ) -> None:
        self.client = client or OpenRouteServiceClient()

    def get_route(
        self,
        start: Coordinates,
        finish: Coordinates,
    ) -> RouteResult:
        data = self.client.request(
            "POST",
            "/v2/directions/driving-car/geojson",
            json={
                "coordinates": [
                    start.as_list(),
                    finish.as_list(),
                ],
                "instructions": False,
            },
        )

        features = data.get("features") or []

        if not features:
            raise RoutingProviderError("No driving route was returned.")

        feature = features[0]

        try:
            geometry = feature["geometry"]
            summary = feature["properties"]["summary"]

            if geometry["type"] != "LineString":
                raise ValueError("Unexpected geometry type.")

            coordinates = geometry["coordinates"]
            if len(coordinates) < 2:
                raise ValueError("Route geometry is incomplete.")

            distance_miles = float(summary["distance"]) / METERS_PER_MILE
            duration_minutes = float(summary["duration"]) / 60

            if distance_miles < 0 or duration_minutes < 0:
                raise ValueError("Invalid route measurements.")

        except (
            KeyError,
            TypeError,
            ValueError,
            IndexError,
        ) as exc:
            raise RoutingProviderError("Invalid route response from provider.") from exc

        return RouteResult(
            distance_miles=round(distance_miles, 2),
            duration_minutes=round(duration_minutes, 2),
            geometry=geometry,
        )
