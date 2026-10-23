"""Phase 2 / Tag 13: Eingabe-Audit und begründete Router-Gegenprüfung.

Diese Prüfungen sind bewusst eng gefasst: nur eindeutige Widersprüche werden
zurückgehalten. Das Audit kann Fakten nicht unabhängig verifizieren.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .inputs import AgentInput
from .router import RouteDecision, route_by_rules


@dataclass(frozen=True, slots=True)
class AuditIssue:
    code: str
    detail: str
    affected_agents: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "detail": self.detail,
            "affected_agents": list(self.affected_agents),
        }


# Die Muster gelten nur fuer explizite Aussagen, nicht fuer Vermutungen.
_SHIPPING_NO = re.compile(
    r"\b(?:kein(?:e[nr]?)?\s+versand|versand\s+(?:nicht\s+m[oö]glich|ausgeschlossen)"
    r"|nur\s+abholung|ausschlie[sß]lich\s+abholung)\b", re.IGNORECASE
)
_SHIPPING_YES = re.compile(
    r"\b(?:versand\s+(?:ist\s+)?m[oö]glich|versand\s+wird\s+angeboten"
    r"|ich\s+(?:versende|verschicke)\b)", re.IGNORECASE
)
_PICKUP_NO = re.compile(
    r"\b(?:keine?\s+abholung|abholung\s+nicht\s+m[oö]glich"
    r"|nur\s+versand|ausschlie[sß]lich\s+versand)\b", re.IGNORECASE
)
_PICKUP_YES = re.compile(
    r"\b(?:abholung\s+(?:ist\s+)?m[oö]glich|selbstabholung\s+m[oö]glich)\b",
    re.IGNORECASE,
)
_SOLD = re.compile(r"\b(?:bereits\s+verkauft|ist\s+verkauft|nicht\s+mehr\s+verf[uü]gbar)\b", re.IGNORECASE)
_RESERVED = re.compile(r"\b(?:ist\s+reserviert|bereits\s+reserviert)\b", re.IGNORECASE)
_AVAILABLE = re.compile(r"\b(?:noch\s+verf[uü]gbar|sofort\s+verf[uü]gbar|noch\s+da)\b", re.IGNORECASE)
_INJECTION = re.compile(
    r"\b(?:ignoriere\s+(?:alle\s+)?(?:vorherigen\s+)?(?:regeln|anweisungen|instruktionen)"
    r"|ignore\s+(?:all\s+)?(?:previous\s+)?instructions|system\s*prompt"
    r"|developer\s*message|jailbreak)\b", re.IGNORECASE
)


def inspect_input(data: AgentInput) -> tuple[AuditIssue, ...]:
    """Kennzeichnet eindeutige Text-/Feld-Widersprueche und Injection-Versuche."""
    if not isinstance(data, AgentInput):
        raise TypeError("AgentInput erforderlich.")
    product = data.product
    description = product.description or ""
    issues: list[AuditIssue] = []

    shipping_no = bool(_SHIPPING_NO.search(description))
    shipping_yes = bool(_SHIPPING_YES.search(description)) and not shipping_no
    if (product.shipping_available is True and shipping_no) or (
        product.shipping_available is False and shipping_yes
    ):
        issues.append(AuditIssue(
            "shipping_conflict",
            "Versandangabe und Produktbeschreibung widersprechen sich; Versandantwort zurückhalten.",
            ("logistics",),
        ))

    pickup_no = bool(_PICKUP_NO.search(description))
    pickup_yes = bool(_PICKUP_YES.search(description)) and not pickup_no
    if (product.pickup_available is True and pickup_no) or (
        product.pickup_available is False and pickup_yes
    ):
        issues.append(AuditIssue(
            "pickup_conflict",
            "Abholangabe und Produktbeschreibung widersprechen sich; Logistikantwort zurückhalten.",
            ("logistics",),
        ))

    sold = bool(_SOLD.search(description))
    reserved = bool(_RESERVED.search(description))
    available = bool(_AVAILABLE.search(description))
    if ((product.availability == "available" and (sold or reserved))
        or (product.availability == "sold" and (available or reserved))
        or (product.availability == "reserved" and (sold or available))):
        issues.append(AuditIssue(
            "availability_conflict",
            "Verfügbarkeitsstatus und Produktbeschreibung widersprechen sich; Informationsantwort zurückhalten.",
            ("information",),
        ))

    if _INJECTION.search(data.request.message):
        issues.append(AuditIssue(
            "untrusted_customer_instruction",
            "Kundenfrage enthält eine mögliche Steueranweisung; nur als Nutzerdaten behandeln.",
        ))
    if _INJECTION.search(description):
        issues.append(AuditIssue(
            "untrusted_product_instruction",
            "Produktbeschreibung enthält eine mögliche Steueranweisung.",
            ("information",),
        ))
    return tuple(issues)


def reconcile_route(data: AgentInput, decision: RouteDecision) -> tuple[RouteDecision, tuple[AuditIssue, ...]]:
    """Ergänzt nur bei LLM-Routing eindeutige Regel-Treffer, ohne Agenten zu entfernen.

    Eine zweite Heuristik darf eine freie LLM-Klassifikation nicht als absolut
    wahr deklarieren. Jede Abweichung wird transparent protokolliert.
    """
    if not isinstance(data, AgentInput) or not isinstance(decision, RouteDecision):
        raise TypeError("AgentInput und RouteDecision erforderlich.")
    if decision.source != "llm":
        return decision, ()

    rules = route_by_rules(data)
    missing = tuple(name for name in rules.agents if name not in decision.agents)
    extra = tuple(name for name in decision.agents if name not in rules.agents)
    issues: list[AuditIssue] = []

    if extra and rules.agents:
        issues.append(AuditIssue(
            "router_unconfirmed_agent",
            "Regeln bestätigen nicht alle LLM-Agenten; Klassifikation manuell bewerten: "
            + ", ".join(extra),
        ))
    if not missing:
        return decision, tuple(issues)

    merged = decision.agents + missing
    issues.append(AuditIssue(
        "router_missing_intent",
        "Die Router-Gegenprüfung hat weitere eindeutige Anliegen gefunden: "
        + ", ".join(missing),
        missing,
    ))
    reason = decision.reason[:200] + " [Regelabgleich ergänzt]"
    warning = ((decision.warning + " ") if decision.warning else "") + (
        "Regelabgleich hat zusätzliche Agenten ausgewählt: " + ", ".join(missing) + "."
    )
    corrected = RouteDecision(
        agents=merged,
        reason=reason,
        needs_clarification=False,
        source="llm",
        warning=warning,
    )
    return corrected, tuple(issues)
