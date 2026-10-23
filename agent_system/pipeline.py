"""Router -> Spezialagenten -> konservative Validierung -> sicherer Entwurf.

Keine automatische Freigabe, kein Versand, keine Änderung von Produktdaten.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .agents import AGENT_REGISTRY, AgentReply
from .inputs import AgentInput
from .ollama_client import OllamaClient
from .router import Orchestrator, RouteDecision
from .validation import DRAFT_BLOCK, ResponseValidator, ValidationResult

CLARIFICATION = (
    "Welche Information benötigst du zum Artikel genau – "
    "Produkteigenschaften, Preis oder Versand/Abholung?"
)
BLOCKED_NOTICE = "Ein Antwortteil wurde zur Sicherheitsprüfung zurückgehalten."


@dataclass(frozen=True, slots=True)
class PipelineResult:
    route: RouteDecision
    replies: tuple[AgentReply, ...]
    combined_draft: str
    review_status: str = "seller_review_required"
    factual_validation: str = "template_and_risk_rules_only"
    validation: tuple[ValidationResult, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": self.route.to_dict(),
            "replies": [reply.to_dict() for reply in self.replies],
            "combined_draft": self.combined_draft,
            "review_status": self.review_status,
            "factual_validation": self.factual_validation,
            "validation": [item.to_dict() for item in self.validation],
        }


class AgentPipeline:
    """End-to-End-Durchlauf. Nur geprüfte Vorlagen in combined_draft."""

    def __init__(
        self,
        *,
        router: Orchestrator | None = None,
        llm: OllamaClient | None = None,
        offline: bool = False,
        validator: ResponseValidator | None = None,
    ) -> None:
        self.llm = None if offline else (llm or OllamaClient())
        self.router = router or Orchestrator(llm=self.llm, use_llm=not offline)
        self.validator = validator or ResponseValidator()

    def run(self, data: AgentInput) -> PipelineResult:
        if not isinstance(data, AgentInput):
            raise TypeError("AgentInput erforderlich.")
        decision = self.router.route(data)
        if decision.needs_clarification:
            return PipelineResult(
                decision, (), CLARIFICATION, factual_validation="clarification_only"
            )

        # Bei Routing-Fallback keine weiteren Modellaufrufe an einen vermutlich
        # nicht erreichbaren Ollama-Server durchführen.
        answer_llm = self.llm if decision.source == "llm" else None
        replies = tuple(
            AGENT_REGISTRY[agent_name].respond(data, llm=answer_llm)
            for agent_name in decision.agents
        )
        checks = tuple(self.validator.validate(data, reply) for reply in replies)

        # NIE eine ungeprüfte LLM-Umformulierung in den Entwurf übernehmen.
        # Bei einer riskanten Produktbeschreibung wird der betroffene Teil
        # nicht angezeigt, bis ein Verkäufer die Fakten bereinigt hat.
        combined = "\n\n".join(
            check.checked_draft if check.draft_status != DRAFT_BLOCK else BLOCKED_NOTICE
            for check in checks
        )
        return PipelineResult(decision, replies, combined, validation=checks)
