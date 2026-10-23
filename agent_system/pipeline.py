"""Verbindet den Tag-8-Router mit den Spezialagenten von Tag 9–11.

Nur Ausgabe von ENTWÜRFEN; weder Django-Zugriff noch Versand noch Preisaktion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .agents import AGENT_REGISTRY, AgentReply
from .inputs import AgentInput
from .ollama_client import OllamaClient
from .router import Orchestrator, RouteDecision

CLARIFICATION = (
    "Welche Information benötigst du zum Artikel genau – "
    "Produkteigenschaften, Preis oder Versand/Abholung?"
)


@dataclass(frozen=True, slots=True)
class PipelineResult:
    route: RouteDecision
    replies: tuple[AgentReply, ...]
    combined_draft: str
    review_status: str = "seller_review_required"
    factual_validation: str = "not_implemented_until_day_12"

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": self.route.to_dict(),
            "replies": [reply.to_dict() for reply in self.replies],
            "combined_draft": self.combined_draft,
            "review_status": self.review_status,
            "factual_validation": self.factual_validation,
        }


class AgentPipeline:
    """Routerauswahl -> spezialisierte Agenten -> kombinierter Basisentwurf."""

    def __init__(
        self,
        *,
        router: Orchestrator | None = None,
        llm: OllamaClient | None = None,
        offline: bool = False,
    ) -> None:
        self.llm = None if offline else (llm or OllamaClient())
        self.router = router or Orchestrator(
            llm=self.llm, use_llm=not offline
        )

    def run(self, data: AgentInput) -> PipelineResult:
        if not isinstance(data, AgentInput):
            raise TypeError("AgentInput erforderlich.")
        decision = self.router.route(data)
        if decision.needs_clarification:
            return PipelineResult(decision, (), CLARIFICATION)

        # Bei Routing-Fallback keine weiteren LLM-Aufrufe an einen mutmaßlich
        # nicht erreichbaren Server versuchen.
        answer_llm = self.llm if decision.source == "llm" else None
        replies = tuple(
            AGENT_REGISTRY[agent_name].respond(data, llm=answer_llm)
            for agent_name in decision.agents
        )
        # LLM-Vorschläge ausdrücklich NICHT in den kombinierten Entwurf mischen.
        combined = "\n\n".join(reply.draft for reply in replies)
        return PipelineResult(decision, replies, combined)
