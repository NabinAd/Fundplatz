"""Phase 3/Tag 16: Sicherheit und Funktionalität der Django-Brücke."""
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .agent_bridge import listing_to_agent_input
from .models import CustomerInquiry, Listing


@override_settings(FUNDPLATZ_AGENT_USE_LLM=False, FUNDPLATZ_AGENT_ASYNC=False)
class DjangoAgentBridgeTests(TestCase):
    def setUp(self):
        user_class = get_user_model()
        self.seller = user_class.objects.create_user(username="seller16", password="SafePassword16!")
        self.buyer = user_class.objects.create_user(username="buyer16", password="SafePassword16!")
        self.other = user_class.objects.create_user(username="other16", password="SafePassword16!")
        self.listing = Listing.objects.create(
            seller=self.seller, title="ThinkPad T480", description="16 GB RAM, gebraucht.",
            price=Decimal("220.00"), condition=Listing.Condition.GOOD,
            shipping_available=True, pickup_available=False, is_negotiable=False,
            is_active=True, location="Frankfurt",
        )
        self.submit_url = reverse("listings:inquiry_submit", args=[self.listing.pk])
        self.inbox_url = reverse("listings:seller_inquiries")

    def login_buyer(self):
        self.client.force_login(self.buyer)

    def ask(self, message="Kannst du den Laptop versenden?"):
        return self.client.post(self.submit_url, {"message": message})

    def test_listing_daten_ohne_fiktion_fuer_agenten(self):
        data = listing_to_agent_input(self.listing, "Ist der Laptop noch verfügbar?")
        self.assertEqual(data.product.price_eur, Decimal("220.00"))
        self.assertEqual(data.product.condition, "Gut")
        self.assertEqual(data.product.location, "Frankfurt")
        self.assertEqual(data.product.shipping_available, True)
        self.assertEqual(data.product.pickup_available, False)
        self.assertEqual(data.product.availability, None)
        self.assertEqual(data.product.listing_id, self.listing.pk)

    def test_gast_sieht_login_hinweis_und_keine_form(self):
        resp = self.client.get(reverse("listings:listing_detail", args=[self.listing.pk]))
        self.assertContains(resp, "Melde dich an")
        self.assertNotContains(resp, "Frage absenden")

    def test_eigentuemer_hat_keine_kundenfrage_form(self):
        self.client.force_login(self.seller)
        resp = self.client.get(reverse("listings:listing_detail", args=[self.listing.pk]))
        self.assertNotContains(resp, "Frage absenden")
        self.assertContains(resp, "Anfrage-Postfach")

    def test_login_erforderlich_fuer_einsenden(self):
        resp = self.ask()
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])
        self.assertEqual(CustomerInquiry.objects.count(), 0)

    def test_eigene_anzeige_nicht_anfragen(self):
        self.client.force_login(self.seller)
        resp = self.ask()
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(CustomerInquiry.objects.exists())

    def test_inaktive_anzeige_wird_nicht_angenommen(self):
        self.listing.is_active = False
        self.listing.save(update_fields=["is_active"])
        self.login_buyer()
        resp = self.ask()
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(CustomerInquiry.objects.exists())

    def test_anfrage_get_nicht_erlaubt(self):
        self.login_buyer()
        self.assertEqual(self.client.get(self.submit_url).status_code, 405)

    def test_anfrage_wird_gespeichert_und_draft_bleibt_privat(self):
        self.login_buyer()
        resp = self.ask("Ist Versand möglich?")
        self.assertRedirects(resp, reverse("listings:listing_detail", args=[self.listing.pk]))
        inquiry = CustomerInquiry.objects.get()
        self.assertEqual(inquiry.buyer, self.buyer)
        self.assertEqual(inquiry.listing, self.listing)
        self.assertEqual(inquiry.route_source, "rules")
        self.assertIn("logistics", inquiry.selected_agents)
        self.assertTrue(inquiry.private_draft)
        self.assertEqual(inquiry.status, CustomerInquiry.Status.REVIEW_REQUIRED)
        public = self.client.get(reverse("listings:listing_detail", args=[self.listing.pk]))
        self.assertNotContains(public, inquiry.private_draft)

    def test_leere_und_zu_lange_nachricht_abgelehnt(self):
        self.login_buyer()
        for msg in ("  ", "X" * 2001, "abc"):
            with self.subTest(length=len(msg)):
                self.assertEqual(self.ask(msg).status_code, 400)
        self.assertFalse(CustomerInquiry.objects.exists())

    def test_keine_masseneinsendungen(self):
        self.login_buyer()
        for idx in range(5):
            CustomerInquiry.objects.create(
                listing=self.listing, buyer=self.buyer, message=f"Frage Nummer {idx}",
            )
        self.assertEqual(self.ask().status_code, 302)
        self.assertEqual(CustomerInquiry.objects.count(), 5)

    def test_alte_nachricht_zaehlt_nicht_zum_stundenlimit(self):
        self.login_buyer()
        old = CustomerInquiry.objects.create(
            listing=self.listing, buyer=self.buyer, message="Alte Frage",
        )
        CustomerInquiry.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(hours=2)
        )
        self.ask()
        self.assertEqual(CustomerInquiry.objects.count(), 2)

    def test_entwurf_bleibt_bei_agent_fehler_gespeichert(self):
        self.login_buyer()
        with patch("listings.agent_bridge.generate_private_draft", side_effect=RuntimeError("LLM offline")):
            self.ask()
        inquiry = CustomerInquiry.objects.get()
        self.assertEqual(inquiry.status, CustomerInquiry.Status.NEEDS_ATTENTION)
        self.assertIn("manuell antworten", inquiry.private_draft)

    @override_settings(FUNDPLATZ_AGENT_USE_LLM=True)
    def test_llm_ist_opt_in(self):
        self.login_buyer()
        dummy = SimpleNamespace(result=SimpleNamespace(
            combined_draft="Privater Text nur für Verkäufer",
            route=SimpleNamespace(source="llm", agents=("information",)),
            audit=(),
        ), requires_attention=False)
        with patch("listings.agent_bridge.generate_private_draft", return_value=dummy) as mock:
            self.ask()
        self.assertTrue(mock.call_args.kwargs["use_llm"])
        self.assertEqual(CustomerInquiry.objects.get().route_source, "llm")

    def test_verkaeufer_sieht_nur_seine_anfragen(self):
        own = CustomerInquiry.objects.create(
            listing=self.listing, buyer=self.buyer, message="Vertrauliche Frage A",
            private_draft="Geheimer Entwurf A",
        )
        other_listing = Listing.objects.create(
            seller=self.other, title="Andere Anzeige", description="Test", price=Decimal("10"),
        )
        CustomerInquiry.objects.create(
            listing=other_listing, buyer=self.buyer, message="Vertrauliche Frage B",
            private_draft="Geheimer Entwurf B",
        )
        self.client.force_login(self.seller)
        response = self.client.get(self.inbox_url)
        self.assertContains(response, own.private_draft)
        self.assertNotContains(response, "Geheimer Entwurf B")

    def test_kaeufer_hat_keinen_zugriff_auf_fremde_entwuerfe(self):
        CustomerInquiry.objects.create(
            listing=self.listing, buyer=self.buyer, message="Frage",
            private_draft="Streng privater Verkäuferentwurf 123",
        )
        self.login_buyer()
        self.assertNotContains(self.client.get(self.inbox_url), "Streng privater Verkäuferentwurf 123")
        self.assertNotContains(self.client.get(reverse("listings:listing_detail", args=[self.listing.pk])), "Streng privater Verkäuferentwurf 123")

    def test_anfrageformular_csrf_geschuetzt(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.buyer)
        resp = client.post(self.submit_url, {"message": "Ist Versand möglich?"})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(CustomerInquiry.objects.exists())
