from django.db import models


class FuelStation(models.Model):
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

    # Enriched later, not present in the source CSV.
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["state", "city"]),
            models.Index(fields=["retail_price"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} — {self.city}, {self.state}"
