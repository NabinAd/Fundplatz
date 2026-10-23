"""Offline-Tests für strukturierte Produkt- und Kundenangaben (Tag 7)."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path

from agent_system.demo import main
from agent_system.inputs import AgentInput, CustomerRequest, InputValidationError, ProductContext


class ProductContextTests(unittest.TestCase):
    def test_minimales_produkt(self):
        product = ProductContext.from_dict({"title": " Fahrrad "})
        self.assertEqual(product.title, "Fahrrad")
        self.assertIsNone(product.price_eur)
        self.assertIsNone(product.shipping_available)

    def test_alle_felder(self):
        product = ProductContext.from_dict({
            "listing_id": 8, "title": "Laptop", "description": "16 GB RAM",
            "condition": "Gut", "price_eur": "220.00", "shipping_available": True,
            "pickup_available": False, "location": "Frankfurt", "is_negotiable": True,
            "availability": "reserved",
        })
        self.assertEqual(product.price_eur, Decimal("220.00"))
        self.assertEqual(product.availability, "reserved")
        self.assertIs(product.pickup_available, False)

    def test_leerer_titel_abgelehnt(self):
        for title in ("", "   ", None):
            with self.subTest(title=title), self.assertRaises(InputValidationError):
                ProductContext.from_dict({"title": title})

    def test_falscher_titeltyp_abgelehnt(self):
        with self.assertRaisesRegex(InputValidationError, "Text erwartet"):
            ProductContext(title=123)

    def test_titel_maximal_120_zeichen(self):
        self.assertEqual(len(ProductContext(title="x" * 120).title), 120)
        with self.assertRaises(InputValidationError):
            ProductContext(title="x" * 121)

    def test_optionaler_beschreibungstext(self):
        self.assertIsNone(ProductContext(title="A", description="  ").description)
        self.assertEqual(ProductContext(title="A", description=" OK ").description, "OK")

    def test_beschreibung_zu_lang(self):
        with self.assertRaises(InputValidationError):
            ProductContext(title="A", description="a" * 5001)

    def test_negativer_preis_abgelehnt(self):
        with self.assertRaisesRegex(InputValidationError, "zwischen 0"):
            ProductContext(title="A", price_eur="-1.00")

    def test_ungueltiger_preis_abgelehnt(self):
        for price in ("abc", "12,50", "NaN", "Infinity", "", "1.999", "10000000"):
            with self.subTest(price=price), self.assertRaises(InputValidationError):
                ProductContext(title="A", price_eur=price)

    def test_float_preis_abgelehnt(self):
        with self.assertRaises(InputValidationError):
            ProductContext(title="A", price_eur=19.99)

    def test_preis_0_und_dezimal_als_text(self):
        self.assertEqual(ProductContext(title="A", price_eur="0").to_dict()["price_eur"], "0.00")
        self.assertEqual(ProductContext(title="A", price_eur=Decimal("19.90")).to_dict()["price_eur"], "19.90")

    def test_unbekannt_ist_nicht_false(self):
        unknown = ProductContext(title="A", shipping_available=None)
        denied = ProductContext(title="A", shipping_available=False)
        self.assertIsNone(unknown.to_dict()["shipping_available"])
        self.assertIs(denied.to_dict()["shipping_available"], False)

    def test_falscher_boolean_abgelehnt(self):
        for value in ("false", 0, 1):
            with self.subTest(value=value), self.assertRaises(InputValidationError):
                ProductContext(title="A", shipping_available=value)

    def test_verfuegbarkeit_nur_explizit(self):
        with self.assertRaises(InputValidationError):
            ProductContext(title="A", availability="yes")
        self.assertIsNone(ProductContext(title="A").availability)
        self.assertEqual(ProductContext(title="A", availability="sold").availability, "sold")

    def test_ungueltige_listing_id(self):
        for value in (0, -4, "5", True):
            with self.subTest(value=value), self.assertRaises(InputValidationError):
                ProductContext(title="A", listing_id=value)

    def test_unbekanntes_feld_erkannt(self):
        with self.assertRaisesRegex(InputValidationError, "unbekannte Felder: prise_eur"):
            ProductContext.from_dict({"title": "A", "prise_eur": "10"})

    def test_eingabe_darf_nicht_uneigentliches_objekt_sein(self):
        with self.assertRaises(InputValidationError):
            ProductContext.from_dict(["A"])


class CustomerRequestTests(unittest.TestCase):
    def test_frage_wird_getrimmt(self):
        request = CustomerRequest.from_dict({"message": "  Versand?  "})
        self.assertEqual(request.message, "Versand?")

    def test_leere_frage_verboten(self):
        with self.assertRaises(InputValidationError):
            CustomerRequest(message="  ")

    def test_zu_lange_frage(self):
        with self.assertRaises(InputValidationError):
            CustomerRequest(message="x" * 2001)

    def test_falsche_frage_typen(self):
        for value in (None, 12, False):
            with self.subTest(value=value), self.assertRaises(InputValidationError):
                CustomerRequest(message=value)

    def test_unbekanntes_feld_verboten(self):
        with self.assertRaises(InputValidationError):
            CustomerRequest.from_dict({"message": "Hallo", "seller_id": 4})


class AgentInputTests(unittest.TestCase):
    def test_minimale_eingabe(self):
        bundle = AgentInput.from_dict({"product": {"title": "Tisch"}, "request": {"message": "Wie alt?"}})
        self.assertEqual(bundle.product.title, "Tisch")
        self.assertEqual(bundle.request.message, "Wie alt?")
        self.assertIsNone(bundle.product.availability)

    def test_missing_request_wird_abgelehnt(self):
        with self.assertRaisesRegex(InputValidationError, "Pflichtfelder fehlen: request"):
            AgentInput.from_dict({"product": {"title": "A"}})

    def test_to_user_prompt_keine_fakten_erganzt(self):
        bundle = AgentInput.from_dict({"product": {"title": "Kamera"}, "request": {"message": "Ist sie verfügbar?"}})
        prompt = bundle.to_user_prompt()
        self.assertIn('"availability": null', prompt)
        self.assertIn("Ist sie verfügbar?", prompt)
        self.assertIn("null = unbekannt", prompt)

    def test_json_roundtrip(self):
        bundle = AgentInput.from_dict({"product": {"title": "A", "price_eur": "12.50", "shipping_available": False}, "request": {"message": "Versand?"}})
        clone = AgentInput.from_dict(json.loads(json.dumps(bundle.to_dict())))
        self.assertEqual(clone, bundle)

    def test_data_ist_immutabel(self):
        bundle = AgentInput.from_dict({"product": {"title": "A"}, "request": {"message": "Hi"}})
        with self.assertRaises(AttributeError):
            bundle.request.message = "Anders"

    def test_typen_notwendig(self):
        with self.assertRaises(InputValidationError):
            AgentInput(product={"title": "A"}, request=CustomerRequest("Hallo"))


class DemoTests(unittest.TestCase):
    def test_demo_nur_pruefen_ohne_ollama(self):
        example = Path(__file__).resolve().parents[1] / "examples" / "tag7_input.json"
        output = io.StringIO()
        with redirect_stdout(output):
            return_code = main(["--datei", str(example), "--nur-pruefen"])
        self.assertEqual(return_code, 0)
        self.assertIn("Validierung OK", output.getvalue())

    def test_demo_fehlerhafte_eingabe(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "bad.json"
            file.write_text('{"product": {"title": ""}, "request": {"message": ""}}', encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                return_code = main(["--datei", str(file), "--nur-pruefen"])
            self.assertEqual(return_code, 1)
            self.assertIn("EINGABEFEHLER", output.getvalue())

    def test_demo_frage_uberschreiben(self):
        example = Path(__file__).resolve().parents[1] / "examples" / "tag7_input.json"
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--datei", str(example), "--frage", "Wie ist der Zustand?", "--nur-pruefen"])
        self.assertEqual(code, 0)
        self.assertIn("Wie ist der Zustand?", output.getvalue())


if __name__ == "__main__":
    unittest.main()
