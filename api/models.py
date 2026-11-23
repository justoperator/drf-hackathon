"""Models for parking levels and parking requests."""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class ParkingLevel(models.Model):
    name = models.CharField(max_length=50, unique=True)
    available = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(available__gte=0),
                name="parking_level_available_nonnegative",
            ),
        ]
        ordering = ["id"]

    def __str__(self):
        return self.name


class ParkingRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        CONFIRMED = "confirmed", "Підтверджена"
        CANCELLED = "cancelled", "Скасована"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parking_requests",
    )
    level = models.ForeignKey(
        ParkingLevel,
        on_delete=models.PROTECT,
        related_name="parking_requests",
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(
        max_length=9,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=1),
                name="parking_request_quantity_positive",
            ),
        ]
        ordering = ["id"]

    def __str__(self):
        return f"{self.level} / {self.quantity} ({self.status})"
