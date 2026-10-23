"""Tag 12: konservativer Regel-Validator für Entwürfe aus drei Agenten.

Grenzen: Er prüft die Übereinstimmung mit deterministischen Antwortvorlagen,
auffällige Zusagen und einige typische Prompt-Injection-Muster. Er kann NICHT
allgemein beweisen, dass freie LLM-Paraphrasen wahr sind oder Produktdaten
korrekt sind. Eine Verkäuferfreigabe bleibt immer erforderlich.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .agents import AGENT_REGISTRY, AgentReply
from .inputs import AgentInput

# Keine dieser Markierungen gilt als Freigabe für den Versand an Kunden.
DRAFT_PASS = "passed_template_checks"
DRAFT_BLOCK = "blocked"
SUGGESTION_NONE = "not_present"
SUGGESTION_PASS = "matches_template"
SUGGESTION_REVIEW = "manual_review_required"
SUGGESTION_BLOCK = "blocked"

# Eine Liste erkennbarer Risiken, KEIN semantischer Halluzinationsdetektor.
_INJECTION = re.compile(
    r"\b(?:ignoriere\s+(?:alle\s+)?(?:vorherigen?\s+)?(?:regeln|anweisungen|instruktionen|systemprompt)"
    r"|system\s*prompt|developer\s*message|jailbreak|du\s+bist\s+jetzt\s+(?:der|ein)\s+(?:system|admin)"
    r"|override\s+(?:the\s+)?(?:instructions|system)|ignore\s+(?:all\s+)?(?:previous\s+)?instructions)\b",
    flags=re.IGNORECASE,
)
_COMMITMENT = re.compile(
    r"\b(?:ich\s+(?:akzeptiere|garantiere|verspreche|bestätige\s+hiermit|"
    r"verkaufe\s+(?:es|ihn|dir|das)|nehme\s+(?:dein|das)\s+angebot\s+an)"
    r"|(?:angebot|preis)\s+ist\s+(?:angenommen|akzeptiert)"
    r"|(?:verkauft|reserviert)\s+(?:für|fuer)\s+dich"
    r"|du\s+bekommst\s+(?:es|ihn|das)\s+für)\b",
    flags=re.IGNORECASE,
)
_UNAUTHORIZED_DELIVERY = re.compile(
    r"\b(?:kostenloser?\s+versand|versand\s+ist\s+kostenlos|"
    r"lieferung\s+(?:garantiert|morgen|übermorgen)|"
    r"garantiert(?:e)?\s+(?:lieferung|zustellung)|"
    r"ich\s+(?:verschicke|versende|liefere)\s+(?:es|das|ihn)\s+(?:morgen|übermorgen))\b",
    flags=re.IGNORECASE,
)
# Neue Zahlen (etwa 16 GB / 5 € / 2 Tage) sollen niemals durch bloße
# LLM-Umformulierungen automatisch als belegte Information gelten.
_NUMBERS = re.compile(r"(?<![\w])\d+(?:[.,]\d+)*(?![\w])")
_AVAILABILITY_ASSERTION = re.compile(
    r"\b(?:ist\s+(?:noch\s+)?(?:sofort\s+)?(?:verfügbar|reserviert|verkauft)"
    r"|ist\s+(?:nicht\s+)?verfügbar|auf\s+lager|bereits\s+verkauft)\b",
    flags=re.IGNORECASE,
)
_SHIPPING_ASSERTION = re.compile(
    r"\b(?:versand\s+ist\s+möglich|versand\s+wird\s+angeboten|"
    r"ich\s+(?:versende|verschicke)|kein\s+versand\s+möglich)\b",
    flags=re.IGNORECASE,
)


def _numbers(text: str) -> set[str]:
    return {m.group().replace(",", ".") for m in _NUMBERS.finditer(text)}


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class ValidationResult:
    agent: str
    draft_status: str
    suggestion_status: str
    checked_draft: str | None
    issues: tuple[ValidationIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "draft_status": self.draft_status,
            "suggestion_status": self.suggestion_status,
            "checked_draft": self.checked_draft,
            "issues": [issue.to_dict() for issue in self.issues],
        }


class ResponseValidator:
    """Verlangt eine unveränderte, erneut berechnete Antwortvorlage.

    Für abweichende freie LLM-Texte gilt *fail closed*: nie automatisch
    in combined_draft übernehmen. Gefährliche Anzeichen werden blockiert;
    andere Abweichungen müssen vom Verkäufer geprüft werden.
    """

    def validate(self, data: AgentInput, reply: AgentReply) -> ValidationResult:
        if not isinstance(data, AgentInput) or not isinstance(reply, AgentReply):
            raise TypeError("AgentInput und AgentReply erforderlich.")

        issues: list[ValidationIssue] = []
        agent = AGENT_REGISTRY.get(reply.agent)
        if agent is None:
            issues.append(ValidationIssue("unknown_agent", "Unbekannter Spezialagent."))
            return ValidationResult(reply.agent, DRAFT_BLOCK, SUGGESTION_BLOCK, None, tuple(issues))

        # Die Referenz wird aus *denselben validierten Produktdaten* erneut
        # konstruiert – kein LLM und keine Vertrauenserhöhung durch Metadaten.
        reference = agent.respond(data, llm=None)
        draft_ok = (
            reply.draft == reference.draft
            and reply.facts_used == reference.facts_used
            and reply.missing_fields == reference.missing_fields
        )
        if not draft_ok:
            issues.append(ValidationIssue(
                "draft_mismatch", "Entwurf oder verwendete Fakten weichen von der Vorlage ab."
            ))

        # Beschreibung gilt als unvertrauenswürdig. Die Informationsstrategie
        # zitiert sie wörtlich; verdächtige Inhalte dürfen nicht als sichere
        # Basisantwort weitergereicht werden.
        if "description" in reference.facts_used and data.product.description:
            if _INJECTION.search(data.product.description):
                draft_ok = False
                issues.append(ValidationIssue(
                    "untrusted_description", "Produktbeschreibung enthält Steueranweisungen."
                ))

        if _COMMITMENT.search(reply.draft) or _UNAUTHORIZED_DELIVERY.search(reply.draft):
            draft_ok = False
            issues.append(ValidationIssue("unsafe_draft_claim", "Entwurf enthält eine Zusage oder Liefergarantie."))

        suggestion_status = SUGGESTION_NONE
        candidate = reply.llm_suggestion
        if candidate is not None:
            if not isinstance(candidate, str) or not candidate.strip():
                suggestion_status = SUGGESTION_BLOCK
                issues.append(ValidationIssue("empty_llm_text", "LLM-Vorschlag ist leer oder ungültig."))
            elif reply.agent == "negotiation":
                suggestion_status = SUGGESTION_BLOCK
                issues.append(ValidationIssue("negotiation_llm_disabled", "Preisverhandlungen dürfen keine freie LLM-Antwort verwenden."))
            else:
                risky = self._candidate_risks(data, candidate, reference.draft)
                if risky:
                    issues.extend(risky)
                    suggestion_status = SUGGESTION_BLOCK
                elif candidate == reference.draft and draft_ok:
                    suggestion_status = SUGGESTION_PASS
                else:
                    suggestion_status = SUGGESTION_REVIEW
                    issues.append(ValidationIssue(
                        "semantic_check_unavailable",
                        "Eine freie Umformulierung kann mit Regeln nicht vollständig geprüft werden.",
                    ))

        return ValidationResult(
            agent=reply.agent,
            draft_status=DRAFT_PASS if draft_ok else DRAFT_BLOCK,
            suggestion_status=suggestion_status,
            checked_draft=reference.draft if draft_ok else None,
            issues=tuple(issues),
        )

    @staticmethod
    def _candidate_risks(data: AgentInput, candidate: str, reference: str) -> list[ValidationIssue]:
        problems: list[ValidationIssue] = []
        if _INJECTION.search(candidate):
            problems.append(ValidationIssue("prompt_injection", "LLM-Text enthält Steueranweisungen."))
        if _COMMITMENT.search(candidate):
            problems.append(ValidationIssue("unauthorized_commitment", "Unerlaubte Zusage erkannt."))
        if _UNAUTHORIZED_DELIVERY.search(candidate):
            problems.append(ValidationIssue("delivery_promise", "Unbelegte Versandkosten oder Liefergarantie."))

        if _numbers(candidate) - _numbers(reference):
            problems.append(ValidationIssue("new_number", "Neue Zahlen sind nicht durch die Antwortvorlage belegt."))
        if data.product.availability is None and _AVAILABILITY_ASSERTION.search(candidate):
            problems.append(ValidationIssue("unknown_availability", "Verfügbarkeit wurde nicht bestätigt."))
        if data.product.shipping_available is None and _SHIPPING_ASSERTION.search(candidate):
            problems.append(ValidationIssue("unknown_shipping", "Versand wurde nicht bestätigt."))
        if data.product.shipping_available is False and re.search(
            r"\b(?:versand\s+ist\s+möglich|ich\s+(?:versende|verschicke))\b",
            candidate,
            re.IGNORECASE,
        ):
            problems.append(ValidationIssue("contradictory_shipping", "Versand widerspricht den Produktdaten."))
        return problems
