"""Pure Python adapter tests: run without Django/SQLite installed."""
from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from listings.agent_bridge import generate_private_draft, listing_to_agent_input


class ListingAdapterTests(TestCase):
    def sample(self, **updates):
        data = {
            "pk": 3,
            "title": "Gaming Laptop",
            "description": "8 GB RAM",
            "price": Decimal("700.00"),
            "shipping_available": False,
            "pickup_available": True,
            "location": "",
            "is_negotiable": None,
        }
        data.update(updates)
        return SimpleNamespace(**data, get_condition_display=lambda: "Gebraucht")

    def test_unbekannte_verfuegbarkeit_bleibt_unbekannt(self):
        result = listing_to_agent_input(self.sample(), "Ist er noch verfügbar?")
        self.assertIsNone(result.product.availability)

    def test_decimal_und_boolean_unveraendert(self):
        result = listing_to_agent_input(self.sample(), "Was kostet er?")
        self.assertEqual(result.product.price_eur, Decimal("700.00"))
        self.assertIs(result.product.shipping_available, False)
        self.assertIs(result.product.pickup_available, True)
        self.assertIsNone(result.product.location)

    def test_standard_pipeline_offline(self):
        output = generate_private_draft(self.sample(), "Ist Versand möglich?")
        self.assertIn("logistics", output.result.route.agents)
        self.assertEqual(output.result.route.source, "rules")
        self.assertEqual(output.result.review_status, "seller_review_required")

    def test_llm_wird_nur_explizit_aktiviert(self):
        with patch("listings.agent_bridge.AgentPipeline") as factory:
            generate_private_draft(self.sample(), "Ist Abholung möglich?", use_llm=True)
        factory.assert_called_once_with(offline=False)
