"""Klare Schnittstelle: Django-Anzeige -> unabhängige Agenten-Pipeline.

Keine Django-Imports in agent_system. Kein automatischer Versand.
"""
from __future__ import annotations

from dataclasses import dataclass

from agent_system.inputs import AgentInput, CustomerRequest, ProductContext
from agent_system.pipeline import AgentPipeline, PipelineResult


@dataclass(frozen=True)
class BridgeOutput:
    """Das Ergebnis ist ein *privater* Verkäuferentwurf, nie eine gesendete Nachricht."""

    result: PipelineResult

    @property
    def requires_attention(self) -> bool:
        return (
            self.result.route.needs_clarification
            or any(check.draft_status == "blocked" for check in self.result.validation)
            or bool(self.result.audit and any(
                issue.code in {"router_error", "agent_execution_error", "agent_unavailable"}
                for issue in self.result.audit
            ))
        )


def listing_to_agent_input(listing, message: str) -> AgentInput:
    """Kein 'is_active -> available': aktive Anzeige beweist keine Verfügbarkeit.

    Fehlen Informationen, liefert das Modell None statt einen erfundenen Wert.
    """
    return AgentInput(
        product=ProductContext(
            listing_id=listing.pk,
            title=listing.title,
            description=listing.description or None,
            condition=listing.get_condition_display(),
            price_eur=listing.price,
            shipping_available=listing.shipping_available,
            pickup_available=listing.pickup_available,
            location=listing.location or None,
            is_negotiable=listing.is_negotiable,
            availability=None,
        ),
        request=CustomerRequest(message),
    )


def generate_private_draft(listing, message: str, *, use_llm: bool = False) -> BridgeOutput:
    """Synchroner lokaler MVP-Prototyp. Kein API-Aufruf bei use_llm=False."""
    data = listing_to_agent_input(listing, message)
    pipeline = AgentPipeline(offline=not use_llm)
    return BridgeOutput(pipeline.run(data))
