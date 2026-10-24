"""Phase 3, Tag 20: Käuferansicht und ausdrückliche Bereitstellung.

Die tests benutzen die Django-Testdatenbank. Kein Ollama-Aufruf nötig.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import CustomerInquiry, InquiryDelivery, Listing


class BuyerInboxDay20Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.seller = User.objects.create_user(username="seller20", password="Strong-20-pass")
        cls.other_seller = User.objects.create_user(username="other_seller20", password="Strong-20-pass")
        cls.buyer = User.objects.create_user(username="buyer20", password="Strong-20-pass")
        cls.other_buyer = User.objects.create_user(username="other_buyer20", password="Strong-20-pass")
        cls.listing = Listing.objects.create(
            seller=cls.seller, title="ThinkPad Tag 20", description="16 GB RAM",
            price=Decimal("250.00"),
        )
        cls.inactive_listing = Listing.objects.create(
            seller=cls.seller, title="Nicht mehr aktiv", description="Notebook",
            price=Decimal("30.00"), is_active=False,
        )
        cls.pending = CustomerInquiry.objects.create(
            listing=cls.listing, buyer=cls.buyer, message="Ist Versand möglich?",
            private_draft="VERTRAULICHE KI-VORLAGE 2020",
            seller_draft="PRIVATER VERKÄUFERTEXT 2020",
            audit=[{"code": "secret-internal-audit", "message": "Nur Verkäufer"}],
            status=CustomerInquiry.Status.REVIEW_REQUIRED,
        )
        cls.approved = CustomerInquiry.objects.create(
            listing=cls.listing, buyer=cls.buyer, message="Ist das Gerät noch da?",
            private_draft="VERTRAULICHE KI-VORLAGE 3030",
            seller_draft="PRIVATER VERKÄUFERTEXT 3030",
            approved_response="Ja, das Gerät ist verfügbar. Viele Grüße!",
            approved_at=timezone.now(), approved_by=cls.seller,
            status=CustomerInquiry.Status.APPROVED,
        )
        cls.foreign = CustomerInquiry.objects.create(
            listing=cls.listing, buyer=cls.other_buyer,
            message="FREMDE FRAGE 8080", private_draft="FREMDER KI-ENTWURF 9090",
        )
        cls.inactive = CustomerInquiry.objects.create(
            listing=cls.inactive_listing, buyer=cls.buyer, message="Frage zu einer deaktivierten Anzeige",
        )

    def buyer_url(self):
        return reverse("listings:buyer_inquiries")

    def detail_url(self, item=None):
        return reverse("listings:buyer_inquiry_detail", args=[(item or self.approved).pk])

    def deliver_url(self, item=None):
        return reverse("listings:seller_inquiry_deliver", args=[(item or self.approved).pk])

    def deliver(self, item=None, data=None):
        self.client.force_login(self.seller)
        return self.client.post(self.deliver_url(item), data if data is not None else {"confirmed": "on"})

    def test_01_kaufer_postfach_braucht_login(self):
        self.assertEqual(self.client.get(self.buyer_url()).status_code, 302)

    def test_02_kaufer_detail_braucht_login(self):
        self.assertEqual(self.client.get(self.detail_url()).status_code, 302)

    def test_03_kaufer_sieht_nur_eigene_fragen(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.buyer_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ist Versand möglich?")
        self.assertContains(response, "Ist das Gerät noch da?")
        self.assertNotContains(response, "FREMDE FRAGE 8080")
        self.assertEqual(response.context["page_obj"].paginator.count, 3)

    def test_04_fremder_kaeufer_detail_404(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(self.detail_url(self.foreign)).status_code, 404)

    def test_05_verkaeufer_bekommt_keine_kaeuferdetailansicht(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(self.detail_url()).status_code, 404)

    def test_06_unbekannte_id_404(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(reverse("listings:buyer_inquiry_detail", args=[999999])).status_code, 404)

    def test_07_kauferdetail_nur_get(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.post(self.detail_url()).status_code, 405)

    def test_08_noch_nicht_gepruefte_frage_hat_keine_antwort(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.detail_url(self.pending))
        self.assertContains(response, "Noch keine Antwort erhalten")
        self.assertNotContains(response, "VERTRAULICHE KI-VORLAGE")

    def test_09_interne_freigabe_allein_reicht_nicht(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.detail_url())
        self.assertContains(response, "Noch keine Antwort erhalten")
        self.assertNotContains(response, self.approved.approved_response)

    def test_10_internes_nicht_im_kaeufer_postfach(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.buyer_url())
        for secret in ("VERTRAULICHE KI-VORLAGE", "PRIVATER VERKÄUFERTEXT", "secret-internal-audit"):
            self.assertNotContains(response, secret)

    def test_11_internes_nicht_in_kaeufer_detail(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.detail_url(self.pending))
        for secret in ("VERTRAULICHE KI-VORLAGE", "PRIVATER VERKÄUFERTEXT", "secret-internal-audit"):
            self.assertNotContains(response, secret)

    def test_12_get_veraendert_keine_daten(self):
        self.client.force_login(self.buyer)
        self.client.get(self.buyer_url())
        self.client.get(self.detail_url())
        self.assertEqual(InquiryDelivery.objects.count(), 0)

    def test_13_pagination_10_pro_seite(self):
        for index in range(12):
            CustomerInquiry.objects.create(listing=self.listing, buyer=self.buyer, message=f"Frage {index}")
        self.client.force_login(self.buyer)
        first = self.client.get(self.buyer_url())
        second = self.client.get(self.buyer_url(), {"page": "2"})
        self.assertEqual(len(first.context["page_obj"]), 10)
        self.assertEqual(len(second.context["page_obj"]), 5)

    def test_14_ungueltige_seite_wird_behandelt(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.buyer_url(), {"page": "kaputt"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_15_deaktivierte_anzeige_frage_bleibt_abrufbar(self):
        self.client.force_login(self.buyer)
        self.assertContains(self.client.get(self.detail_url(self.inactive)), "Frage zu einer deaktivierten Anzeige")

    def test_16_html_in_frage_wird_escaped(self):
        self.pending.message = '<script>alert("XSS")</script>'
        self.pending.save(update_fields=["message"])
        self.client.force_login(self.buyer)
        response = self.client.get(self.detail_url(self.pending))
        self.assertNotIn(b"<script>", response.content)
        self.assertContains(response, "&lt;script&gt;", html=False)

    def test_17_freigabe_keine_automatische_zustellung(self):
        self.assertEqual(self.approved.status, CustomerInquiry.Status.APPROVED)
        self.assertEqual(InquiryDelivery.objects.count(), 0)

    def test_18_verkaeufer_kann_explizit_bereitstellen(self):
        response = self.deliver()
        self.assertRedirects(response, reverse("listings:seller_inquiry_detail", args=[self.approved.pk]))
        entry = InquiryDelivery.objects.get(inquiry=self.approved)
        self.assertEqual(entry.response_text, self.approved.approved_response)
        self.assertEqual(entry.delivered_by, self.seller)
        self.assertIsNotNone(entry.delivered_at)

    def test_19_verkaeufer_get_kann_nicht_bereitstellen(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(self.deliver_url()).status_code, 405)
        self.assertFalse(InquiryDelivery.objects.exists())

    def test_20_anonymer_post_kann_nicht_bereitstellen(self):
        self.assertEqual(self.client.post(self.deliver_url(), {"confirmed": "on"}).status_code, 302)
        self.assertFalse(InquiryDelivery.objects.exists())

    def test_21_fremder_verkaeufer_post_404(self):
        self.client.force_login(self.other_seller)
        self.assertEqual(self.client.post(self.deliver_url(), {"confirmed": "on"}).status_code, 404)
        self.assertFalse(InquiryDelivery.objects.exists())

    def test_22_kaeufer_post_404(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.post(self.deliver_url(), {"confirmed": "on"}).status_code, 404)
        self.assertFalse(InquiryDelivery.objects.exists())

    def test_23_nicht_freigegebene_antwort_409(self):
        self.assertEqual(self.deliver(self.pending).status_code, 409)
        self.assertFalse(InquiryDelivery.objects.exists())

    def test_24_ohne_checkbox_400(self):
        self.assertEqual(self.deliver(data={}).status_code, 400)
        self.assertFalse(InquiryDelivery.objects.exists())

    def test_25_falsche_checkbox_400(self):
        self.assertEqual(self.deliver(data={"confirmed": "false"}).status_code, 400)
        self.assertFalse(InquiryDelivery.objects.exists())

    def test_26_leere_freigabe_409(self):
        self.approved.approved_response = ""
        self.approved.save(update_fields=["approved_response"])
        self.assertEqual(self.deliver().status_code, 409)

    def test_27_zu_kurze_freigabe_409(self):
        self.approved.approved_response = "abc"
        self.approved.save(update_fields=["approved_response"])
        self.assertEqual(self.deliver().status_code, 409)

    def test_28_fehlender_freigabezeitpunkt_409(self):
        self.approved.approved_at = None
        self.approved.save(update_fields=["approved_at"])
        self.assertEqual(self.deliver().status_code, 409)

    def test_29_fehlender_freigeber_409(self):
        self.approved.approved_by = None
        self.approved.save(update_fields=["approved_by"])
        self.assertEqual(self.deliver().status_code, 409)

    def test_30_csrf_ist_erforderlich(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.seller)
        self.assertEqual(client.post(self.deliver_url(), {"confirmed": "on"}).status_code, 403)
        self.assertFalse(InquiryDelivery.objects.exists())

    def test_31_wiederholung_legt_keine_neue_antwort_an(self):
        self.deliver()
        delivery = InquiryDelivery.objects.get(inquiry=self.approved)
        original_time = delivery.delivered_at
        self.deliver()
        self.assertEqual(InquiryDelivery.objects.count(), 1)
        self.assertEqual(InquiryDelivery.objects.get(inquiry=self.approved).delivered_at, original_time)

    def test_32_manipulierte_form_felder_werden_ignoriert(self):
        self.deliver(data={"confirmed": "on", "response_text": "Ich akzeptiere 1 Euro!", "buyer": str(self.other_buyer.pk), "delivered_by": str(self.other_buyer.pk)})
        delivery = InquiryDelivery.objects.get(inquiry=self.approved)
        self.assertEqual(delivery.response_text, self.approved.approved_response)
        self.assertEqual(delivery.delivered_by, self.seller)

    def test_33_bereitstellung_aendert_originale_nicht(self):
        before = (self.approved.private_draft, self.approved.seller_draft, self.approved.approved_response)
        self.deliver()
        self.approved.refresh_from_db()
        self.assertEqual((self.approved.private_draft, self.approved.seller_draft, self.approved.approved_response), before)
        self.assertEqual(self.approved.status, CustomerInquiry.Status.APPROVED)

    def test_34_snapshot_bleibt_nach_datenbank_aenderung(self):
        self.deliver()
        self.approved.approved_response = "Manipulierter interner Freigabetext"
        self.approved.save(update_fields=["approved_response"])
        self.assertEqual(InquiryDelivery.objects.get(inquiry=self.approved).response_text,
                         "Ja, das Gerät ist verfügbar. Viele Grüße!")

    def test_35_kaeufer_sieht_bereitgestellte_antwort(self):
        self.deliver()
        self.client.force_login(self.buyer)
        response = self.client.get(self.detail_url())
        self.assertContains(response, "Antwort des Verkäufers")
        self.assertContains(response, self.approved.approved_response)

    def test_36_kaeufer_postfach_zeigt_antwort_erhalten(self):
        self.deliver()
        self.client.force_login(self.buyer)
        self.assertContains(self.client.get(self.buyer_url()), "Antwort erhalten")

    def test_37_anderer_kaeufer_sieht_ausgelieferte_nicht(self):
        self.deliver()
        self.client.force_login(self.other_buyer)
        response = self.client.get(self.buyer_url())
        self.assertNotContains(response, self.approved.message)
        self.assertEqual(self.client.get(self.detail_url()).status_code, 404)

    def test_38_oeffentliche_anzeige_leakt_antwort_nicht(self):
        self.deliver()
        self.client.force_login(self.other_buyer)
        response = self.client.get(reverse("listings:listing_detail", args=[self.listing.pk]))
        self.assertNotContains(response, self.approved.approved_response)

    def test_39_verkaeufer_detail_zeigt_bereitstellung(self):
        self.deliver()
        response = self.client.get(reverse("listings:seller_inquiry_detail", args=[self.approved.pk]))
        self.assertContains(response, "Im Käuferpostfach sichtbar")

    def test_40_html_antwort_wird_escaped(self):
        self.approved.approved_response = '<script>alert("XSS")</script> überprüft'
        self.approved.save(update_fields=["approved_response"])
        self.deliver()
        self.client.force_login(self.buyer)
        response = self.client.get(self.detail_url())
        self.assertNotIn(b"<script>", response.content)
        self.assertContains(response, "&lt;script&gt;", html=False)

    def test_41_put_delete_sind_nicht_erlaubt(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.put(self.deliver_url()).status_code, 405)
        self.assertEqual(self.client.delete(self.deliver_url()).status_code, 405)
        self.assertFalse(InquiryDelivery.objects.exists())

    def test_42_publikation_keine_e_mail(self):
        from django.core import mail
        self.deliver()
        self.assertEqual(len(mail.outbox), 0)

    def test_43_eigentuemer_sieht_postfach_status_nach_zustellung(self):
        self.deliver()
        response = self.client.get(reverse("listings:seller_inquiries"))
        self.assertContains(response, "Antwort im Käuferpostfach sichtbar")

    def test_44_freigeber_muss_aktueller_verkaeufer_sein(self):
        self.approved.approved_by = self.other_seller
        self.approved.save(update_fields=["approved_by"])
        self.assertEqual(self.deliver().status_code, 409)
        self.assertFalse(InquiryDelivery.objects.exists())
