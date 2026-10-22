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


class MarketplaceTag3Tests(TestCase):
    """CRUD, Login und Zugriffsschutz (Phase 1, Tag 3)."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="anna", password="SicheresPasswort!123"
        )
        self.other = get_user_model().objects.create_user(
            username="ben", password="SicheresPasswort!123"
        )

    def create_listing(self, seller=None, **overrides):
        data = {
            "seller": seller or self.owner,
            "title": "Altes Rennrad",
            "description": "Fahrtüchtig, 28 Zoll.",
            "price": Decimal("150.00"),
            "category": Listing.Category.SPORTS,
            "condition": Listing.Condition.GOOD,
        }
        data.update(overrides)
        return Listing.objects.create(**data)

    def form_data(self, **overrides):
        data = {
            "title": "Bürostuhl",
            "description": "Bequem, mit Armlehnen.",
            "price": "55.00",
            "category": Listing.Category.FURNITURE,
            "condition": Listing.Condition.GOOD,
            "location": "Kassel",
            "pickup_available": "on",
            "is_active": "on",
        }
        data.update(overrides)
        return data

    def test_ohne_login_wird_zur_anmeldung_umgeleitet(self):
        listing = self.create_listing()
        urls = [
            reverse("listings:my_listings"),
            reverse("listings:listing_create"),
            reverse("listings:listing_update", args=[listing.pk]),
            reverse("listings:listing_delete", args=[listing.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith("/login/?next="))

    def test_login_mit_vorhandenem_nutzer(self):
        response = self.client.post(reverse("login"), {
            "username": "anna", "password": "SicheresPasswort!123"
        })
        self.assertRedirects(response, reverse("listings:my_listings"))

    def test_erstellen_seite_zeigt_formular(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("listings:listing_create"))
        self.assertContains(response, "Anzeige erstellen")
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_erstellen_speichert_anzeige_mit_richtigem_besitzer(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("listings:listing_create"),
            self.form_data(seller=str(self.other.pk)),
        )
        listing = Listing.objects.get(title="Bürostuhl")
        self.assertEqual(listing.seller, self.owner)
        self.assertEqual(listing.price, Decimal("55.00"))
        self.assertRedirects(response, reverse("listings:listing_detail", args=[listing.pk]))

    def test_leeres_formular_zeigt_fehler_und_speichert_nichts(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("listings:listing_create"), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dieses Feld ist erforderlich")
        self.assertEqual(Listing.objects.count(), 0)

    def test_negativer_preis_wird_abgelehnt(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("listings:listing_create"), self.form_data(price="-20")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Listing.objects.count(), 0)
        self.assertIn("price", response.context["form"].errors)

    def test_deaktivierte_anzeige_bleibt_in_meine_anzeigen(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("listings:listing_create"), self.form_data(is_active="")
        )
        listing = Listing.objects.get(title="Bürostuhl")
        self.assertFalse(listing.is_active)
        self.assertRedirects(response, reverse("listings:my_listings"))
        self.assertContains(self.client.get(reverse("listings:my_listings")), "Bürostuhl")
        self.assertNotContains(self.client.get(reverse("listings:listing_list")), "Bürostuhl")

    def test_meine_anzeigen_zeigt_nur_eigene_anzeigen(self):
        self.create_listing(title="Mein Angebot", is_active=False)
        self.create_listing(seller=self.other, title="Fremdes Angebot")
        self.client.force_login(self.owner)
        response = self.client.get(reverse("listings:my_listings"))
        self.assertContains(response, "Mein Angebot")
        self.assertNotContains(response, "Fremdes Angebot")
        self.assertContains(response, "Deaktiviert")

    def test_eigene_anzeige_bearbeiten(self):
        listing = self.create_listing()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("listings:listing_update", args=[listing.pk]),
            self.form_data(title="Neuer Titel", price="75.50"),
        )
        listing.refresh_from_db()
        self.assertEqual(listing.title, "Neuer Titel")
        self.assertEqual(listing.price, Decimal("75.50"))
        self.assertRedirects(response, reverse("listings:listing_detail", args=[listing.pk]))

    def test_fremde_anzeige_darf_nicht_bearbeitet_werden(self):
        listing = self.create_listing(seller=self.other)
        self.client.force_login(self.owner)
        url = reverse("listings:listing_update", args=[listing.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, self.form_data()).status_code, 404)
        listing.refresh_from_db()
        self.assertEqual(listing.title, "Altes Rennrad")

    def test_fremde_anzeige_darf_nicht_geloescht_werden(self):
        listing = self.create_listing(seller=self.other)
        self.client.force_login(self.owner)
        url = reverse("listings:listing_delete", args=[listing.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(Listing.objects.filter(pk=listing.pk).exists())

    def test_loeschen_nur_nach_bestaetigung_per_post(self):
        listing = self.create_listing()
        self.client.force_login(self.owner)
        url = reverse("listings:listing_delete", args=[listing.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Listing.objects.filter(pk=listing.pk).exists())
        response = self.client.post(url)
        self.assertRedirects(response, reverse("listings:my_listings"))
        self.assertFalse(Listing.objects.filter(pk=listing.pk).exists())

    def test_abmelden_ist_post_anfrage(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("listings:home"))
        self.assertEqual(
            self.client.get(reverse("listings:my_listings")).status_code, 302
        )

    def test_produktbild_wird_hochgeladen(self):
        import base64
        import tempfile
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        import os

        self.client.force_login(self.owner)
        # Echtes 1x1-GIF für Pillow/ImageField-Validierung.
        gif = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==")
        with tempfile.TemporaryDirectory() as tempdir, override_settings(MEDIA_ROOT=tempdir):
            upload = SimpleUploadedFile("tiny.gif", gif, content_type="image/gif")
            data = self.form_data(image=upload)
            response = self.client.post(reverse("listings:listing_create"), data)
            self.assertEqual(response.status_code, 302)
            listing = Listing.objects.get(title="Bürostuhl")
            self.assertTrue(listing.image.name.startswith("listings/"))
            self.assertTrue(os.path.isfile(listing.image.path))

    def test_deaktivieren_ueber_bearbeiten_ist_kein_loeschen(self):
        listing = self.create_listing()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("listings:listing_update", args=[listing.pk]),
            self.form_data(is_active=""),
        )
        listing.refresh_from_db()
        self.assertFalse(listing.is_active)
        self.assertRedirects(response, reverse("listings:my_listings"))
        self.assertEqual(
            self.client.get(reverse("listings:listing_detail", args=[listing.pk])).status_code,
            404,
        )

    def test_loeschung_mit_aktivierter_csrf_pruefung_ohne_token_verboten(self):
        from django.test import Client

        listing = self.create_listing()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.post(reverse("listings:listing_delete", args=[listing.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Listing.objects.filter(pk=listing.pk).exists())


class MarketplaceTag4Tests(TestCase):
    """Suche, GET-Filter, Registrierung, Anmeldung und Randfälle (Tag 4)."""

    def setUp(self):
        self.seller = get_user_model().objects.create_user(
            username="tag4verkaeufer", password="TestPasswort!2026"
        )
        self.url = reverse("listings:listing_list")

    def make_listing(self, **overrides):
        fields = {
            "seller": self.seller,
            "title": "Gebrauchtes Fahrrad",
            "description": "Sehr gut gepflegtes Fahrrad",
            "price": Decimal("150.00"),
            "category": Listing.Category.SPORTS,
            "condition": Listing.Condition.GOOD,
        }
        fields.update(overrides)
        return Listing.objects.create(**fields)

    def test_leere_suche_zeigt_alle_aktiven_anzeigen(self):
        self.make_listing(title="Aktives Produkt")
        self.make_listing(title="Privates Produkt", is_active=False)
        response = self.client.get(self.url)
        self.assertContains(response, "Aktives Produkt")
        self.assertNotContains(response, "Privates Produkt")
        self.assertEqual(response.context["page_obj"].paginator.count, 1)

    def test_suche_nach_titel_ohne_gross_kleinschreibung(self):
        self.make_listing(title="Gaming Laptop")
        self.make_listing(title="Fahrrad")
        response = self.client.get(self.url, {"q": "LAPTOP"})
        self.assertContains(response, "Gaming Laptop")
        self.assertNotContains(response, "Fahrrad")

    def test_suche_nach_beschreibung(self):
        self.make_listing(title="Tisch", description="Aus massiver Eiche")
        self.make_listing(title="Stuhl", description="Kunststoff")
        response = self.client.get(self.url, {"q": "Eiche"})
        self.assertContains(response, "Tisch")
        self.assertNotContains(response, "Stuhl")

    def test_suche_blendet_deaktivierte_anzeigen_aus(self):
        self.make_listing(title="Laptop sichtbar")
        self.make_listing(title="Laptop verborgen", is_active=False)
        response = self.client.get(self.url, {"q": "Laptop"})
        self.assertContains(response, "Laptop sichtbar")
        self.assertNotContains(response, "Laptop verborgen")

    def test_filter_kategorie(self):
        self.make_listing(title="Sport-Angebot")
        self.make_listing(title="Technik-Angebot", category=Listing.Category.ELECTRONICS)
        response = self.client.get(self.url, {"category": Listing.Category.SPORTS})
        self.assertContains(response, "Sport-Angebot")
        self.assertNotContains(response, "Technik-Angebot")

    def test_mindestpreis_inklusive_grenze(self):
        self.make_listing(title="Genau 150")
        self.make_listing(title="Nur 50", price=Decimal("50.00"))
        response = self.client.get(self.url, {"min_price": "150"})
        self.assertContains(response, "Genau 150")
        self.assertNotContains(response, "Nur 50")

    def test_hoechstpreis_inklusive_grenze(self):
        self.make_listing(title="Genau 150")
        self.make_listing(title="Teuer", price=Decimal("200.00"))
        response = self.client.get(self.url, {"max_price": "150"})
        self.assertContains(response, "Genau 150")
        self.assertNotContains(response, "Teuer")

    def test_alle_filter_kombinieren(self):
        self.make_listing(title="Fahrrad passend", price=Decimal("80"))
        self.make_listing(title="Fahrrad zu teuer", price=Decimal("200"))
        self.make_listing(title="Fahrrad falsch", price=Decimal("80"),
                          category=Listing.Category.ELECTRONICS)
        self.make_listing(title="Snowboard", price=Decimal("80"))
        response = self.client.get(self.url, {
            "q": "Fahrrad", "category": Listing.Category.SPORTS,
            "min_price": "50", "max_price": "100",
        })
        self.assertContains(response, "Fahrrad passend")
        for text in ["Fahrrad zu teuer", "Fahrrad falsch", "Snowboard"]:
            self.assertNotContains(response, text)
        self.assertEqual(response.context["page_obj"].paginator.count, 1)

    def test_unbekannte_kategorie_ist_ungueltig(self):
        self.make_listing()
        response = self.client.get(self.url, {"category": "gibts-nicht"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("category", response.context["filter_form"].errors)
        self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_negativer_preis_ist_ungueltig(self):
        self.make_listing()
        response = self.client.get(self.url, {"min_price": "-1"})
        self.assertIn("min_price", response.context["filter_form"].errors)
        self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_unlogischer_preisbereich_zeigt_fehler(self):
        self.make_listing()
        response = self.client.get(self.url, {"min_price": "200", "max_price": "100"})
        self.assertContains(response, "Mindestpreis darf nicht größer")
        self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_leeres_suchergebnis(self):
        self.make_listing()
        response = self.client.get(self.url, {"q": "nichtvorhanden"})
        self.assertContains(response, "Aktuell sind keine Anzeigen verfügbar")

    def test_paginierung_behält_filter(self):
        for nr in range(13):
            self.make_listing(title=f"Fahrrad Nr {nr}", price=Decimal("90"))
        response = self.client.get(self.url, {"q": "Fahrrad", "max_price": "100"})
        self.assertEqual(len(response.context["page_obj"]), 12)
        self.assertContains(response, "q=Fahrrad")
        self.assertContains(response, "page=2")
        second = self.client.get(self.url, {
            "q": "Fahrrad", "max_price": "100", "page": "2"
        })
        self.assertEqual(len(second.context["page_obj"]), 1)

    def test_suche_zeigt_keine_html_tags_als_code(self):
        self.make_listing(title="Bücher", description="<script>alert(1)</script>")
        response = self.client.get(self.url, {"q": "script"})
        self.assertNotContains(response, "<script>")

    def test_startseite_enthaelt_suchfeld(self):
        response = self.client.get(reverse("listings:home"))
        self.assertContains(response, 'name="q"')

    def test_registrieren_get_zeigt_formular(self):
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Konto erstellen")
        self.assertContains(response, 'name="password2"')

    def test_registrierung_erstellt_konto_und_meldet_an(self):
        response = self.client.post(reverse("signup"), {
            "username": "neuerverkaeufer",
            "password1": "NeuesSicheresPasswort!2026",
            "password2": "NeuesSicheresPasswort!2026",
        })
        self.assertRedirects(response, reverse("listings:my_listings"))
        user = get_user_model().objects.get(username="neuerverkaeufer")
        self.assertTrue(user.check_password("NeuesSicheresPasswort!2026"))
        self.assertNotEqual(user.password, "NeuesSicheresPasswort!2026")
        self.assertEqual(self.client.get(reverse("listings:my_listings")).status_code, 200)

    def test_registrierung_lehnt_unterschiedliche_passwoerter_ab(self):
        response = self.client.post(reverse("signup"), {
            "username": "vielleicht",
            "password1": "SicheresPasswort!2026",
            "password2": "AnderesPasswort!2026",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(get_user_model().objects.filter(username="vielleicht").exists())

    def test_registrierung_lehnt_bereits_vergebenen_namen_ab(self):
        response = self.client.post(reverse("signup"), {
            "username": "tag4verkaeufer",
            "password1": "SicheresPasswort!2026",
            "password2": "SicheresPasswort!2026",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)

    def test_registrierung_prueft_passwortregeln(self):
        response = self.client.post(reverse("signup"), {
            "username": "kurt",
            "password1": "123",
            "password2": "123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(get_user_model().objects.filter(username="kurt").exists())

    def test_angemeldeter_nutzer_nicht_erneut_registrieren(self):
        self.client.force_login(self.seller)
        self.assertRedirects(
            self.client.get(reverse("signup")), reverse("listings:my_listings")
        )

    def test_registrierung_post_ohne_csrf_wird_abgewiesen(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("signup"), {
            "username": "ohnecsrf",
            "password1": "SicheresPasswort!2026",
            "password2": "SicheresPasswort!2026",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(get_user_model().objects.filter(username="ohnecsrf").exists())

    def test_registrierter_nutzer_kann_eigene_anzeige_erstellen(self):
        self.client.post(reverse("signup"), {
            "username": "neueranbieter",
            "password1": "NeuesSicheresPasswort!2026",
            "password2": "NeuesSicheresPasswort!2026",
        })
        response = self.client.post(reverse("listings:listing_create"), {
            "title": "Artikel vom neuen Nutzer",
            "description": "Dies ist ein Testartikel.",
            "price": "15.00",
            "category": Listing.Category.OTHER,
            "condition": Listing.Condition.GOOD,
            "is_active": "on",
        })
        listing = Listing.objects.get(title="Artikel vom neuen Nutzer")
        self.assertEqual(listing.seller.username, "neueranbieter")
        self.assertRedirects(
            response, reverse("listings:listing_detail", args=[listing.pk])
        )

    def test_suchbegriff_wird_html_sicher_ins_formular_uebernommen(self):
        response = self.client.get(self.url, {"q": "<script>alert(1)</script>"})
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")


class MarketplaceTag5Tests(TestCase):
    """Phase-1-Regressionsprüfungen für den schnellen Anzeigenstatuswechsel."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="tag5besitzer", password="SicheresPasswort!2026"
        )
        self.other = get_user_model().objects.create_user(
            username="tag5fremd", password="SicheresPasswort!2026"
        )
        self.listing = Listing.objects.create(
            seller=self.owner, title="Test-Gitarre", description="Guter Zustand",
            price=Decimal("95.00"), category=Listing.Category.OTHER,
            condition=Listing.Condition.GOOD, is_active=True,
        )
        self.url = reverse("listings:listing_toggle_active", args=[self.listing.pk])

    def test_status_button_in_meinen_anzeigen(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("listings:my_listings"))
        self.assertContains(response, self.url)
        self.assertContains(response, "Deaktivieren")
        self.assertContains(response, 'method="post"')

    def test_status_nur_mit_login(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/?next=", response["Location"])
        self.listing.refresh_from_db()
        self.assertTrue(self.listing.is_active)

    def test_status_wechsel_get_ist_unzulaessig(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.listing.refresh_from_db()
        self.assertTrue(self.listing.is_active)

    def test_fremder_kann_status_nicht_aendern(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)
        self.listing.refresh_from_db()
        self.assertTrue(self.listing.is_active)

    def test_deaktivieren_blendet_anzeige_aus(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("listings:my_listings"))
        self.listing.refresh_from_db()
        self.assertFalse(self.listing.is_active)
        self.assertNotContains(self.client.get(reverse("listings:home")), "Test-Gitarre")
        self.assertNotContains(
            self.client.get(reverse("listings:listing_list")), "Test-Gitarre"
        )
        self.assertEqual(
            self.client.get(
                reverse("listings:listing_detail", args=[self.listing.pk])
            ).status_code, 404
        )
        self.assertContains(
            self.client.get(reverse("listings:my_listings")), "Test-Gitarre"
        )

    def test_reaktivieren_zeigt_anzeige_wieder(self):
        self.client.force_login(self.owner)
        self.client.post(self.url)
        response = self.client.get(reverse("listings:my_listings"))
        self.assertContains(response, "Aktivieren")
        self.client.post(self.url)
        self.listing.refresh_from_db()
        self.assertTrue(self.listing.is_active)
        self.assertContains(self.client.get(reverse("listings:listing_list")), "Test-Gitarre")

    def test_ohne_csrf_darf_status_nicht_wechseln(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.listing.refresh_from_db()
        self.assertTrue(self.listing.is_active)

    def test_meine_anzeigen_statuswechsel_loescht_nichts(self):
        self.client.force_login(self.owner)
        self.client.post(self.url)
        self.assertTrue(Listing.objects.filter(pk=self.listing.pk).exists())
        self.client.post(self.url)
        self.assertTrue(Listing.objects.filter(pk=self.listing.pk).exists())

    def test_bootstrap_css_wird_lokal_geladen(self):
        response = self.client.get(reverse("listings:home"))
        self.assertContains(response, "/static/vendor/bootstrap.min.css")
        self.assertNotContains(response, "cdn.jsdelivr.net")

    def test_startseite_hat_sprungmarke(self):
        response = self.client.get(reverse("listings:home"))
        self.assertContains(response, 'href="#hauptinhalt"')
        self.assertContains(response, 'id="hauptinhalt"')
