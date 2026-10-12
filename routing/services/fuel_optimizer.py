from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

MAX_RANGE_MILES = Decimal(500)
MILES_PER_GALLON = Decimal(10)
TANK_CAPACITY_GALLONS = MAX_RANGE_MILES / MILES_PER_GALLON

MONEY_QUANTUM = Decimal("0.01")


class FuelOptimizationError(ValueError):
    """Raised when a valid refueling plan cannot be generated."""


@dataclass(frozen=True, slots=True)
class FuelStationCandidate:
    station_id: int
    name: str
    distance_along_route: Decimal
    retail_price: Decimal


@dataclass(frozen=True, slots=True)
class FuelStop:
    station_id: int
    name: str
    distance_along_route: Decimal
    price_per_gallon: Decimal
    gallons_purchased: Decimal
    fuel_cost: Decimal
    fuel_after_refueling: Decimal


@dataclass(frozen=True, slots=True)
class FuelPlan:
    distance_miles: Decimal
    total_gallons_purchased: Decimal
    total_cost: Decimal
    fuel_remaining_gallons: Decimal
    stops: tuple[FuelStop, ...]


class FuelOptimizer:
    def __init__(
        self,
        max_range_miles: Decimal = MAX_RANGE_MILES,
        miles_per_gallon: Decimal = MILES_PER_GALLON,
    ) -> None:
        self.max_range_miles = Decimal(str(max_range_miles))
        self.miles_per_gallon = Decimal(str(miles_per_gallon))

        if (
            not self.max_range_miles.is_finite()
            or self.max_range_miles <= 0
            or not self.miles_per_gallon.is_finite()
            or self.miles_per_gallon <= 0
        ):
            raise ValueError(
                "Range and fuel efficiency must be positive finite values."
            )

        self.tank_capacity = self.max_range_miles / self.miles_per_gallon

    @staticmethod
    def _decimal(value: Decimal) -> Decimal:
        try:
            result = Decimal(str(value))
        except (ValueError, TypeError) as exc:
            raise FuelOptimizationError("Invalid numeric value.") from exc

        if not result.is_finite():
            raise FuelOptimizationError("Numeric values must be finite.")

        return result

    def _next_cheaper_position(
        self,
        index: int,
        stations: list[FuelStationCandidate],
        destination: Decimal,
    ) -> Decimal | None:
        current = stations[index]
        current_position = current.distance_along_route

        # The destination requires no additional fuel purchase.
        if destination - current_position <= self.max_range_miles:
            return destination

        for candidate in stations[index + 1 :]:
            distance = candidate.distance_along_route - current_position

            if distance > self.max_range_miles:
                break

            if candidate.retail_price < current.retail_price:
                return candidate.distance_along_route

        return None

    def optimize(
        self,
        distance_miles: Decimal,
        stations: list[FuelStationCandidate],
    ) -> FuelPlan:
        destination = self._decimal(distance_miles)

        if destination < 0:
            raise FuelOptimizationError("Route distance cannot be negative.")

        ordered_stations = []

        for station in stations:
            position = self._decimal(station.distance_along_route)
            price = self._decimal(station.retail_price)

            if position < 0 or position >= destination:
                raise FuelOptimizationError(
                    f"Station {station.station_id} is outside the route."
                )

            if price <= 0:
                raise FuelOptimizationError(
                    f"Invalid fuel price for station {station.station_id}."
                )

            ordered_stations.append(
                FuelStationCandidate(
                    station_id=station.station_id,
                    name=station.name,
                    distance_along_route=position,
                    retail_price=price,
                )
            )

        ordered_stations.sort(key=lambda station: station.distance_along_route)

        # Keep only the cheapest station at each route position.
        cheapest_by_position: dict[Decimal, FuelStationCandidate] = {}

        for candidate in ordered_stations:
            position = candidate.distance_along_route
            current = cheapest_by_position.get(position)

            if current is None or candidate.retail_price < current.retail_price:
                cheapest_by_position[position] = candidate

        # Crucial: replace the original list with the filtered list.
        ordered_stations = sorted(
            cheapest_by_position.values(),
            key=lambda candidate: candidate.distance_along_route,
        )

        # The vehicle begins with a full tank.
        fuel_remaining = self.tank_capacity
        previous_position = Decimal(0)

        stops = []
        total_gallons = Decimal(0)
        total_cost = Decimal(0)

        for index, station in enumerate(ordered_stations):
            segment_distance = station.distance_along_route - previous_position

            fuel_required = segment_distance / self.miles_per_gallon

            if fuel_required > fuel_remaining:
                raise FuelOptimizationError(
                    "Destination is unreachable with the available "
                    "fuel stations and tank capacity."
                )

            fuel_remaining -= fuel_required
            previous_position = station.distance_along_route

            next_cheaper = self._next_cheaper_position(
                index,
                ordered_stations,
                destination,
            )

            if next_cheaper is not None:
                target_fuel = (
                    next_cheaper - station.distance_along_route
                ) / self.miles_per_gallon
            else:
                # No cheaper station is reachable.
                # Fill up, but never buy fuel beyond what's
                # needed to reach the destination.
                remaining_distance = destination - station.distance_along_route
                target_fuel = min(
                    self.tank_capacity,
                    remaining_distance / self.miles_per_gallon,
                )

            gallons_to_buy = max(
                Decimal(0),
                target_fuel - fuel_remaining,
            )

            if gallons_to_buy == 0:
                continue

            if fuel_remaining + gallons_to_buy > self.tank_capacity:
                raise FuelOptimizationError("Refueling exceeds tank capacity.")

            cost = gallons_to_buy * station.retail_price
            fuel_remaining += gallons_to_buy

            total_gallons += gallons_to_buy
            total_cost += cost

            stops.append(
                FuelStop(
                    station_id=station.station_id,
                    name=station.name,
                    distance_along_route=station.distance_along_route,
                    price_per_gallon=station.retail_price,
                    gallons_purchased=gallons_to_buy,
                    fuel_cost=cost,
                    fuel_after_refueling=fuel_remaining,
                )
            )

        final_segment = destination - previous_position
        final_fuel_required = final_segment / self.miles_per_gallon

        if final_fuel_required > fuel_remaining:
            raise FuelOptimizationError(
                "Destination cannot be reached with the available fuel stations."
            )

        fuel_remaining -= final_fuel_required

        return FuelPlan(
            distance_miles=destination,
            total_gallons_purchased=total_gallons,
            total_cost=total_cost.quantize(
                MONEY_QUANTUM,
                rounding=ROUND_HALF_UP,
            ),
            fuel_remaining_gallons=fuel_remaining,
            stops=tuple(stops),
        )
