from dataclasses import dataclass
from decimal import Decimal

from fuel_stations.services.station_matcher import (
    StationMatch,
    StationMatcher,
)
from routing.services.fuel_optimizer import (
    FuelOptimizationError,
    FuelOptimizer,
    FuelPlan,
    FuelStationCandidate,
)
from routing.services.geocoding import (
    Coordinates,
    GeocodingService,
)
from routing.services.routing import RouteResult, RoutingService


class RoutePlanningError(Exception):
    """Base exception for route planning failures."""


class LocationNotFoundError(RoutePlanningError):
    """A start or finish location could not be resolved."""


class InsufficientStationCoverageError(RoutePlanningError):
    """Available verified stations cannot support the journey."""


@dataclass(frozen=True, slots=True)
class RoutePlanResult:
    start: str
    finish: str
    start_coordinates: Coordinates
    finish_coordinates: Coordinates
    route: RouteResult
    fuel_plan: FuelPlan
    matched_stations: tuple[StationMatch, ...]


class RoutePlanner:
    def __init__(
        self,
        geocoding_service: GeocodingService | None = None,
        routing_service: RoutingService | None = None,
        station_matcher: StationMatcher | None = None,
        fuel_optimizer: FuelOptimizer | None = None,
        max_station_distance_miles: float = 5.0,
    ) -> None:
        if max_station_distance_miles <= 0:
            raise ValueError("Maximum station distance must be positive.")

        self.geocoding_service = geocoding_service or GeocodingService()
        self.routing_service = routing_service or RoutingService()
        self.station_matcher = station_matcher or StationMatcher()
        self.fuel_optimizer = fuel_optimizer or FuelOptimizer()
        self.max_station_distance_miles = max_station_distance_miles

    def _geocode(self, location: str) -> Coordinates:
        coordinates = self.geocoding_service.geocode(location)

        if coordinates is None:
            raise LocationNotFoundError(f"Could not find coordinates for: {location}")

        return coordinates

    @staticmethod
    def _route_coordinates(route: RouteResult) -> list:
        """
        Extract longitude/latitude pairs from route geometry.

        Supports GeoJSON LineString geometry or a raw coordinate list.
        """
        geometry = route.geometry

        if isinstance(geometry, dict):
            return geometry["coordinates"]

        return geometry

    @staticmethod
    def _fuel_candidates(
        matches: list[StationMatch],
    ) -> list[FuelStationCandidate]:
        return [
            FuelStationCandidate(
                station_id=match.station_id,
                name=match.name,
                distance_along_route=Decimal(str(match.distance_along_route)),
                retail_price=Decimal(str(match.retail_price)),
            )
            for match in matches
        ]

    def plan(
        self,
        start: str,
        finish: str,
    ) -> RoutePlanResult:
        start = start.strip()
        finish = finish.strip()

        if not start or not finish:
            raise RoutePlanningError("Both start and finish locations are required.")

        # Step 1: Resolve user-provided locations.
        start_coordinates = self._geocode(start)
        finish_coordinates = self._geocode(finish)

        # Step 2: Request the road route once.
        route = self.routing_service.get_route(
            start_coordinates,
            finish_coordinates,
        )

        # Step 3: Match verified stations to the road geometry.
        matches = self.station_matcher.find_nearby_stations(
            geometry=route.geometry,
            route_distance_miles=route.distance_miles,
            max_distance_miles=self.max_station_distance_miles,
        )

        # Step 4: Convert station matcher output into optimizer input.
        candidates = self._fuel_candidates(matches)

        # Step 5: Find the fuel purchasing plan.
        try:
            fuel_plan = self.fuel_optimizer.optimize(
                distance_miles=Decimal(str(route.distance_miles)),
                stations=candidates,
            )
        except FuelOptimizationError as exc:
            raise InsufficientStationCoverageError(
                "A feasible fuel plan could not be generated "
                "using the currently verified fuel stations. "
                "Station coverage may be insufficient."
            ) from exc

        return RoutePlanResult(
            start=start,
            finish=finish,
            start_coordinates=start_coordinates,
            finish_coordinates=finish_coordinates,
            route=route,
            fuel_plan=fuel_plan,
            matched_stations=tuple(matches),
        )
