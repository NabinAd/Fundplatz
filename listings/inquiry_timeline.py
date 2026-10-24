"""Kleine Hilfsfunktionen für die Tag-21-Ereignisprotokollierung.

Rufe `record_event` nach der Zustandsänderung IN DERSELBEN atomic-Transaktion
auf. Die Käuferseite sieht weder Agenten-Diagnostik noch private Schritte.
"""
from .models import InquiryEvent


_PUBLIC_KINDS = frozenset({
    InquiryEvent.Kind.RECEIVED, InquiryEvent.Kind.DELIVERED,
})


def record_event(inquiry, kind, *, actor=None, occurred_at=None):
    """Neues Ereignis ohne Nachrichtentext oder interne Auditdaten speichern."""
    if kind not in InquiryEvent.Kind.values:
        raise ValueError("Unbekannter Ereignistyp")
    kwargs = {
        "inquiry": inquiry,
        "kind": kind,
        "actor": actor,
        "audience": (
            InquiryEvent.Audience.BUYER
            if kind in _PUBLIC_KINDS else InquiryEvent.Audience.SELLER
        ),
    }
    if occurred_at is not None:
        kwargs["occurred_at"] = occurred_at
    return InquiryEvent.objects.create(**kwargs)


def buyer_timeline(inquiry):
    """Strikte erlaubte Liste verhindert Lecks bei fehlerhaften audience-Werten."""
    return InquiryEvent.objects.filter(
        inquiry=inquiry, audience=InquiryEvent.Audience.BUYER,
        kind__in=tuple(_PUBLIC_KINDS),
    ).order_by("occurred_at", "pk")


def seller_timeline(inquiry):
    return InquiryEvent.objects.filter(inquiry=inquiry).select_related("actor").order_by("occurred_at", "pk")
