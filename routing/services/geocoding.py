from dataclasses import dataclass

from routing.services.client import (
    OpenRouteServiceClient,
    RoutingProviderError,
)


@dataclass(frozen=True, slots=True)
class Coordinates:
    longitude: float
    latitude: float

    def as_list(self) -> list[float]:
        return [self.longitude, self.latitude]


class GeocodingService:
    def __init__(
        self,
        client: OpenRouteServiceClient | None = None,
    ) -> None:
        self.client = client or OpenRouteServiceClient()

    def geocode(self, location: str) -> Coordinates:
        if not location.strip():
            raise ValueError("Location cannot be empty.")

        data = self.client.request(
            "GET",
            "/geocode/search",
            params={
                "api_key": self.client.api_key,
                "text": location.strip(),
                "boundary.country": "USA",
                "size": 1,
            },
        )

        features = data.get("features") or []

        if not features:
            raise RoutingProviderError(f"No location found for: {location}")

        feature = features[0]
        properties = feature.get("properties", {})

        if properties.get("country_a") != "USA":
            raise RoutingProviderError("The location must be inside the USA.")

        coordinates = feature["geometry"]["coordinates"]

        try:
            longitude, latitude = map(float, coordinates[:2])
        except (TypeError, ValueError, IndexError) as exc:
            raise RoutingProviderError(
                "Invalid coordinates returned by geocoder."
            ) from exc

        if not (-180 <= longitude <= 180):
            raise RoutingProviderError("Invalid longitude.")

        if not (-90 <= latitude <= 90):
            raise RoutingProviderError("Invalid latitude.")

        return Coordinates(
            longitude=longitude,
            latitude=latitude,
        )
