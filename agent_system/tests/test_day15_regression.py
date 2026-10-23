"""Tag 15: Fachliche Regression nach der 40-Fall-Evaluation von Tag 14."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_system.evaluation import load_cases, run_suite
from agent_system.inputs import AgentInput
from agent_system.pipeline import AgentPipeline
from agent_system.router import route_by_rules
from agent_system.tag15_compare import compare, load_summary


ADDITIONAL = Path(__file__).resolve().parents[1] / "examples" / "tag15_additional_scenarios.json"
BASELINE = Path("evaluation_reports/tag15_before/report.json")
AFTER = Path("evaluation_reports/tag15_after/report.json")


def sample(question: str, **overrides) -> AgentInput:
    product = {
        "title": "ThinkPad", "description": "16 GB RAM, Baujahr 2021.",
        "price_eur": "220.00", "is_negotiable": False,
        "shipping_available": True, "pickup_available": True,
        "availability": None,
    }
    product.update(overrides)
    return AgentInput.from_dict({"product": product, "request": {"message": question}})


class RouterRegressionsTests(unittest.TestCase):
    def assert_agents(self, question: str, names: set[str]):
        self.assertEqual(set(route_by_rules(sample(question)).agents), names)

    def test_verkauft(self):
        self.assert_agents("Ist das Gerät bereits verkauft?", {"information"})

    def test_reserviert(self):
        self.assert_agents("Ist der Artikel reserviert?", {"information"})

    def test_reservierung(self):
        self.assert_agents("Gibt es eine Reservierung?", {"information"})

    def test_ist_schon_weg(self):
        self.assert_agents("Ist das Gerät schon weg?", {"information"})

    def test_wie_alt(self):
        self.assert_agents("Wie alt ist der Laptop?", {"information"})

    def test_baujahr(self):
        self.assert_agents("Welches Baujahr hat der Laptop?", {"information"})

    def test_neue_preisvariante(self):
        self.assert_agents("Wären 150 € für dich in Ordnung?", {"negotiation"})

    def test_multiple(self):
        self.assert_agents("Ist er reserviert, kann ich abholen und wären 100 Euro okay?",
                           {"information", "negotiation", "logistics"})

    def test_off_topic_bleibt_unklar(self):
        decision = route_by_rules(sample("Hallo, schönen Tag!"))
        self.assertEqual(decision.agents, ())
        self.assertTrue(decision.needs_clarification)

    def test_keine_fehlklassifikation_bei_wortteil(self):
        self.assert_agents("Das Wort unverkauft ist ungewöhnlich.", set())


class PipelineRegressionsTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = AgentPipeline(offline=True)

    def test_verfuegbarkeit_unbekannt_wird_nicht_erfunden(self):
        result = self.pipeline.run(sample("Ist das Gerät verkauft?"))
        self.assertIn("keine bestätigte Angabe", result.combined_draft)
        self.assertEqual(result.review_status, "seller_review_required")

    def test_reservierung_explizit(self):
        result = self.pipeline.run(sample("Ist das Gerät reserviert?", availability="reserved"))
        self.assertIn("reserviert", result.combined_draft)
        self.assertEqual(result.route.agents, ("information",))

    def test_konflikt_haelt_nur_betroffenen_agent_zurueck(self):
        result = self.pipeline.run(sample(
            "Ist der Artikel reserviert, und was ist der letzte Preis?",
            description="Bereits verkauft.", availability="reserved",
        ))
        self.assertEqual(set(result.route.agents), {"information", "negotiation"})
        self.assertIn("zur Sicherheitsprüfung zurückgehalten", result.combined_draft)
        self.assertIn("220,00 €", result.combined_draft)
        self.assertIn("availability_conflict", {i.code for i in result.audit})

    def test_preisvorschlag_keine_zusage(self):
        result = self.pipeline.run(sample("Wären 150 Euro okay?"))
        self.assertEqual(result.route.agents, ("negotiation",))
        self.assertIn("keine Zusage", result.combined_draft)
        self.assertIn("220,00 €", result.combined_draft)
        self.assertNotIn("ich akzeptiere", result.combined_draft.casefold())


class EvalRegressionsTests(unittest.TestCase):
    def test_alte_40_szenarien(self):
        base, cases = load_cases()
        report = run_suite(base, cases, offline=True)
        self.assertEqual(report["summary"]["count"], 40)
        self.assertEqual(report["summary"]["all_checks_passed"], 40)
        self.assertEqual(report["summary"]["route_exact_pct"], 100.0)

    def test_18_neue_zusaetzliche_szenarien(self):
        base, cases = load_cases(ADDITIONAL)
        report = run_suite(base, cases, offline=True)
        self.assertEqual(report["summary"]["count"], 18)
        self.assertEqual(report["summary"]["all_checks_passed"], 18)

    def test_baseline_vorher_nachher(self):
        old, new = load_summary(BASELINE), load_summary(AFTER)
        self.assertEqual(old["all_checks_passed"], 36)
        self.assertEqual(new["all_checks_passed"], 40)
        self.assertIn("90.0 % -> 100.0 %", compare(old, new))

    def test_vergleich_verhindert_verschiedene_fallzahlen(self):
        left = {"count": 40}
        right = {"count": 18}
        with self.assertRaisesRegex(ValueError, "Unterschiedliche Fallzahlen"):
            compare(left, right)

    def test_nicht_valider_bericht_abgelehnt(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.json"
            p.write_text(json.dumps({"summary": {}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_summary(p)


if __name__ == "__main__":
    unittest.main()
