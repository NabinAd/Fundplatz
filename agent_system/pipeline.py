"""Router -> Eingabe-Audit -> Spezialagenten -> Validierung -> sicherer Entwurf.

Tag 13: Intent-Gegenprüfung, erkennbare Datenkonflikte und partielle Ausfälle.
Kein automatischer Versand, kein Preisabschluss, keine Produktänderung.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .agents import AGENT_REGISTRY, AgentReply
from .inputs import AgentInput
from .ollama_client import OllamaClient
from .router import Orchestrator, RouteDecision
from .safety import AuditIssue, inspect_input, reconcile_route
from .validation import DRAFT_BLOCK, ResponseValidator, ValidationIssue, ValidationResult

CLARIFICATION = (
    "Welche Information benötigst du zum Artikel genau – "
    "Produkteigenschaften, Preis oder Versand/Abholung?"
)
BLOCKED_NOTICE = "Ein Antwortteil wurde zur Sicherheitsprüfung zurückgehalten."
ERROR_NOTICE = "Ein Antwortteil konnte nicht erstellt werden und benötigt manuelle Bearbeitung."


@dataclass(frozen=True, slots=True)
class PipelineResult:
    route: RouteDecision
    replies: tuple[AgentReply, ...]
    combined_draft: str
    review_status: str = "seller_review_required"
    factual_validation: str = "template_and_risk_rules_only"
    validation: tuple[ValidationResult, ...] = ()
    audit: tuple[AuditIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": self.route.to_dict(),
            "replies": [reply.to_dict() for reply in self.replies],
            "combined_draft": self.combined_draft,
            "review_status": self.review_status,
            "factual_validation": self.factual_validation,
            "validation": [item.to_dict() for item in self.validation],
            "audit": [item.to_dict() for item in self.audit],
        }


class AgentPipeline:
    """End-to-End-Durchlauf mit transparenter Eingabe- und Ausfallauditierung."""

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

        audit = list(inspect_input(data))
        try:
            decision = self.router.route(data)
            decision, route_issues = reconcile_route(data, decision)
            audit.extend(route_issues)
        except Exception:
            # Ein fehlerhafter Router darf niemals zu automatischer Ausgabe
            # oder zu unkontrollierten weiteren LLM-Aufrufen führen.
            audit.append(AuditIssue(
                "router_error", "Router konnte nicht sicher ausgeführt werden; manuelle Prüfung erforderlich."
            ))
            return PipelineResult(
                RouteDecision((), "Routerfehler; Rückfrage notwendig.", True, "fallback",
                              "Routerfehler: keine Agenten ausgeführt."),
                (), CLARIFICATION, factual_validation="clarification_only", audit=tuple(audit),
            )
        if decision.needs_clarification:
            return PipelineResult(
                decision, (), CLARIFICATION, factual_validation="clarification_only", audit=tuple(audit),
            )

        # Eindeutige widersprüchliche Produktangaben blockieren die betroffenen
        # Agenten-Ausgaben, ohne unbeeinflusste Ausgaben zu unterdrücken.
        held_agents = {agent for issue in audit
                       if issue.code in {"shipping_conflict", "pickup_conflict", "availability_conflict", "untrusted_product_instruction"}
                       for agent in issue.affected_agents}

        # Bei LLM-Ausfall/Regelmodus keine weiteren LLM-Aufrufe starten.
        answer_llm = self.llm if decision.source == "llm" else None
        replies: list[AgentReply] = []
        checks: list[ValidationResult] = []
        visible_parts: list[str] = []
        for agent_name in decision.agents:
            agent = AGENT_REGISTRY.get(agent_name)
            if agent is None:
                audit.append(AuditIssue("agent_unavailable", "Spezialagent fehlt: " + agent_name, (agent_name,)))
                visible_parts.append(ERROR_NOTICE)
                continue
            try:
                reply = agent.respond(data, llm=answer_llm)
                check = self.validator.validate(data, reply)
            except Exception:
                # Die übrigen Agenten können weiterarbeiten. Niemals rohe
                # Fehlermeldungen oder nicht geprüfte Teilentwürfe veröffentlichen.
                audit.append(AuditIssue(
                    "agent_execution_error", "Ein Agent konnte nicht sicher ausgeführt werden: " + agent_name,
                    (agent_name,),
                ))
                visible_parts.append(ERROR_NOTICE)
                continue
            replies.append(reply)
            if agent_name in held_agents:
                check = ValidationResult(
                    agent=check.agent,
                    draft_status=DRAFT_BLOCK,
                    suggestion_status=check.suggestion_status,
                    checked_draft=None,
                    issues=check.issues + (ValidationIssue(
                        "conflicting_input_hold",
                        "Die Eingabeprüfung hat widersprüchliche oder manipulative Quelldaten erkannt.",
                    ),),
                )
            checks.append(check)
            if check.draft_status == DRAFT_BLOCK:
                visible_parts.append(BLOCKED_NOTICE)
            else:
                visible_parts.append(check.checked_draft or BLOCKED_NOTICE)

        combined = "\n\n".join(visible_parts) if visible_parts else ERROR_NOTICE
        return PipelineResult(
            decision, tuple(replies), combined,
            validation=tuple(checks), audit=tuple(audit),
        )
