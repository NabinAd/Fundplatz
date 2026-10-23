"""Tag 14: Evaluationsmechanik und manuell kuratierte Fälle testen."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from agent_system.evaluation import (
    DEFAULT_CASES, EvaluationDataError, evaluate_case, load_cases,
    main, markdown_report, run_suite, summarize, write_report,
)
from agent_system.pipeline import AgentPipeline


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product, cls.scenarios = load_cases()

    def test_mindestens_30_szenarien(self):
        self.assertGreaterEqual(len(self.scenarios), 30)

    def test_40_faelle_aus_zehn_kategorien(self):
        self.assertEqual(len(self.scenarios), 40)
        self.assertEqual(sorted(Counter(x["category"] for x in self.scenarios).values()), [4] * 10)

    def test_ids_eindeutig(self):
        self.assertEqual(len({c["id"] for c in self.scenarios}), len(self.scenarios))

    def test_alle_szenarien_sind_validiert(self):
        self.assertIn("price_eur", self.product)
        self.assertTrue(all(c["expected_agents"] is not None for c in self.scenarios))

    def test_duplikat_wird_verworfen(self):
        with tempfile.TemporaryDirectory() as temp:
            raw = json.loads(DEFAULT_CASES.read_text(encoding="utf-8"))
            raw["scenarios"].append(copy.deepcopy(raw["scenarios"][0]))
            path = Path(temp) / "duplicate.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(EvaluationDataError, "Doppelte Fall-ID"):
                load_cases(path)

    def test_ungueltiger_agent_wird_verworfen(self):
        with tempfile.TemporaryDirectory() as temp:
            raw = json.loads(DEFAULT_CASES.read_text(encoding="utf-8"))
            raw["scenarios"][0]["expected_agents"] = ["magischer_agent"]
            path = Path(temp) / "wrong.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(EvaluationDataError, "unbekannter Agent"):
                load_cases(path)

    def test_negativer_preis_wird_verworfen(self):
        with tempfile.TemporaryDirectory() as temp:
            raw = json.loads(DEFAULT_CASES.read_text(encoding="utf-8"))
            raw["scenarios"][0]["product_overrides"]["price_eur"] = "-10.00"
            path = Path(temp) / "negative.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(EvaluationDataError, "ungültige Eingabe"):
                load_cases(path)

    def test_ungueltiges_json_wird_abgelehnt(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "broken.json"
            path.write_text("{kaputt", encoding="utf-8")
            with self.assertRaises(EvaluationDataError):
                load_cases(path)

    def test_leere_falldatei_wird_abgelehnt(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "empty.json"
            path.write_text('{"version":1,"base_product":{},"scenarios":[]}', encoding="utf-8")
            with self.assertRaises(EvaluationDataError):
                load_cases(path)


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.cases = load_cases()
        cls.report = run_suite(cls.base, cls.cases, offline=True)

    def test_alle_40_offline_durchfuehrbar(self):
        self.assertEqual(len(self.report["cases"]), 40)
        self.assertTrue(all(case["error"] is None for case in self.report["cases"]))

    def test_auswertung_unabhaengig_vom_router_label(self):
        modified = copy.deepcopy(self.cases[0])
        modified["expected_agents"] = ["negotiation"]
        modified["expected_text_fragments"] = []
        row = evaluate_case(self.base, modified, AgentPipeline(offline=True))
        self.assertFalse(row["route_exact"])

    def test_router_label_definiert_keine_erwartung(self):
        result = next(c for c in self.report["cases"] if c["id"] == "A03")
        self.assertEqual(result["expected_agents"], ["information"])
        self.assertEqual(result["source"], "rules")
        self.assertIn(result["actual_agents"], ([], ["information"]))

    def test_unbekannte_daten_werden_nicht_als_nein_gewertet(self):
        row = next(c for c in self.report["cases"] if c["id"] == "F03")
        self.assertTrue(row["text_ok"])

    def test_bekannter_versandkonflikt_wird_blockiert(self):
        row = next(c for c in self.report["cases"] if c["id"] == "W01")
        self.assertTrue(row["audit_ok"])
        self.assertTrue(row["blocked_ok"])

    def test_injection_aus_kundentext_wird_protokolliert(self):
        row = next(c for c in self.report["cases"] if c["id"] == "P01")
        self.assertIn("untrusted_customer_instruction", row["actual_audit_codes"])

    def test_freigabe_immer_erforderlich(self):
        self.assertTrue(all(c["review_required"] for c in self.report["cases"]))

    def test_keine_erkannte_riskante_zusage(self):
        self.assertFalse(any(c["unsafe_commitment"] for c in self.report["cases"]))

    def test_keine_unbelegten_zahlen_im_offline_entwurf(self):
        self.assertFalse(any(c["unexpected_numbers"] for c in self.report["cases"]))

    def test_qualitaetsabweichungen_nicht_als_crash(self):
        summary = self.report["summary"]
        self.assertEqual(summary["count"], 40)
        self.assertGreaterEqual(summary["all_checks_passed"], 1)
        self.assertLessEqual(summary["all_checks_passed"], 40)

    def test_precision_recall_sind_getrennt(self):
        summary = self.report["summary"]
        self.assertIn("agent_precision_pct", summary)
        self.assertIn("agent_recall_pct", summary)
        self.assertIn("route_exact_pct", summary)

    def test_blockierung_denominator_nur_relevante_faelle(self):
        summary = self.report["summary"]
        self.assertEqual(summary["blocking_expected_case_count"], 5)
        self.assertEqual(summary["audit_expected_case_count"], 8)

    def test_leere_auswertung_ist_fehler(self):
        with self.assertRaises(EvaluationDataError):
            summarize([], "offline")

    def test_markdown_enthaelt_abweichungen(self):
        content = markdown_report(self.report)
        self.assertIn("# Fundplatz", content)
        self.assertIn("A03", content)
        self.assertIn("Aussagegrenzen", content)

    def test_bericht_dateien_sind_korrekt(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_report(self.report, Path(tmp))
            for name in ("report.csv", "report.json", "report.md"):
                self.assertTrue((Path(tmp) / name).exists())
            parsed = json.loads((Path(tmp) / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(parsed["summary"]["count"], 40)
            self.assertEqual(len(parsed["cases"]), 40)

    def test_cli_limit_drei(self):
        with tempfile.TemporaryDirectory() as tmp:
            ret = main(["--mode", "offline", "--limit", "3", "--out-dir", tmp])
            self.assertEqual(ret, 0)
            parsed = json.loads((Path(tmp) / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(parsed["summary"]["count"], 3)

    def test_cli_je_ein_fall_aus_jeder_kategorie(self):
        with tempfile.TemporaryDirectory() as tmp:
            ret = main(["--per-category", "1", "--out-dir", tmp])
            self.assertEqual(ret, 0)
            parsed = json.loads((Path(tmp) / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(parsed["summary"]["count"], 10)
            self.assertEqual(len(parsed["summary"]["categories"]), 10)

    def test_cli_nur_eine_kategorie(self):
        with tempfile.TemporaryDirectory() as tmp:
            ret = main(["--category", "negotiation", "--out-dir", tmp])
            self.assertEqual(ret, 0)
            parsed = json.loads((Path(tmp) / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(parsed["summary"]["count"], 4)


if __name__ == "__main__":
    unittest.main()
