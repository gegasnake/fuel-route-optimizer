from django.db import models


class FuelStation(models.Model):
    class GeocodingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REVIEW = "review", "Needs review"
        FAILED = "failed", "Failed"

    opis_id = models.PositiveIntegerField(db_index=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=2, db_index=True)
    rack_id = models.PositiveIntegerField()

    retail_price = models.DecimalField(
        max_digits=12,
        decimal_places=8,
    )

    source_row_number = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
    )

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    geocoding_status = models.CharField(
        max_length=10,
        choices=GeocodingStatus.choices,
        default=GeocodingStatus.PENDING,
        db_index=True,
    )

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["state", "city"]),
            models.Index(fields=["retail_price"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} — {self.city}, {self.state}"


class GeocodingCache(models.Model):
    query = models.CharField(max_length=600, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Geocoding cache"
        verbose_name_plural = "Geocoding cache entries"

    def __str__(self) -> str:
        return self.query
