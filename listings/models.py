"""Datenmodell für Marketplace-Anzeigen – ohne KI-Komponenten."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Listing(models.Model):
    class Category(models.TextChoices):
        ELECTRONICS = "electronics", "Elektronik"
        FURNITURE = "furniture", "Möbel & Wohnen"
        FASHION = "fashion", "Mode"
        SPORTS = "sports", "Sport & Freizeit"
        OTHER = "other", "Sonstiges"

    class Condition(models.TextChoices):
        NEW = "new", "Neu"
        LIKE_NEW = "like_new", "Wie neu"
        GOOD = "good", "Gut"
        USED = "used", "Gebraucht"
        DEFECTIVE = "defective", "Defekt"

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
        verbose_name="Verkäufer",
    )
    title = models.CharField("Titel", max_length=120)
    description = models.TextField("Beschreibung")
    price = models.DecimalField(
        "Preis in EUR",
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    category = models.CharField(
        "Kategorie", max_length=20, choices=Category.choices, default=Category.OTHER
    )
    condition = models.CharField(
        "Zustand", max_length=20, choices=Condition.choices, default=Condition.USED
    )
    image = models.ImageField("Produktbild", upload_to="listings/", blank=True)
    location = models.CharField("Ort", max_length=100, blank=True)
    shipping_available = models.BooleanField("Versand möglich", default=False)
    pickup_available = models.BooleanField("Abholung möglich", default=True)
    is_negotiable = models.BooleanField("Verhandlungsbasis", default=False)
    is_active = models.BooleanField("Anzeige aktiv", default=True)
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    updated_at = models.DateTimeField("Geändert am", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Anzeige"
        verbose_name_plural = "Anzeigen"

    def __str__(self):
        return self.title
