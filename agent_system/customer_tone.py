"""Käuferfreundliche, datengebundene Formulierungen für die Verkäuferprüfung.

Kein Modellaufruf, keine eigenständige Preiszusage, keine Freigabe.
Diese Ansicht ist ein *neuer*, manuell zu prüfender Entwurf, nicht das
validierte Ergebnis der Agenten-Pipeline.
"""
from __future__ import annotations

import re
from decimal import Decimal

from .inputs import AgentInput


_PRICE_IN_QUESTION = re.compile(r"(?<!\w)(\d{1,7}(?:[.,]\d{1,2})?)\s*(?:€|euro\b)", re.I)
_SHIPPING = re.compile(r"\b(?:versand\w*|versend\w*|verschick\w*|liefer\w*|porto|zustell\w*)\b", re.I)
_PICKUP = re.compile(r"\b(?:abhol\w*|abholen|treffpunkt|vor\s+ort)\b", re.I)
_LOCATION = re.compile(r"\b(?:standort|adresse|ort|wo|stadt)\b", re.I)
_AVAILABILITY = re.compile(r"\b(?:verf[üu]gbar\w*|reserviert|verkauft|noch\s+da|schon\s+weg)\b", re.I)
_CONDITION = re.compile(r"\b(?:zustand|kratzer|defekt\w*|besch[äa]dig\w*|funktionier\w*)\b", re.I)
_DETAILS = re.compile(r"\b(?:ram|ssd|akku|speicher|modell|baujahr|wie\s+alt|technisch\w*)\b", re.I)


def _euro(value: Decimal) -> str:
    return f"{value:.2f}".replace(".", ",") + " €"


def _offer(question: str) -> Decimal | None:
    hit = _PRICE_IN_QUESTION.search(question)
    if hit is None:
        return None
    try:
        return Decimal(hit.group(1).replace(",", "."))
    except Exception:
        return None


def compose_buyer_friendly_draft(data: AgentInput, agent_names: tuple[str, ...] | list[str]) -> str | None:
    """Erzeugt nur einen vom Verkäufer zu prüfenden Text.

    Bei fehlendem/ungültigem Routing wird keine vermeintlich fertige
    Kundenantwort gebaut. Produktbeschreibung wird nicht wörtlich eingefügt.
    """
    if not isinstance(data, AgentInput):
        raise TypeError("AgentInput erwartet.")
    if not isinstance(agent_names, (list, tuple)) or not agent_names:
        return None
    if any(name not in {"information", "negotiation", "logistics"} for name in agent_names):
        return None

    product = data.product
    q = data.request.message
    sentences: list[str] = []
    names = set(agent_names)

    if "information" in names:
        if _AVAILABILITY.search(q):
            if product.availability == "available":
                sentences.append("Der Artikel ist laut den hinterlegten Angaben noch verfügbar.")
            elif product.availability == "reserved":
                sentences.append("Der Artikel ist aktuell als reserviert eingetragen.")
            elif product.availability == "sold":
                sentences.append("Der Artikel ist als verkauft eingetragen.")
            else:
                sentences.append("Ob der Artikel noch verfügbar ist, müsste ich kurz prüfen.")
        if _CONDITION.search(q):
            if product.condition:
                sentences.append(f"Der Zustand ist mit „{product.condition}“ angegeben.")
            else:
                sentences.append("Zum Zustand müsste ich dir noch eine genauere Angabe machen.")
        if _DETAILS.search(q):
            # Freitext-Beschreibungen können unzuverlässig und sogar manipulativ
            # sein; deshalb nicht unkontrolliert als Verkäuferbehauptung kopieren.
            sentences.append("Zu den technischen Details müsste ich noch einmal nachsehen.")
        if not sentences and "negotiation" not in names and "logistics" not in names:
            sentences.append("Danke für deine Frage. Die genauen Angaben müsste ich noch einmal prüfen.")

    if "logistics" in names:
        shipping = bool(_SHIPPING.search(q))
        pickup = bool(_PICKUP.search(q))
        location = bool(_LOCATION.search(q))
        if not any((shipping, pickup, location)):
            shipping = pickup = True
        if shipping:
            if product.shipping_available is True:
                sentences.append("Ja, Versand ist möglich. Die genauen Versandkosten und die Lieferzeit müsste ich noch klären.")
            elif product.shipping_available is False:
                sentences.append("Leider biete ich für diesen Artikel keinen Versand an.")
            else:
                sentences.append("Ob Versand möglich ist, müsste ich noch prüfen.")
        if pickup:
            if product.pickup_available is True:
                sentences.append("Eine Abholung ist möglich; den Termin müssten wir noch abstimmen.")
            elif product.pickup_available is False:
                sentences.append("Eine Abholung wird derzeit nicht angeboten.")
            else:
                sentences.append("Ob eine Abholung möglich ist, müsste ich noch prüfen.")
        if (pickup or location) and product.location:
            sentences.append(f"Der angegebene Standort ist {product.location}.")
        elif location and not product.location:
            sentences.append("Den genauen Standort müsste ich dir noch nennen.")

    if "negotiation" in names:
        if product.price_eur is None:
            sentences.append("Zum Preis müsste ich noch eine genaue Angabe machen.")
        else:
            tag = " VB" if product.is_negotiable is True else ""
            sentences.append(f"In der Anzeige steht ein Preis von {_euro(product.price_eur)}{tag}.")
            offer = _offer(q)
            if offer is not None and offer > product.price_eur:
                sentences.append(f"Du hast {_euro(offer)} genannt – war das so gemeint?")
            elif product.is_negotiable is True:
                sentences.append("Deinen Preisvorschlag schaue ich mir gern an; zugesagt ist noch nichts.")
            else:
                sentences.append("Ob ich einen anderen Preis anbiete, müsste ich erst entscheiden.")

    if not sentences:
        return None
    # Absichtlich nur ein Vorschlag für die vom Verkäufer kontrollierte Fassung.
    return "Hallo!\n\n" + " ".join(sentences) + "\n\nViele Grüße"
