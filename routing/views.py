from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.serializers import (
    RouteOptimizeRequestSerializer,
    RouteOptimizeResponseSerializer,
)
from routing.services.client import RoutingProviderError
from routing.services.route_planner import (
    InsufficientStationCoverageError,
    LocationNotFoundError,
    RoutePlanner,
    RoutePlanningError,
)


class RouteOptimizeView(APIView):
    authentication_classes = ()
    permission_classes = ()

    @extend_schema(
        summary="Optimize a driving route with fuel stops",
        description=(
            "Calculate a driving route between two US locations "
            "and recommend cost-effective refueling stops. "
            "Assumes a full starting tank, 500-mile maximum range, "
            "and 10 miles per gallon. "
            "The total fuel cost includes only fuel purchased "
            "during the journey. "
            "Station matching uses approximate geographic proximity "
            "and does not include driving detours."
        ),
        request=RouteOptimizeRequestSerializer,
        responses={
            200: RouteOptimizeResponseSerializer,
            400: OpenApiResponse(
                description="Invalid request or unknown location.",
            ),
            422: OpenApiResponse(
                description="Insufficient verified fuel station coverage.",
            ),
            502: OpenApiResponse(
                description="Routing provider unavailable.",
            ),
        },
        tags=["Route Optimization"],
    )
    def post(self, request):
        serializer = RouteOptimizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        planner = RoutePlanner()

        try:
            result = planner.plan(**serializer.validated_data)
        except LocationNotFoundError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InsufficientStationCoverageError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "insufficient_station_coverage",
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except RoutePlanningError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RoutingProviderError:
            return Response(
                {"detail": "Routing provider is temporarily unavailable."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        station_coordinates = {
            station.station_id: {
                "latitude": station.latitude,
                "longitude": station.longitude,
            }
            for station in result.matched_stations
        }

        return Response(
            {
                "start": result.start,
                "finish": result.finish,
                "distance_miles": result.route.distance_miles,
                "duration_minutes": result.route.duration_minutes,
                "geometry": result.route.geometry,
                "fuel": {
                    "total_cost": result.fuel_plan.total_cost,
                    "total_gallons_purchased": (
                        result.fuel_plan.total_gallons_purchased
                    ),
                    "fuel_remaining_gallons": (result.fuel_plan.fuel_remaining_gallons),
                    "stops": [
                        {
                            "station_id": stop.station_id,
                            "name": stop.name,
                            "latitude": station_coordinates[stop.station_id][
                                "latitude"
                            ],
                            "longitude": station_coordinates[stop.station_id][
                                "longitude"
                            ],
                            "distance_along_route": (stop.distance_along_route),
                            "price_per_gallon": stop.price_per_gallon,
                            "gallons_purchased": stop.gallons_purchased,
                            "fuel_cost": stop.fuel_cost,
                        }
                        for stop in result.fuel_plan.stops
                    ],
                },
            },
            status=status.HTTP_200_OK,
        )
