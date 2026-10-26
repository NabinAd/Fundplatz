"""Lesende Abschlusspruefung der Fundplatz-Anfragen (Phase 3, Tag 25).

Keine Aenderung an der Datenbank. Ausgabe enthaelt niemals Nachrichtentexte,
KI-Entwuerfe, Kundennamen, geheime Konfigurationswerte oder Audit-Payloads.
"""
import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import F, Q
from django.utils import timezone

from listings.models import CustomerInquiry, InquiryDelivery, InquiryEvent, Listing


class Command(BaseCommand):
    help = "Liest und prueft Freigaben, Bereitstellungen, Timeline-Privacy und Worker-Status."

    def add_arguments(self, parser):
        parser.add_argument("--json", dest="as_json", action="store_true", help="JSON-Bericht ausgeben")
        parser.add_argument("--strict", action="store_true", help="Bei Daten-Inkonsistenzen mit Fehlercode enden")
        parser.add_argument("--stale-minutes", type=int, default=30,
                            help="Altersgrenze fuer laufende KI-Jobs (mind. 5; Standard 30)")

    def handle(self, *args, **options):
        minutes = options["stale_minutes"]
        if minutes < 5:
            raise CommandError("--stale-minutes muss mindestens 5 sein.")

        cutoff = timezone.now() - timedelta(minutes=minutes)
        q = CustomerInquiry.objects
        deliveries = InquiryDelivery.objects
        events = InquiryEvent.objects
        errors = {}
        warnings = {}

        # Eine intern freigegebene Antwort braucht Text, Zeitpunkt und Freigeber.
        errors["approved_missing_fields"] = q.filter(status="approved").filter(
            Q(approved_at__isnull=True) | Q(approved_by__isnull=True) | Q(approved_response="")
        ).count()
        errors["approved_wrong_seller"] = q.filter(
            status="approved", approved_by__isnull=False
        ).exclude(approved_by_id=F("listing__seller_id")).count()
        errors["approval_data_without_approval"] = q.exclude(status="approved").filter(
            Q(approved_at__isnull=False) | Q(approved_by__isnull=False) | ~Q(approved_response="")
        ).count()
        errors["delivery_without_valid_approval"] = deliveries.filter(
            Q(inquiry__approved_at__isnull=True)
            | Q(inquiry__approved_response="")
            | ~Q(inquiry__status="approved")
        ).count()
        errors["delivery_text_changed"] = deliveries.exclude(
            response_text=F("inquiry__approved_response")
        ).count()
        errors["delivery_wrong_seller"] = deliveries.exclude(
            delivered_by_id=F("inquiry__listing__seller_id")
        ).count()
        errors["delivery_before_approval"] = deliveries.filter(
            delivered_at__lt=F("inquiry__approved_at")
        ).count()
        errors["private_event_marked_public"] = events.filter(
            audience=InquiryEvent.Audience.BUYER
        ).exclude(kind__in=[InquiryEvent.Kind.RECEIVED, InquiryEvent.Kind.DELIVERED]).count()
        errors["approved_still_queued"] = q.filter(
            status="approved", draft_processing__in=["queued", "running"]
        ).count()
        errors["unknown_processing_state"] = q.exclude(
            draft_processing__in=CustomerInquiry.DraftProcessing.values
        ).count()

        # Warnungen sind Hinweise zur Wartung, nicht automatisch Datenkorruption.
        warnings["stale_running"] = q.filter(draft_processing="running").filter(
            Q(draft_started_at__lt=cutoff) | Q(draft_started_at__isnull=True)
        ).count()
        warnings["received_event_missing"] = q.exclude(
            events__kind=InquiryEvent.Kind.RECEIVED
        ).count()
        warnings["delivery_event_missing"] = deliveries.exclude(
            inquiry__events__kind=InquiryEvent.Kind.DELIVERED
        ).count()

        # Konfiguration ist rein lokal; niemals Schluessel oder Benutzerinhalte ausgeben.
        local_only = (
            settings.DEBUG
            or str(settings.SECRET_KEY).startswith("django-insecure-fundplatz-only-for-local-development")
            or not getattr(settings, "SESSION_COOKIE_SECURE", False)
            or not getattr(settings, "CSRF_COOKIE_SECURE", False)
        )
        counts = {
            "listings": Listing.objects.count(),
            "inquiries": q.count(),
            "deliveries": deliveries.count(),
            "events": events.count(),
            "queued": q.filter(draft_processing="queued").count(),
            "running": q.filter(draft_processing="running").count(),
            "ready": q.filter(draft_processing="ready").count(),
            "failed": q.filter(draft_processing="failed").count(),
        }
        report = {
            "report": "Fundplatz Tag 25 Daten- und Ablaufpruefung",
            "mode": "lokales MVP",
            "data_consistent": not any(errors.values()),
            "public_deployment_ready": False,  # Kein Online-Sicherheitsaudit durch diesen Befehl.
            "configuration": {
                "async_enabled": bool(getattr(settings, "FUNDPLATZ_AGENT_ASYNC", False)),
                "llm_enabled": bool(getattr(settings, "FUNDPLATZ_AGENT_USE_LLM", False)),
                "local_development_settings_detected": bool(local_only),
            },
            "counts": counts,
            "errors": errors,
            "warnings": warnings,
            "note": "Keine automatisierte Freigabe fuer das Internet; funktionale Tests und manuelle Pruefung bleiben notwendig.",
        }

        if options["as_json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))
        else:
            self.stdout.write("Fundplatz – Abschlusspruefung (nur lesen)")
            for name, value in counts.items():
                self.stdout.write(f"  {name}: {value}")
            for name, value in errors.items():
                self.stdout.write(f"  [FEHLER] {name}: {value}" if value else f"  [OK] {name}: 0")
            for name, value in warnings.items():
                self.stdout.write(f"  [HINWEIS] {name}: {value}")
            if local_only:
                self.stdout.write("  [HINWEIS] Nur fuer lokale Entwicklung konfiguriert, nicht fuer oeffentliches Hosting.")
            self.stdout.write("Datenkonsistenz: " + ("OK" if report["data_consistent"] else "FEHLER"))

        if options["strict"] and not report["data_consistent"]:
            raise CommandError("Dateninkonsistenzen gefunden. Bitte Bericht auswerten.")
        return None
