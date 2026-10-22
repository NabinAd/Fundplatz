"""Automatisierte Tests für Phase 1, Tag 1 und 2."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Listing


class MarketplaceTag1Tests(TestCase):
    def setUp(self):
        self.seller = get_user_model().objects.create_user(
            username="testverkaeufer", password="NurEinTestPasswort123!"
        )

    def create_listing(self, **overrides):
        values = {
            "seller": self.seller,
            "title": "Gebrauchter Schreibtisch",
            "description": "Massivholz, mit leichten Gebrauchsspuren.",
            "price": Decimal("79.00"),
            "category": Listing.Category.FURNITURE,
            "condition": Listing.Condition.GOOD,
        }
        values.update(overrides)
        return Listing.objects.create(**values)

    # Tests aus Tag 1 (unverändert)
    def test_startseite_ist_erreichbar(self):
        response = self.client.get(reverse("listings:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fundplatz")

    def test_aktive_anzeige_wird_angezeigt(self):
        self.create_listing()
        response = self.client.get(reverse("listings:home"))
        self.assertContains(response, "Gebrauchter Schreibtisch")
        self.assertEqual(response.context["listing_count"], 1)

    def test_inaktive_anzeige_wird_ausgeblendet(self):
        self.create_listing(is_active=False)
        response = self.client.get(reverse("listings:home"))
        self.assertNotContains(response, "Gebrauchter Schreibtisch")
        self.assertEqual(response.context["listing_count"], 0)

    def test_negativer_preis_ist_ungueltig(self):
        listing = self.create_listing(price=Decimal("-5.00"))
        with self.assertRaises(ValidationError):
            listing.full_clean()

    def test_admin_erfordert_anmeldung(self):
        response = self.client.get("/admin/listings/listing/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    # Neue Tests für Tag 2
    def test_uebersicht_ist_erreichbar_und_verlinkt(self):
        listing = self.create_listing()
        response = self.client.get(reverse("listings:listing_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gebrauchter Schreibtisch")
        self.assertContains(response, reverse("listings:listing_detail", args=[listing.pk]))

    def test_uebersicht_zeigt_keine_inaktiven_anzeigen(self):
        self.create_listing(title="Aktives Angebot", is_active=True)
        self.create_listing(title="Verstecktes Angebot", is_active=False)
        response = self.client.get(reverse("listings:listing_list"))
        self.assertContains(response, "Aktives Angebot")
        self.assertNotContains(response, "Verstecktes Angebot")
        self.assertEqual(response.context["page_obj"].paginator.count, 1)

    def test_uebersicht_hat_paginierung(self):
        for nummer in range(13):
            self.create_listing(title=f"Angebot {nummer}")
        url = reverse("listings:listing_list")
        first_page = self.client.get(url)
        self.assertEqual(len(first_page.context["page_obj"]), 12)
        self.assertTrue(first_page.context["page_obj"].has_next())
        second_page = self.client.get(url + "?page=2")
        self.assertEqual(len(second_page.context["page_obj"]), 1)

    def test_detailseite_zeigt_produktdaten(self):
        listing = self.create_listing(
            location="Frankfurt", shipping_available=True,
            pickup_available=False, is_negotiable=True
        )
        response = self.client.get(
            reverse("listings:listing_detail", args=[listing.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Massivholz")
        self.assertContains(response, "Frankfurt")
        self.assertContains(response, "Verhandlungsbasis (VB)")
        self.assertContains(response, "testverkaeufer")

    def test_startseitenkarte_fuehrt_zur_detailseite(self):
        listing = self.create_listing()
        response = self.client.get(reverse("listings:home"))
        self.assertContains(response, reverse("listings:listing_detail", args=[listing.pk]))

    def test_inaktive_detailseite_liefert_404(self):
        listing = self.create_listing(is_active=False)
        response = self.client.get(
            reverse("listings:listing_detail", args=[listing.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_unbekannte_detailseite_liefert_404(self):
        response = self.client.get(
            reverse("listings:listing_detail", args=[999999])
        )
        self.assertEqual(response.status_code, 404)

    def test_leere_uebersicht_zeigt_hinweis(self):
        response = self.client.get(reverse("listings:listing_list"))
        self.assertContains(response, "Aktuell sind keine Anzeigen verfügbar")

    def test_beschreibung_wird_html_sicher_ausgegeben(self):
        listing = self.create_listing(description="<script>alert('hi')</script>")
        response = self.client.get(
            reverse("listings:listing_detail", args=[listing.pk])
        )
        self.assertNotContains(response, "<script>alert('hi')</script>")
        self.assertContains(response, "&lt;script&gt;")
