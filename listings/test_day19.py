"""Tag 19: explizite Freigabe, unveränderlicher Snapshot, kein Versand."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import CustomerInquiry, Listing


class SellerApprovalDay19Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username="owner19", password="Pass19-Secure")
        cls.other = User.objects.create_user(username="other19", password="Pass19-Secure")
        cls.buyer = User.objects.create_user(username="buyer19", password="Pass19-Secure")
        cls.listing = Listing.objects.create(
            seller=cls.owner, title="ThinkPad 19", description="Guter Zustand",
            price=Decimal("220.00"), shipping_available=True,
        )
        cls.other_listing = Listing.objects.create(
            seller=cls.other, title="Fremde Anzeige", description="Privat",
            price=Decimal("40.00"),
        )
        cls.inquiry = CustomerInquiry.objects.create(
            listing=cls.listing, buyer=cls.buyer,
            message="Ist Versand möglich und wären 190 Euro denkbar?",
            private_draft="Die KI empfiehlt nur eine Rücksprache.",
            seller_draft="Hallo, Versand ist möglich. Beim Preis bleibe ich bei 220 Euro.",
            seller_draft_updated_at=timezone.now(),
            status=CustomerInquiry.Status.IN_PROGRESS,
            selected_agents=["logistics", "negotiation"],
            audit=[{"code": "price_review", "message": "Preis selbst prüfen"}],
        )
        cls.foreign = CustomerInquiry.objects.create(
            listing=cls.other_listing, buyer=cls.buyer,
            message="Kann ich abholen?",
            seller_draft="Abholung ist am Freitag möglich.",
            seller_draft_updated_at=timezone.now(),
        )

    def approve_url(self, inquiry=None):
        return reverse("listings:seller_inquiry_approve", args=[(inquiry or self.inquiry).pk])

    def detail_url(self, inquiry=None):
        return reverse("listings:seller_inquiry_detail", args=[(inquiry or self.inquiry).pk])

    def edit_url(self, inquiry=None):
        return reverse("listings:seller_inquiry_edit", args=[(inquiry or self.inquiry).pk])

    def token(self, inquiry=None):
        self.client.force_login(self.owner)
        response = self.client.get(self.approve_url(inquiry))
        self.assertEqual(response.status_code, 200)
        return response.context["form"].initial["draft_token"]

    def post_approval(self, **extra):
        token = self.token()
        values = {"draft_token": token, "confirmed": "on", "confirmation_word": "FREIGEBEN"}
        values.update(extra)
        return self.client.post(self.approve_url(), values)

    def assert_not_approved(self, inquiry=None):
        inquiry = inquiry or self.inquiry
        inquiry.refresh_from_db()
        self.assertNotEqual(inquiry.status, CustomerInquiry.Status.APPROVED)
        self.assertEqual(inquiry.approved_response, "")
        self.assertIsNone(inquiry.approved_at)
        self.assertIsNone(inquiry.approved_by)

    def test_status_approved_ist_vorhanden(self):
        self.assertIn("approved", CustomerInquiry.Status.values)
        self.assertNotIn("sent", CustomerInquiry.Status.values)

    def test_get_benoetigt_login(self):
        response = self.client.get(self.approve_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_post_benoetigt_login(self):
        response = self.client.post(self.approve_url(), {"confirmed": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])
        self.assert_not_approved()

    def test_eigentuemer_sieht_pruefseite(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.approve_url())
        self.assertContains(response, "Antwort vor der Freigabe prüfen")
        self.assertContains(response, self.inquiry.seller_draft)
        self.assertContains(response, "FREIGEBEN")
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_get_allein_gibt_nichts_frei(self):
        self.token()
        self.assert_not_approved()

    def test_fremder_verkaeufer_darf_nicht_sehen(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.approve_url()).status_code, 404)

    def test_fremder_verkaeufer_darf_nicht_freigeben(self):
        token = self.token()
        self.client.force_login(self.other)
        response = self.client.post(self.approve_url(), {
            "draft_token": token, "confirmed": "on", "confirmation_word": "FREIGEBEN",
        })
        self.assertEqual(response.status_code, 404)
        self.assert_not_approved()

    def test_kaeufer_sieht_keine_freigabeseite(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(self.approve_url()).status_code, 404)

    def test_kaeufer_darf_nicht_freigeben(self):
        token = self.token()
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.post(self.approve_url(), {
            "draft_token": token, "confirmed": "on", "confirmation_word": "FREIGEBEN",
        }).status_code, 404)
        self.assert_not_approved()

    def test_eigentuemer_hat_keinen_zugriff_auf_fremde_anfrage(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.approve_url(self.foreign)).status_code, 404)
        self.assertEqual(self.client.post(self.approve_url(self.foreign)).status_code, 404)
        self.assert_not_approved(self.foreign)

    def test_unbekannte_anfrage_404(self):
        self.client.force_login(self.owner)
        url = reverse("listings:seller_inquiry_approve", args=[9999999])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_ohne_checkbox_keine_freigabe(self):
        response = self.post_approval(confirmed="")
        self.assertEqual(response.status_code, 400)
        self.assert_not_approved()

    def test_ohne_bestaetigungswort_keine_freigabe(self):
        response = self.post_approval(confirmation_word="")
        self.assertEqual(response.status_code, 400)
        self.assert_not_approved()

    def test_falsches_bestaetigungswort_keine_freigabe(self):
        response = self.post_approval(confirmation_word="OK")
        self.assertEqual(response.status_code, 400)
        self.assert_not_approved()

    def test_kleingeschriebenes_bestaetigungswort_unzureichend(self):
        response = self.post_approval(confirmation_word="freigeben")
        self.assertEqual(response.status_code, 400)
        self.assert_not_approved()

    def test_fehlender_token_keine_freigabe(self):
        response = self.post_approval(draft_token="")
        self.assertEqual(response.status_code, 400)
        self.assert_not_approved()

    def test_gefaelschter_token_keine_freigabe(self):
        response = self.post_approval(draft_token="0" * 64)
        self.assertEqual(response.status_code, 409)
        self.assert_not_approved()

    def test_veralteter_draft_token_wird_abgelehnt(self):
        token = self.token()
        self.inquiry.seller_draft = "Neuer Verkäufertext, der geprüft werden muss."
        self.inquiry.seller_draft_updated_at = timezone.now()
        self.inquiry.save(update_fields=["seller_draft", "seller_draft_updated_at"])
        response = self.client.post(self.approve_url(), {
            "draft_token": token, "confirmed": "on", "confirmation_word": "FREIGEBEN",
        })
        self.assertEqual(response.status_code, 409)
        self.assert_not_approved()

    def test_kein_verkaeufertext_keine_freigabe(self):
        self.inquiry.seller_draft = ""
        self.inquiry.seller_draft_updated_at = None
        self.inquiry.save(update_fields=["seller_draft", "seller_draft_updated_at"])
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.get(self.approve_url()), self.edit_url())
        self.assertEqual(self.client.post(self.approve_url(), {
            "draft_token": "dummy", "confirmed": "on", "confirmation_word": "FREIGEBEN",
        }).status_code, 400)
        self.assert_not_approved()

    def test_zu_kurzer_verkaeufertext_keine_freigabe(self):
        self.inquiry.seller_draft = "abc"
        self.inquiry.save(update_fields=["seller_draft"])
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.get(self.approve_url()), self.edit_url())
        self.assert_not_approved()

    def test_explizite_freigabe_speichert_snapshot(self):
        before = self.inquiry.seller_draft
        response = self.post_approval()
        self.assertRedirects(response, self.detail_url())
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, CustomerInquiry.Status.APPROVED)
        self.assertEqual(self.inquiry.approved_response, before)
        self.assertIsNotNone(self.inquiry.approved_at)
        self.assertEqual(self.inquiry.approved_by, self.owner)
        self.assertEqual(self.inquiry.seller_draft, before)
        self.assertEqual(self.inquiry.private_draft, "Die KI empfiehlt nur eine Rücksprache.")

    def test_post_extra_fields_koennen_nichts_faelschen(self):
        self.post_approval(
            approved_response="Gefälschter Inhalt", approved_by=str(self.other.pk),
            status="sent", buyer=str(self.other.pk), listing=str(self.other_listing.pk),
            seller_draft="Ich verschenke es", audit="[]",
        )
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.approved_response, self.inquiry.seller_draft)
        self.assertEqual(self.inquiry.approved_by, self.owner)
        self.assertEqual(self.inquiry.status, CustomerInquiry.Status.APPROVED)
        self.assertEqual(self.inquiry.buyer, self.buyer)
        self.assertEqual(self.inquiry.listing, self.listing)
        self.assertEqual(self.inquiry.audit, [{"code": "price_review", "message": "Preis selbst prüfen"}])

    def test_doppelklick_aendert_freigabe_nicht(self):
        self.post_approval()
        self.inquiry.refresh_from_db()
        first_at = self.inquiry.approved_at
        first_text = self.inquiry.approved_response
        response = self.client.post(self.approve_url(), {
            "draft_token": "manipuliert", "confirmed": "on", "confirmation_word": "FREIGEBEN",
        })
        self.assertRedirects(response, self.detail_url())
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.approved_at, first_at)
        self.assertEqual(self.inquiry.approved_response, first_text)

    def test_get_nach_freigabe_leitet_auf_detail(self):
        self.post_approval()
        self.assertRedirects(self.client.get(self.approve_url()), self.detail_url())

    def test_editor_nach_freigabe_gesperrt(self):
        self.post_approval()
        self.assertEqual(self.client.get(self.edit_url()).status_code, 409)
        response = self.client.post(self.edit_url(), {"seller_draft": "Ich habe etwas Neues geschrieben"})
        self.assertEqual(response.status_code, 409)
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.approved_response, self.inquiry.seller_draft)

    def test_status_in_bearbeitung_nach_freigabe_gesperrt(self):
        self.post_approval()
        self.client.force_login(self.owner)
        url = reverse("listings:seller_inquiry_start", args=[self.inquiry.pk])
        self.assertEqual(self.client.post(url).status_code, 409)
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, CustomerInquiry.Status.APPROVED)

    def test_details_zeigen_snapshot_und_freigabeinfo(self):
        self.post_approval()
        response = self.client.get(self.detail_url())
        self.assertContains(response, "Intern freigegebene Antwort")
        self.assertContains(response, "NICHT versendet")
        self.assertContains(response, self.inquiry.seller_draft)
        self.assertNotContains(response, "Antwortentwurf bearbeiten")

    def test_postfach_filter_freigegeben(self):
        self.post_approval()
        response = self.client.get(reverse("listings:seller_inquiries"), {"status": "approved"})
        self.assertContains(response, "ThinkPad 19")
        self.assertContains(response, "Intern freigegeben")
        self.assertEqual(response.context["approved_count"], 1)

    def test_nicht_automatisch_freigegeben_durch_editieren(self):
        self.client.force_login(self.owner)
        self.client.post(self.edit_url(), {"seller_draft": "Ein neuer manueller Antworttext, noch nicht geprüft"})
        self.assert_not_approved()

    def test_manuelle_hinweise_bleiben_bestehen(self):
        self.post_approval()
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.audit, [{"code": "price_review", "message": "Preis selbst prüfen"}])

    def test_kaeufer_sieht_keine_freigegebene_antwort(self):
        self.post_approval()
        self.inquiry.refresh_from_db()
        self.client.force_login(self.buyer)
        detail = self.client.get(reverse("listings:listing_detail", args=[self.listing.pk]))
        self.assertNotContains(detail, self.inquiry.approved_response)
        self.assertEqual(self.client.get(self.detail_url()).status_code, 404)
        self.assertEqual(self.client.get(self.approve_url()).status_code, 404)

    def test_csrf_erforderlich(self):
        token = self.token()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.approve_url(), {
            "draft_token": token, "confirmed": "on", "confirmation_word": "FREIGEBEN",
        }).status_code, 403)
        self.assert_not_approved()

    def test_unzulaessige_http_methoden(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.put(self.approve_url()).status_code, 405)
        self.assertEqual(self.client.delete(self.approve_url()).status_code, 405)
        self.assert_not_approved()

    def test_html_in_antwort_wird_escaped(self):
        self.inquiry.seller_draft = '<script>alert("XSS")</script> geprüft'
        self.inquiry.seller_draft_updated_at = timezone.now()
        self.inquiry.save(update_fields=["seller_draft", "seller_draft_updated_at"])
        self.post_approval()
        for url in (self.detail_url(),):
            response = self.client.get(url)
            self.assertNotIn(b"<script>", response.content)
            self.assertContains(response, "&lt;script&gt;", html=False)

    def test_keine_kundenbenachrichtigung_oder_sende_endpoint(self):
        self.post_approval()
        self.assertNotIn("sent", CustomerInquiry.Status.values)
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, CustomerInquiry.Status.APPROVED)
