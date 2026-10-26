"""Tag 23: DB-Queue fuer private KI-Entwuerfe. Kein HTTP-Thread und kein Mailversand.

Eine separate Django-Management-Command ruft diesen Code auf.
Anfragen werden per bedingtem DB-UPDATE beansprucht (nur 1 Worker gewinnt).
Eine Versuchszahl schuetzt gegen spaet eintreffende Ergebnisse nach Recovery.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .agent_bridge import generate_private_draft
from .inquiry_timeline import record_event
from .models import CustomerInquiry, InquiryEvent

logger = logging.getLogger(__name__)


def process_inquiry(inquiry_id: int, *, use_llm: bool | None = None) -> bool:
    """Beanspruche genau einen Queue-Eintrag und bearbeite ihn. False = schon belegt.

    Bei Ollama-Timeout/Fault bleibt die Anfrage erhalten; der Verkaeufer kann
    manuell antworten. Ein regelbasierter Fallback wird als solcher ausgewiesen.
    """
    queued = CustomerInquiry.DraftProcessing.QUEUED
    running = CustomerInquiry.DraftProcessing.RUNNING
    claimed = CustomerInquiry.objects.filter(
        pk=inquiry_id, draft_processing=queued,
    ).exclude(status=CustomerInquiry.Status.APPROVED).update(
        draft_processing=running, draft_started_at=timezone.now(),
        draft_attempts=F("draft_attempts") + 1,
    )
    if claimed != 1:
        return False

    try:
        inquiry = CustomerInquiry.objects.select_related("listing").get(pk=inquiry_id)
    except CustomerInquiry.DoesNotExist:
        return False  # Anzeige geloescht, daher Anfrage durch CASCADE weg.
    attempt = inquiry.draft_attempts
    if use_llm is None:
        use_llm = getattr(settings, "FUNDPLATZ_AGENT_USE_LLM", False)

    failure = False
    try:
        output = generate_private_draft(inquiry.listing, inquiry.message, use_llm=use_llm)
        result = output.result
        draft = result.combined_draft
        source = result.route.source
        agents = list(result.route.agents)
        audit = [item.to_dict() for item in result.audit]
        status = (CustomerInquiry.Status.NEEDS_ATTENTION
                  if output.requires_attention else CustomerInquiry.Status.REVIEW_REQUIRED)
    except Exception:
        # Kein Traceback und keine internen Fehlermeldungen an den Kaeufer.
        logger.exception("Privater Worker-Entwurf fuer Anfrage %s fehlgeschlagen", inquiry_id)
        failure = True
        draft = "Kein automatischer Entwurf verfügbar. Bitte manuell antworten."
        source = ""
        agents = []
        audit = []
        status = CustomerInquiry.Status.NEEDS_ATTENTION

    with transaction.atomic():
        # Versuchszahl verhindert, dass ein nach Recovery ueberholter Worker
        # einen neuen Lauf oder gar eine inzwischen freigegebene Antwort ersetzt.
        current = CustomerInquiry.objects.select_for_update().filter(
            pk=inquiry_id, draft_processing=running, draft_attempts=attempt,
        ).exclude(status=CustomerInquiry.Status.APPROVED).first()
        if current is None:
            return False
        current.private_draft = draft
        current.route_source = source
        current.selected_agents = agents
        current.audit = audit
        current.status = status
        current.draft_processing = (
            CustomerInquiry.DraftProcessing.FAILED
            if failure else CustomerInquiry.DraftProcessing.READY
        )
        current.draft_finished_at = timezone.now()
        current.save(update_fields=[
            "private_draft", "route_source", "selected_agents", "audit", "status",
            "draft_processing", "draft_finished_at",
        ])
        record_event(current, InquiryEvent.Kind.DRAFT_FAILED if failure
                     else InquiryEvent.Kind.DRAFT_CREATED)
    return True


def next_queued_id() -> int | None:
    """Keine langen Datenbanksperren waehrend Ollama-Aufrufen."""
    return (CustomerInquiry.objects.filter(
        draft_processing=CustomerInquiry.DraftProcessing.QUEUED
    ).exclude(status=CustomerInquiry.Status.APPROVED).order_by(
        "created_at", "pk"
    ).values_list("pk", flat=True).first())


def recover_stale(*, minutes: int = 30) -> int:
    """Nur auf ausdruecklichen Operator-Befehl. Ein laufender Job koennte
    dabei erneut eingeplant werden, daher ist der Versuchszahl-Schutz Pflicht.
    """
    if minutes < 5:
        raise ValueError("Recovery erst nach mindestens fuenf Minuten erlaubt.")
    cutoff = timezone.now() - timedelta(minutes=minutes)
    return (CustomerInquiry.objects.filter(
        draft_processing=CustomerInquiry.DraftProcessing.RUNNING,
        draft_started_at__lt=cutoff,
    ).exclude(status=CustomerInquiry.Status.APPROVED).update(
        draft_processing=CustomerInquiry.DraftProcessing.QUEUED,
        draft_started_at=None,
    ))
