"""Kleine, automatisierte Tests für das Ergebnis von Tag 1."""
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
