from rest_framework import serializers


class RouteOptimizeRequestSerializer(serializers.Serializer):
    start = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )
    finish = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )


from rest_framework import serializers


class FuelStopSerializer(serializers.Serializer):
    station_id = serializers.IntegerField()
    name = serializers.CharField()

    latitude = serializers.FloatField()
    longitude = serializers.FloatField()

    distance_along_route = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    price_per_gallon = serializers.DecimalField(
        max_digits=12,
        decimal_places=8,
    )
    gallons_purchased = serializers.DecimalField(
        max_digits=14,
        decimal_places=6,
    )
    fuel_cost = serializers.DecimalField(
        max_digits=18,
        decimal_places=8,
    )


class FuelSummarySerializer(serializers.Serializer):
    total_cost = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    total_gallons_purchased = serializers.DecimalField(
        max_digits=14,
        decimal_places=6,
    )
    fuel_remaining_gallons = serializers.DecimalField(
        max_digits=14,
        decimal_places=6,
    )
    stops = FuelStopSerializer(many=True)


class RouteOptimizeResponseSerializer(serializers.Serializer):
    start = serializers.CharField()
    finish = serializers.CharField()

    distance_miles = serializers.FloatField()
    duration_minutes = serializers.FloatField()

    # The routing provider returns GeoJSON LineString geometry.
    geometry = serializers.JSONField()

    fuel = FuelSummarySerializer()
