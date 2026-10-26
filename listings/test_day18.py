"""Tag 18: Verkäufer kann einen eigenen privaten Entwurf bearbeiten und speichern.

WICHTIG: Weder Freigabe noch Käuferbenachrichtigung / Versand existieren.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import SellerDraftForm
from .models import CustomerInquiry, Listing


class SellerDraftFormTests(TestCase):
    def test_gueltiger_text_wird_getrimmt(self):
        form = SellerDraftForm({"seller_draft": "  Hallo, Versand ist möglich.  "})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["seller_draft"], "Hallo, Versand ist möglich.")

    def test_leerer_text_wird_abgelehnt(self):
        for text in ("", " ", "   \n "):
            with self.subTest(text=text):
                self.assertFalse(SellerDraftForm({"seller_draft": text}).is_valid())

    def test_zu_kurzer_text_wird_abgelehnt(self):
        self.assertFalse(SellerDraftForm({"seller_draft": "1234"}).is_valid())

    def test_zu_langer_text_wird_abgelehnt(self):
        self.assertFalse(SellerDraftForm({"seller_draft": "x" * 3001}).is_valid())

    def test_genau_3000_zeichen_sind_gueltig(self):
        self.assertTrue(SellerDraftForm({"seller_draft": "x" * 3000}).is_valid())


class SellerDraftDay18Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username="owner18", password="Safe-password-18")
        cls.other = User.objects.create_user(username="other18", password="Safe-password-18")
        cls.buyer = User.objects.create_user(username="buyer18", password="Safe-password-18")
        cls.listing = Listing.objects.create(
            seller=cls.owner, title="Notebook 18", description="Ein Notebook",
            price=Decimal("245.00"), is_active=True, shipping_available=True,
        )
        cls.other_listing = Listing.objects.create(
            seller=cls.other, title="Fremde Anzeige", description="Andere",
            price=Decimal("90.00"), is_active=True,
        )
        cls.inquiry = CustomerInquiry.objects.create(
            listing=cls.listing, buyer=cls.buyer, message="Ist Versand möglich?",
            private_draft="Laut Anzeige ist Versand möglich.",
            route_source="rules", selected_agents=["logistics"],
            audit=[{"code": "notice", "message": "Preise selbst prüfen"}],
            status=CustomerInquiry.Status.REVIEW_REQUIRED,
        )
        cls.foreign = CustomerInquiry.objects.create(
            listing=cls.other_listing, buyer=cls.buyer,
            message="Frage von anderem Verkäufer",
            private_draft="Anderer privater KI-Text 839",
        )

    def edit(self, inquiry=None):
        return reverse("listings:seller_inquiry_edit", args=[(inquiry or self.inquiry).pk])

    def detail(self, inquiry=None):
        return reverse("listings:seller_inquiry_detail", args=[(inquiry or self.inquiry).pk])

    def post(self, text="Danke für die Frage. Versand wäre möglich.", **extra):
        return self.client.post(self.edit(), {"seller_draft": text, **extra})

    def test_route_existiert(self):
        self.assertIn("/entwurf/", self.edit())

    def test_anonymer_benutzer_wird_umgeleitet(self):
        self.assertEqual(self.client.get(self.edit()).status_code, 302)
        self.assertIn("/login/", self.client.get(self.edit())["Location"])
        self.assertEqual(self.post().status_code, 302)

    def test_eigentuemer_darf_editor_oeffnen(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.edit())
        self.assertContains(response, "Antwortentwurf bearbeiten")
        self.assertContains(response, "Ist Versand möglich?")
        self.assertContains(response, "Laut Anzeige ist Versand möglich.")
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_kaeuferfreundliche_vorbelegung_ki_original_bleibt_unveraendert(self):
        # Seit dem Tonfall-Update verwendet der Editor einen datengebundenen
        # Käufertext. Die technischen KI-Daten werden dadurch nicht geändert.
        self.client.force_login(self.owner)
        form = self.client.get(self.edit()).context["form"]
        draft = form.initial["seller_draft"]
        self.assertTrue(draft.startswith("Hallo!"))
        self.assertIn("Ja, Versand ist möglich.", draft)
        self.assertNotEqual(draft, self.inquiry.private_draft)
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.private_draft, "Laut Anzeige ist Versand möglich.")
        self.assertEqual(self.inquiry.seller_draft, "")

    def test_unbekannte_anfrage_404(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("listings:seller_inquiry_edit", args=[999999])).status_code, 404)

    def test_fremder_verkaeufer_bekommt_404(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.edit()).status_code, 404)
        self.assertEqual(self.post().status_code, 404)

    def test_kaeufer_bekommt_404(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(self.edit()).status_code, 404)
        self.assertEqual(self.post().status_code, 404)

    def test_verkaeufer_kann_fremde_anfrage_nicht_aendern(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.edit(self.foreign)).status_code, 404)
        self.assertEqual(self.client.post(self.edit(self.foreign), {"seller_draft": "Versuch"}).status_code, 404)
        self.foreign.refresh_from_db()
        self.assertFalse(self.foreign.seller_draft)
        self.assertIsNone(self.foreign.seller_draft_updated_at)

    def test_get_speichert_nichts(self):
        self.client.force_login(self.owner)
        self.client.get(self.edit())
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.seller_draft, "")
        self.assertIsNone(self.inquiry.seller_draft_updated_at)
        self.assertEqual(self.inquiry.status, CustomerInquiry.Status.REVIEW_REQUIRED)

    def test_speichern_erhaelt_ki_vorlage(self):
        self.client.force_login(self.owner)
        response = self.post("  Hallo! Versand ist nach Anzeige möglich.  ")
        self.assertRedirects(response, self.detail())
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.seller_draft, "Hallo! Versand ist nach Anzeige möglich.")
        self.assertEqual(self.inquiry.private_draft, "Laut Anzeige ist Versand möglich.")
        self.assertIsNotNone(self.inquiry.seller_draft_updated_at)
        self.assertEqual(self.inquiry.status, CustomerInquiry.Status.IN_PROGRESS)

    def test_kritischer_hinweis_bleibt_beim_speichern_erhalten(self):
        self.inquiry.status = CustomerInquiry.Status.NEEDS_ATTENTION
        self.inquiry.save(update_fields=["status"])
        self.client.force_login(self.owner)
        self.post("Privat geprüft, muss aber noch inhaltlich ergänzt werden")
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, CustomerInquiry.Status.NEEDS_ATTENTION)
        self.assertIsNotNone(self.inquiry.seller_draft_updated_at)

    def test_gespeicherte_fassung_erneut_anzeigen(self):
        self.client.force_login(self.owner)
        self.post("Meine überarbeitete Antwort, Version 1")
        response = self.client.get(self.edit())
        self.assertEqual(response.context["form"].initial["seller_draft"], "Meine überarbeitete Antwort, Version 1")

    def test_zweite_bearbeitung_aktualisiert_text(self):
        self.client.force_login(self.owner)
        self.post("Erste gültige Fassung")
        self.post("Zweite gültige Fassung")
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.seller_draft, "Zweite gültige Fassung")
        self.assertIsNotNone(self.inquiry.seller_draft_updated_at)

    def test_invalid_text_keine_aenderungen(self):
        self.client.force_login(self.owner)
        for text in ("    ", "abc", "x" * 3001):
            with self.subTest(length=len(text)):
                response = self.post(text)
                self.assertEqual(response.status_code, 400)
                self.assertContains(response, "Entwurf privat speichern", status_code=400)
                self.inquiry.refresh_from_db()
                self.assertEqual(self.inquiry.seller_draft, "")
                self.assertIsNone(self.inquiry.seller_draft_updated_at)
                self.assertEqual(self.inquiry.status, CustomerInquiry.Status.REVIEW_REQUIRED)

    def test_nur_ein_formularfeld_ist_schreibbar(self):
        self.client.force_login(self.owner)
        self.post("Seriöser eigener Text", private_draft="FÄLSCHUNG", status="approved",
                  buyer=str(self.other.pk), listing=str(self.other_listing.pk),
                  route_source="llm", selected_agents='["negotiation"]',
                  audit='[{"code":"fake"}]')
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.seller_draft, "Seriöser eigener Text")
        self.assertEqual(self.inquiry.private_draft, "Laut Anzeige ist Versand möglich.")
        self.assertEqual(self.inquiry.status, CustomerInquiry.Status.IN_PROGRESS)
        self.assertEqual(self.inquiry.buyer, self.buyer)
        self.assertEqual(self.inquiry.listing, self.listing)
        self.assertEqual(self.inquiry.route_source, "rules")
        self.assertEqual(self.inquiry.selected_agents, ["logistics"])
        self.assertEqual(self.inquiry.audit, [{"code": "notice", "message": "Preise selbst prüfen"}])

    def test_keine_freigabe_oder_kundenbenachrichtigung(self):
        self.client.force_login(self.owner)
        self.post("Privat bearbeitete Antwort 18")
        self.inquiry.refresh_from_db()
        self.assertNotIn("sent", CustomerInquiry.Status.values)
        self.assertEqual(self.inquiry.status, CustomerInquiry.Status.IN_PROGRESS)
        self.assertEqual(self.inquiry.approved_response, "")
        self.assertIsNone(self.inquiry.approved_at)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("listings:listing_detail", args=[self.listing.pk]))
        self.assertNotContains(response, "Privat bearbeitete Antwort 18")
        self.assertEqual(self.client.get(self.detail()).status_code, 404)

    def test_detail_zeigt_beide_versionen_nur_verkaeufer(self):
        self.client.force_login(self.owner)
        self.post("Privat geändert 18")
        response = self.client.get(self.detail())
        self.assertContains(response, "Laut Anzeige ist Versand möglich.")
        self.assertContains(response, "Privat geändert 18")
        self.assertContains(response, "Antwortentwurf bearbeiten")

    def test_inbox_zeigt_bearbeitete_vorschau(self):
        self.client.force_login(self.owner)
        self.post("Privater Verkäufertext 18")
        response = self.client.get(reverse("listings:seller_inquiries"))
        self.assertContains(response, "Privater Verkäufertext 18")
        self.assertContains(response, "Von dir bearbeitet")

    def test_html_wird_in_editor_und_detail_escaped(self):
        self.client.force_login(self.owner)
        malicious = '<script>alert("angriff")</script>'
        self.assertEqual(self.post(malicious).status_code, 302)
        for url in (self.edit(), self.detail()):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn(b"<script>", response.content)
                self.assertContains(response, "&lt;script&gt;", html=False)

    def test_csrf_ohne_token_verboten(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.edit(), {"seller_draft": "Mein privater Antwortentwurf"}).status_code, 403)
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.seller_draft, "")

    def test_andere_http_methoden_unzulaessig(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.put(self.edit(), data={"seller_draft": "Versuch"}).status_code, 405)
        self.assertEqual(self.client.delete(self.edit()).status_code, 405)

    def test_ki_platzhalter_wird_nicht_vorbefuellt(self):
        self.inquiry.private_draft = "Kein automatischer Entwurf verfügbar. Bitte manuell antworten."
        self.inquiry.save(update_fields=["private_draft"])
        self.client.force_login(self.owner)
        form = self.client.get(self.edit()).context["form"]
        self.assertEqual(form.initial["seller_draft"], "")

    def test_zurueckgehaltener_teil_wird_nicht_vorbefuellt(self):
        self.inquiry.private_draft = "Ein Antwortteil wurde zur Sicherheitsprüfung zurückgehalten."
        self.inquiry.save(update_fields=["private_draft"])
        self.client.force_login(self.owner)
        form = self.client.get(self.edit()).context["form"]
        self.assertEqual(form.initial["seller_draft"], "")

    def test_ohne_ki_entwurf_kann_manuell_geschrieben_werden(self):
        self.inquiry.private_draft = ""
        self.inquiry.save(update_fields=["private_draft"])
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.edit()).context["form"].initial["seller_draft"], "")
        self.assertRedirects(self.post("Ich muss das erst prüfen."), self.detail())
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.seller_draft, "Ich muss das erst prüfen.")

    def test_alte_daten_bleiben_ohne_bearbeitung_unveraendert(self):
        # Datensatz aus Tag 16/17 ohne Verkäufertext bleibt gültig.
        self.inquiry.refresh_from_db()
        self.assertIsNone(self.inquiry.seller_draft_updated_at)
        self.assertEqual(self.inquiry.seller_draft, "")
