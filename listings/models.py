"""Datenmodell für Marketplace-Anzeigen – ohne KI-Komponenten."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


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


class CustomerInquiry(models.Model):
    """Private Kundenanfrage mit Entwurf; keine gesendete Verkäuferantwort."""

    class DraftProcessing(models.TextChoices):
        READY = "ready", "KI-Entwurf abgeschlossen"
        QUEUED = "queued", "KI-Entwurf wartet"
        RUNNING = "running", "KI-Entwurf wird erstellt"
        FAILED = "failed", "KI-Entwurf fehlgeschlagen"

    class Status(models.TextChoices):
        REVIEW_REQUIRED = "review_required", "Verkäuferprüfung erforderlich"
        NEEDS_ATTENTION = "needs_attention", "Manuelle Bearbeitung erforderlich"
        IN_PROGRESS = "in_progress", "In Bearbeitung"
        APPROVED = "approved", "Vom Verkäufer freigegeben"

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="customer_inquiries",
        verbose_name="Anzeige",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="customer_inquiries", verbose_name="Interessent",
    )
    message = models.TextField("Kundenfrage", max_length=2000)
    private_draft = models.TextField("Privater Antwortentwurf", blank=True)
    # Verkäufertext bleibt getrennt vom unveränderten KI-Original.
    # Bis zur ausdrücklichen Freigabe bleiben alle Antworten private Entwürfe.
    seller_draft = models.TextField(
        "Vom Verkäufer bearbeiteter Entwurf", max_length=3000, blank=True,
    )
    seller_draft_updated_at = models.DateTimeField(
        "Entwurf zuletzt gespeichert", null=True, blank=True,
    )
    # Freigabe als eigene, unveränderliche Momentaufnahme: NICHT gleich Versand.
    approved_response = models.TextField(
        "Freigegebene Antwort (nur intern)", blank=True, max_length=3000,
    )
    approved_at = models.DateTimeField(
        "Freigabezeitpunkt", null=True, blank=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_customer_inquiries", verbose_name="Freigegeben von",
    )
    status = models.CharField(
        "Bearbeitungsstatus", max_length=24, choices=Status.choices,
        default=Status.NEEDS_ATTENTION,
    )
    # Phase 3 Tag 23: getrennte Verarbeitung, ohne den Verkäuferstatus umzudeuten.
    # ready ist der Default für bereits vorhandene Anfragen aus Tag 16–22.
    draft_processing = models.CharField(
        "KI-Verarbeitung", max_length=12, choices=DraftProcessing.choices,
        default=DraftProcessing.READY, db_index=True,
    )
    draft_started_at = models.DateTimeField("KI-Lauf gestartet", null=True, blank=True)
    draft_finished_at = models.DateTimeField("KI-Lauf beendet", null=True, blank=True)
    draft_attempts = models.PositiveIntegerField("Verarbeitungsversuche", default=0)
    route_source = models.CharField("Routerquelle", max_length=12, blank=True)
    selected_agents = models.JSONField("Ausgewählte Agenten", default=list, blank=True)
    audit = models.JSONField("Prüfhinweise", default=list, blank=True)
    created_at = models.DateTimeField("Erstellt", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kundenanfrage"
        verbose_name_plural = "Kundenanfragen"

    def __str__(self):
        return f"Anfrage #{self.pk} zu {self.listing_id}"



class InquiryDelivery(models.Model):
    """Eine einzige, ausdrücklich veröffentlichte Antwort pro Kundenanfrage.

    Das unabhängige Snapshot-Feld schützt die Käuferansicht gegen nachträgliche
    Änderungen am intern freigegebenen Antworttext.
    Kein E-Mail- oder externer Versand: die Antwort wird im Käuferpostfach sichtbar.
    """

    inquiry = models.OneToOneField(
        CustomerInquiry, on_delete=models.CASCADE,
        related_name="delivery", verbose_name="Kundenanfrage",
    )
    response_text = models.TextField("Bereitgestellte Antwort", max_length=3000)
    delivered_at = models.DateTimeField("Bereitgestellt am", auto_now_add=True)
    delivered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="inquiry_deliveries", verbose_name="Bereitgestellt von",
    )

    class Meta:
        verbose_name = "Bereitgestellte Antwort"
        verbose_name_plural = "Bereitgestellte Antworten"
        ordering = ["-delivered_at"]

    def __str__(self):
        return f"Antwort für Anfrage #{self.inquiry_id}"


class InquiryEvent(models.Model):
    """Append-only Ereignisprotokoll der normalen Anfrage-Workflows.

    Keine Nachrichtentexte, keine KI-Entwürfe, keine Audit-Payloads kopieren.
    `audience` steuert die minimale UI-Sichtbarkeit; Käufer-Views filtern
    zusätzlich explizit auf zwei erlaubte Ereignistypen.
    """

    class Kind(models.TextChoices):
        RECEIVED = "received", "Kundenanfrage eingegangen"
        DRAFT_CREATED = "draft_created", "Interner Antwortentwurf erstellt"
        DRAFT_FAILED = "draft_failed", "Automatischer Entwurf fehlgeschlagen"
        STARTED = "started", "Verkäufer hat Bearbeitung begonnen"
        SELLER_DRAFT_SAVED = "seller_draft_saved", "Verkäuferentwurf gespeichert"
        APPROVED = "approved", "Antwort intern freigegeben"
        DELIVERED = "delivered", "Antwort für Käufer bereitgestellt"

    class Audience(models.TextChoices):
        BUYER = "buyer", "Für Käufer sichtbar"
        SELLER = "seller", "Nur für Verkäufer"

    inquiry = models.ForeignKey(
        CustomerInquiry, on_delete=models.CASCADE, related_name="events",
        verbose_name="Kundenanfrage",
    )
    kind = models.CharField("Ereignis", max_length=24, choices=Kind.choices)
    audience = models.CharField(
        "Sichtbarkeit", max_length=8, choices=Audience.choices,
        default=Audience.SELLER,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="inquiry_events", verbose_name="Ausgelöst von",
    )
    occurred_at = models.DateTimeField(
        "Ereigniszeitpunkt", default=timezone.now, db_index=True,
    )

    class Meta:
        ordering = ["occurred_at", "pk"]
        verbose_name = "Anfrageereignis"
        verbose_name_plural = "Anfrageereignisse"
        indexes = [
            models.Index(fields=["inquiry", "occurred_at"], name="inquiry_event_when_idx"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} – Anfrage #{self.inquiry_id}"
