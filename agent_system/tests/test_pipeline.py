"""Gemeinsame End-to-End-Tests für Router und drei Agenten, ohne Ollama."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from agent_system.agents import AGENT_REGISTRY
from agent_system.agents_demo import main
from agent_system.inputs import AgentInput
from agent_system.pipeline import AgentPipeline, CLARIFICATION
from agent_system.router import RouteDecision
from agent_system.tests.test_agents import FakeLLM, make_data


class PipelineTests(unittest.TestCase):
    def pipeline(self):
        return AgentPipeline(offline=True)

    def test_ein_information_agent(self):
        result = self.pipeline().run(make_data("Wie ist der Zustand?"))
        self.assertEqual(result.route.agents, ("information",))
        self.assertEqual(len(result.replies), 1)
        self.assertIn("Gut", result.combined_draft)

    def test_ein_negotiation_agent(self):
        result = self.pipeline().run(make_data("Letzter Preis?"))
        self.assertEqual(result.route.agents, ("negotiation",))
        self.assertIn("keine Zusage", result.combined_draft)

    def test_ein_logistics_agent(self):
        result = self.pipeline().run(make_data("Versand möglich?"))
        self.assertEqual(result.route.agents, ("logistics",))
        self.assertIn("Versand möglich", result.combined_draft)

    def test_alle_drei_agenten_gemeinsam(self):
        data = make_data("Wie ist der Zustand, ist Versand möglich und wäre 100 Euro okay?")
        result = self.pipeline().run(data)
        self.assertEqual(set(result.route.agents), set(AGENT_REGISTRY))
        self.assertEqual(len(result.replies), 3)
        self.assertIn("Gut", result.combined_draft)
        self.assertIn("220,00 €", result.combined_draft)
        self.assertIn("Versand möglich", result.combined_draft)
        self.assertIn("keine Zusage", result.combined_draft)

    def test_gegentangebot_waere_als_verhandlung(self):
        result = self.pipeline().run(make_data("Wäre 100 Euro okay?"))
        self.assertEqual(result.route.agents, ("negotiation",))

    def test_alle_drei_ohne_llm_vorschlag(self):
        result = self.pipeline().run(make_data("Zustand, Versand und Rabatt?"))
        self.assertTrue(all(x.llm_suggestion is None for x in result.replies))

    def test_mehrere_agenten_zwei(self):
        result = self.pipeline().run(make_data("Wie ist der Zustand und Versand?"))
        self.assertEqual(set(result.route.agents), {"information", "logistics"})

    def test_reihenfolge_durch_router(self):
        class RouterStub:
            def route(self, data):
                return RouteDecision(("information", "logistics"), "Test", False, "rules")
        result = AgentPipeline(router=RouterStub(), offline=True).run(make_data("Hallo"))
        self.assertEqual([r.agent for r in result.replies], ["information", "logistics"])

    def test_leere_frage_ist_bereits_durch_inputmodell_verboten(self):
        with self.assertRaises(ValueError):
            make_data(" ")

    def test_unbekanntes_anliegen_frage(self):
        result = self.pipeline().run(make_data("Hallo!"))
        self.assertTrue(result.route.needs_clarification)
        self.assertEqual(result.replies, ())
        self.assertEqual(result.combined_draft, CLARIFICATION)

    def test_nie_automatisch_freigegeben(self):
        result = self.pipeline().run(make_data("Ist Versand möglich?"))
        self.assertEqual(result.review_status, "seller_review_required")
        self.assertEqual(result.factual_validation, "template_and_risk_rules_only")
        self.assertEqual(result.validation[0].draft_status, "passed_template_checks")

    def test_llm_alternative_nicht_in_combined_draft(self):
        class RouterStub:
            def route(self, data):
                return RouteDecision(("information",), "Test", False, "llm")
        llm = FakeLLM("Frei erfundene Zusatzinformation")
        result = AgentPipeline(router=RouterStub(), llm=llm).run(make_data("Zustand?"))
        self.assertIn("erfundene", result.replies[0].llm_suggestion)
        self.assertNotIn("erfundene", result.combined_draft)
        self.assertIn("Gut", result.combined_draft)

    def test_negotiation_auch_mit_llm_ohne_versprechen(self):
        class RouterStub:
            def route(self, data):
                return RouteDecision(("negotiation",), "Test", False, "llm")
        llm = FakeLLM("Ich nehme die 1 Euro!")
        result = AgentPipeline(router=RouterStub(), llm=llm).run(make_data("Rabatt?"))
        self.assertEqual(llm.calls, [])
        self.assertIsNone(result.replies[0].llm_suggestion)
        self.assertIn("keine Zusage", result.combined_draft)

    def test_llm_aufrufe_mehrere(self):
        class RouterStub:
            def route(self, data):
                return RouteDecision(("information", "logistics"), "Test", False, "llm")
        llm = FakeLLM()
        result = AgentPipeline(router=RouterStub(), llm=llm).run(make_data("Zustand und Versand?"))
        self.assertEqual(len(llm.calls), 2)
        self.assertEqual(len(result.replies), 2)

    def test_fallback_vermeidet_weitere_llm_aufrufe(self):
        class RouterStub:
            def route(self, data):
                return RouteDecision(("information",), "Regeln", False, "fallback", "Timeout")
        llm = FakeLLM()
        result = AgentPipeline(router=RouterStub(), llm=llm).run(make_data("Zustand?"))
        self.assertEqual(llm.calls, [])
        self.assertIn("Gut", result.combined_draft)

    def test_route_fallback_bleibt_sichtbar(self):
        class RouterStub:
            def route(self, data):
                return RouteDecision(("information",), "Regeln", False, "fallback", "Timeout")
        result = AgentPipeline(router=RouterStub(), offline=True).run(make_data("Zustand?"))
        self.assertEqual(result.to_dict()["route"]["source"], "fallback")
        self.assertEqual(result.route.warning, "Timeout")

    def test_falsche_eingabe_abgelehnt(self):
        with self.assertRaises(TypeError):
            self.pipeline().run({"question": "Hallo"})

    def test_input_wird_nicht_modifiziert(self):
        data = make_data("Versand und Rabatt?")
        original = data.to_dict()
        self.pipeline().run(data)
        self.assertEqual(data.to_dict(), original)

    def test_result_serialisierbar(self):
        result = self.pipeline().run(make_data("Wie ist der Zustand und ist Versand möglich?"))
        dumped = json.dumps(result.to_dict(), ensure_ascii=False)
        self.assertIn("combined_draft", dumped)

    def test_keine_fremde_agentenstruktur(self):
        result = self.pipeline().run(make_data("Verfügbar?"))
        self.assertTrue(all(x.agent in AGENT_REGISTRY for x in result.replies))


class DemoTests(unittest.TestCase):
    def test_demo_offline(self):
        buff = io.StringIO()
        with redirect_stdout(buff):
            code = main(["--offline", "--frage", "Zustand und Versand?"])
        self.assertEqual(code, 0)
        self.assertIn('"review_status": "seller_review_required"', buff.getvalue())

    def test_demo_vier_beispiele(self):
        buff = io.StringIO()
        with redirect_stdout(buff):
            code = main(["--offline", "--beispiele"])
        self.assertEqual(code, 0)
        self.assertIn("[Information]", buff.getvalue())
        self.assertIn("[Negotiation]", buff.getvalue())
        self.assertIn("[Logistics]", buff.getvalue())
        self.assertIn("[Alle drei]", buff.getvalue())

    def test_demo_leere_frage(self):
        buff = io.StringIO()
        with redirect_stdout(buff):
            code = main(["--offline", "--frage", " "])
        self.assertEqual(code, 1)
        self.assertIn("EINGABEFEHLER", buff.getvalue())

    def test_demo_ungueltige_datei(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "invalid.json"
            p.write_text('{"broken": ', encoding="utf-8")
            buff = io.StringIO()
            with redirect_stdout(buff):
                code = main(["--offline", "--datei", str(p)])
            self.assertEqual(code, 1)
            self.assertIn("EINGABEFEHLER", buff.getvalue())


if __name__ == "__main__":
    unittest.main()
