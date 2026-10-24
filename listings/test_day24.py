"""Tag 24: reproduzierbare Ende-zu-Ende-Tests fuer Fundplatz.

32 parametrisierte Gesamtwege und gezielte Negativfaelle. Vier getrennte
Django-Testclients bilden zwei Verkaeufer-Browser und zwei Kaeufer-Browser ab.
Der eigentliche Ollama-Server wird NICHT aufgerufen; ausschliesslich die
Agenten-Aussengrenze wird per mock kontrolliert ersetzt. Alles danach laeuft
ueber reale Views, Formulare, Berechtigungen, Datenbank und Templates.

Start: python manage.py test listings.test_day24 -v 2
"""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .agent_bridge import listing_to_agent_input
from .draft_queue import process_inquiry
from .models import CustomerInquiry, InquiryDelivery, InquiryEvent, Listing


# Fall: Testbezeichnung, Verkaeuferanzeige, Kaeufer, zust. Agenten, Routerquelle, Frage.
# Alle 32 Faelle laufen durch POST -> Queue -> Worker -> Edit -> Approve ->
# Deliver -> Buyer-Detail. Die Varianten pruefen Account- und Produkttrennung.
SCENARIOS = [
    ("versand_a_1", "a", "a", ("logistics",), "rules", "Ist Versand moeglich?"),
    ("versand_b_1", "b", "a", ("logistics",), "rules", "Geht Versand bei euch?"),
    ("abholung_a_1", "a", "b", ("logistics",), "rules", "Kann ich das Geraet abholen?"),
    ("abholung_b_1", "b", "b", ("logistics",), "rules", "Ist eine Abholung moeglich?"),
    ("preis_a_1", "a", "a", ("information",), "rules", "Was ist der ausgeschriebene Preis?"),
    ("preis_b_1", "b", "a", ("information",), "rules", "Wie viel kostet das Angebot?"),
    ("zustand_a_1", "a", "b", ("information",), "rules", "Welchen Zustand hat der Artikel?"),
    ("zustand_b_1", "b", "b", ("information",), "rules", "Ist das Geraet gebraucht?"),
    ("vb_a_1", "a", "a", ("negotiation",), "llm", "Ist der Preis verhandelbar?"),
    ("vb_b_1", "b", "a", ("negotiation",), "llm", "Gibt es beim Preis Spielraum?"),
    ("angebot_a_1", "a", "b", ("negotiation",), "llm", "Wuerden Sie 4 Euro akzeptieren?"),
    ("angebot_b_1", "b", "b", ("negotiation",), "llm", "Wuerden Sie 170 Euro akzeptieren?"),
    ("versand_preis_a_1", "a", "a", ("logistics", "negotiation"), "llm", "Versand und Verhandlung moeglich?"),
    ("versand_preis_b_1", "b", "a", ("logistics", "negotiation"), "llm", "Versand und Preisnachlass moeglich?"),
    ("zustand_preis_a_1", "a", "b", ("information", "negotiation"), "rules", "Zustand und Preis?"),
    ("zustand_preis_b_1", "b", "b", ("information", "negotiation"), "rules", "Zustand und VB?"),
    ("versand_zustand_a_1", "a", "a", ("information", "logistics"), "rules", "Versand und Zustand bitte?"),
    ("versand_zustand_b_1", "b", "a", ("information", "logistics"), "rules", "Wie ist der Zustand bei Versand?"),
    ("alle_agenten_a_1", "a", "b", ("information", "negotiation", "logistics"), "llm", "Preis Zustand und Versand?"),
    ("alle_agenten_b_1", "b", "b", ("information", "negotiation", "logistics"), "llm", "VB Zustand und Abholung?"),
    ("fallback_a_1", "a", "a", ("logistics",), "fallback", "Koennen Sie es versenden?"),
    ("fallback_b_1", "b", "a", ("information",), "fallback", "Was fuer ein Artikel ist das?"),
    ("preis_a_2", "a", "b", ("information",), "rules", "Wie lautet der Preis in EUR?"),
    ("preis_b_2", "b", "b", ("information",), "rules", "Ist der Betrag 180 Euro?"),
    ("versand_a_2", "a", "a", ("logistics",), "llm", "Versenden Sie auch innerhalb Deutschlands?"),
    ("versand_b_2", "b", "a", ("logistics",), "llm", "Liefern Sie den Artikel per Post?"),
    ("abholung_a_2", "a", "b", ("logistics",), "rules", "Ist eine persoenliche Abholung vorgesehen?"),
    ("abholung_b_2", "b", "b", ("logistics",), "rules", "Koennen wir eine Abholung besprechen?"),
    ("angebot_a_2", "a", "a", ("negotiation",), "llm", "Wie sieht es mit 6 Euro aus?"),
    ("angebot_b_2", "b", "a", ("negotiation",), "llm", "Waeren 175 Euro eine Option?"),
    ("mixed_a_2", "a", "b", ("information", "logistics"), "rules", "Ist der Artikel defekt und kann ich ihn abholen?"),
    ("mixed_b_2", "b", "b", ("information", "negotiation"), "llm", "Ist er neu und der Preis verhandelbar?"),
]


@override_settings(FUNDPLATZ_AGENT_USE_LLM=False, FUNDPLATZ_AGENT_ASYNC=True)
class Day24EndToEndTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.seller_a = User.objects.create_user(username="tag24_seller_a", password="Secure-tag24-A")
        cls.seller_b = User.objects.create_user(username="tag24_seller_b", password="Secure-tag24-B")
        cls.buyer_a = User.objects.create_user(username="tag24_buyer_a", password="Secure-tag24-C")
        cls.buyer_b = User.objects.create_user(username="tag24_buyer_b", password="Secure-tag24-D")
        cls.listing_a = Listing.objects.create(
            seller=cls.seller_a, title="Fahrrad von A", description="Fahrrad rot, gebraucht",
            price=Decimal("5.00"), shipping_available=True, pickup_available=False,
            is_negotiable=True, location="Berlin",
        )
        cls.listing_b = Listing.objects.create(
            seller=cls.seller_b, title="Notebook von B", description="Notebook blau, wie neu",
            price=Decimal("180.00"), shipping_available=False, pickup_available=True,
            is_negotiable=False, location="Bonn",
        )

    def setUp(self):
        # Vier parallele Sessions wie getrennte Browser. Keine Anmeldung wechselt
        # unbemerkt die Identitaet eines anderen Clients.
        self.sell_a = Client()
        self.sell_b = Client()
        self.buy_a = Client()
        self.buy_b = Client()
        for client, user in (
            (self.sell_a, self.seller_a), (self.sell_b, self.seller_b),
            (self.buy_a, self.buyer_a), (self.buy_b, self.buyer_b),
        ):
            client.force_login(user)

    def buyer_client(self, name):
        return self.buy_a if name == "a" else self.buy_b

    def seller_client(self, name):
        return self.sell_a if name == "a" else self.sell_b

    def listing(self, name):
        return self.listing_a if name == "a" else self.listing_b

    @staticmethod
    def mock_output(listing, *, agents=("information",), source="rules", attention=False):
        return SimpleNamespace(
            result=SimpleNamespace(
                combined_draft=f"NUR-INTERN-24 {listing.title} {listing.price} {listing.shipping_available}",
                route=SimpleNamespace(source=source, agents=agents),
                audit=(),
            ),
            requires_attention=attention,
        )

    def submit(self, *, seller="a", buyer="a", message="Ist Versand moeglich?"):
        listing = self.listing(seller)
        client = self.buyer_client(buyer)
        response = client.post(reverse("listings:inquiry_submit", args=[listing.pk]), {"message": message})
        self.assertEqual(response.status_code, 302)
        # Der gespeicherte Datensatz wird anhand der wirklich angemeldeten
        # Kaeufer-ID gefunden (niemals anhand einer gesendeten buyer_id).
        buyer_user = self.buyer_a if buyer == "a" else self.buyer_b
        inquiry = CustomerInquiry.objects.filter(listing=listing, buyer=buyer_user).latest("pk")
        self.assertEqual(inquiry.draft_processing, "queued")
        return inquiry

    def make_ready(self, inquiry, *, agents=("information",), source="rules", attention=False):
        fake_output = self.mock_output(inquiry.listing, agents=agents, source=source, attention=attention)
        with patch("listings.draft_queue.generate_private_draft", return_value=fake_output) as generator:
            self.assertTrue(process_inquiry(inquiry.pk))
            self.assertFalse(process_inquiry(inquiry.pk))
        generator.assert_called_once()
        self.assertEqual(generator.call_args.args[0].pk, inquiry.listing.pk)
        self.assertEqual(generator.call_args.args[1], inquiry.message)
        inquiry.refresh_from_db()
        return inquiry

    def edit_and_approve(self, inquiry, seller, text):
        browser = self.seller_client(seller)
        edit_url = reverse("listings:seller_inquiry_edit", args=[inquiry.pk])
        self.assertEqual(browser.post(edit_url, {"seller_draft": text}).status_code, 302)
        approval_url = reverse("listings:seller_inquiry_approve", args=[inquiry.pk])
        preflight = browser.get(approval_url)
        self.assertEqual(preflight.status_code, 200)
        token = preflight.context["form"].initial["draft_token"]
        self.assertEqual(browser.post(approval_url, {
            "draft_token": token, "confirmed": "on", "confirmation_word": "FREIGEBEN",
        }).status_code, 302)
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.approved_response, text)
        self.assertEqual(inquiry.status, "approved")

    def exercise_full_flow(self, label, owner, buyer, agents, source, question):
        listing = self.listing(owner)
        buyer_browser = self.buyer_client(buyer)
        owner_browser = self.seller_client(owner)
        wrong_browser = self.seller_client("b" if owner == "a" else "a")
        other_buyer_browser = self.buyer_client("b" if buyer == "a" else "a")

        # 1. Kaeuferfrage im richtigen Browser, HTTP-Annahme ohne LLM.
        with patch("listings.agent_bridge.generate_private_draft") as wrong_path:
            inquiry = self.submit(seller=owner, buyer=buyer, message=question)
        wrong_path.assert_not_called()
        self.assertEqual(inquiry.events.filter(kind="received").count(), 1)
        self.assertFalse(InquiryDelivery.objects.filter(inquiry=inquiry).exists())

        # 2. Der Worker verwendet EXAKT die Anzeige dieser Anfrage.
        context = listing_to_agent_input(inquiry.listing, inquiry.message).product
        self.assertEqual(context.listing_id, listing.pk)
        self.assertEqual(context.price_eur, listing.price)
        self.assertEqual(context.shipping_available, listing.shipping_available)
        self.assertEqual(context.is_negotiable, listing.is_negotiable)
        self.make_ready(inquiry, agents=agents, source=source)
        self.assertEqual(inquiry.route_source, source)
        self.assertEqual(inquiry.selected_agents, list(agents))
        self.assertEqual(inquiry.draft_processing, "ready")
        self.assertEqual(inquiry.events.filter(kind="draft_created").count(), 1)

        # 3. Falscher Verkaeufer kann nicht lesen. Kaeufer sieht kein Original.
        detail = reverse("listings:seller_inquiry_detail", args=[inquiry.pk])
        self.assertEqual(owner_browser.get(detail).status_code, 200)
        self.assertEqual(wrong_browser.get(detail).status_code, 404)
        buyer_detail = reverse("listings:buyer_inquiry_detail", args=[inquiry.pk])
        before = buyer_browser.get(buyer_detail)
        self.assertEqual(before.status_code, 200)
        self.assertNotContains(before, "NUR-INTERN-24")
        self.assertEqual(other_buyer_browser.get(buyer_detail).status_code, 404)

        # 4. Eigentuemergepruefter eigener Text und Freigabe.
        reply = f"Hallo! Zu {listing.title}: Ich habe deine Frage gelesen. {label}. Viele Gruesse!"
        self.edit_and_approve(inquiry, owner, reply)
        self.assertEqual(inquiry.events.filter(kind="seller_draft_saved").count(), 1)
        self.assertEqual(inquiry.events.filter(kind="approved").count(), 1)
        self.assertFalse(InquiryDelivery.objects.filter(inquiry=inquiry).exists())
        self.assertNotContains(buyer_browser.get(buyer_detail), reply)

        # 5. Erst der Bereitstellen-POST veroeffentlicht den Snapshot.
        send_url = reverse("listings:seller_inquiry_deliver", args=[inquiry.pk])
        self.assertEqual(wrong_browser.post(send_url, {"confirmed": "on"}).status_code, 404)
        self.assertEqual(owner_browser.post(send_url, {"confirmed": "on"}).status_code, 302)
        delivery = InquiryDelivery.objects.get(inquiry=inquiry)
        self.assertEqual(delivery.response_text, reply)
        self.assertEqual(delivery.delivered_by_id, listing.seller_id)
        self.assertEqual(inquiry.events.filter(kind="delivered").count(), 1)
        final = buyer_browser.get(buyer_detail)
        self.assertContains(final, reply)
        self.assertNotContains(final, "NUR-INTERN-24")
        self.assertNotContains(final, "draft_created")
        self.assertEqual(other_buyer_browser.get(buyer_detail).status_code, 404)

    def real_offline_flow(self, owner, question, expected_fragment, expected_agent):
        """Echte Rule-Router-/Agentenverarbeitung ohne Mock und ohne Ollama."""
        q = self.submit(seller=owner, buyer="a", message=question)
        self.assertTrue(process_inquiry(q.pk, use_llm=False))
        q.refresh_from_db()
        self.assertEqual(q.draft_processing, "ready")
        self.assertEqual(q.route_source, "rules")
        self.assertIn(expected_agent, q.selected_agents)
        self.assertIn(expected_fragment, q.private_draft)
        buyer_url = reverse("listings:buyer_inquiry_detail", args=[q.pk])
        self.assertNotContains(self.buy_a.get(buyer_url), q.private_draft)
        approved_text = f"Hallo, ich habe deine Frage zu {q.listing.title} geprueft. Viele Gruesse!"
        self.edit_and_approve(q, owner, approved_text)
        self.assertEqual(self.seller_client(owner).post(
            reverse("listings:seller_inquiry_deliver", args=[q.pk]),
            {"confirmed": "on"},
        ).status_code, 302)
        buyer_response = self.buy_a.get(buyer_url)
        self.assertContains(buyer_response, approved_text)
        self.assertNotContains(buyer_response, q.private_draft)
        self.assertEqual(q.events.filter(kind="delivered").count(), 1)

    def test_57_echter_regelrouter_versand_anzeige_a(self):
        self.real_offline_flow("a", "Ist Versand möglich?", "Versand möglich", "logistics")

    def test_58_echter_regelrouter_versand_anzeige_b(self):
        self.real_offline_flow("b", "Ist Versand möglich?", "kein Versand angeboten", "logistics")

    def test_59_echter_regelrouter_preis_anzeige_a(self):
        self.real_offline_flow("a", "Ist der Preis verhandelbar?", "5,00 €", "negotiation")

    def test_60_echter_regelrouter_preis_anzeige_b(self):
        self.real_offline_flow("b", "Ist der Preis verhandelbar?", "180,00 €", "negotiation")

    def test_33_get_beim_verkaeufer_veroeffentlicht_nichts(self):
        q = self.submit()
        self.make_ready(q)
        detail_url = reverse("listings:seller_inquiry_detail", args=[q.pk])
        self.assertEqual(self.sell_a.get(detail_url).status_code, 200)
        self.assertFalse(InquiryDelivery.objects.filter(inquiry=q).exists())

    def test_34_fremder_verkaeufer_kann_nicht_editieren(self):
        q = self.submit()
        self.make_ready(q)
        url = reverse("listings:seller_inquiry_edit", args=[q.pk])
        self.assertEqual(self.sell_b.post(url, {"seller_draft": "Falscher Verkaeufertext"}).status_code, 404)
        q.refresh_from_db()
        self.assertEqual(q.seller_draft, "")

    def test_35_fremder_verkaeufer_kann_nicht_freigeben(self):
        q = self.submit()
        self.make_ready(q)
        self.assertEqual(self.sell_a.post(
            reverse("listings:seller_inquiry_edit", args=[q.pk]),
            {"seller_draft": "Gepruefter Text von A"},
        ).status_code, 302)
        url = reverse("listings:seller_inquiry_approve", args=[q.pk])
        self.assertEqual(self.sell_b.post(url, {
            "draft_token": "x", "confirmed": "on", "confirmation_word": "FREIGEBEN",
        }).status_code, 404)
        self.assertFalse(CustomerInquiry.objects.get(pk=q.pk).approved_response)

    def test_36_buyer_kann_keine_verkaeuferaktionen_ausfuehren(self):
        q = self.submit()
        self.make_ready(q)
        for endpoint, data in (
            ("seller_inquiry_start", {}),
            ("seller_inquiry_edit", {"seller_draft": "Unerlaubter Text"}),
            ("seller_inquiry_approve", {"confirmed": "on"}),
            ("seller_inquiry_deliver", {"confirmed": "on"}),
        ):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.buy_a.post(
                    reverse(f"listings:{endpoint}", args=[q.pk]), data,
                ).status_code, 404)
        self.assertFalse(InquiryDelivery.objects.filter(inquiry=q).exists())

    def test_37_ungueltige_kundenfrage_wird_nicht_angenommen(self):
        for message in ("", "abcd", " " * 10, "x" * 2001):
            with self.subTest(length=len(message)):
                response = self.buy_a.post(reverse("listings:inquiry_submit", args=[self.listing_a.pk]),
                                           {"message": message})
                self.assertEqual(response.status_code, 400)
        self.assertFalse(CustomerInquiry.objects.exists())

    def test_38_eigenes_inserat_kann_nicht_angefragt_werden(self):
        response = self.sell_a.post(reverse("listings:inquiry_submit", args=[self.listing_a.pk]),
                                    {"message": "Ist Versand moeglich?"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CustomerInquiry.objects.exists())

    def test_39_sixth_question_rate_limited_auch_bei_zwei_anzeigen(self):
        for index in range(5):
            listing = self.listing_a if index % 2 == 0 else self.listing_b
            result = self.buy_a.post(reverse("listings:inquiry_submit", args=[listing.pk]),
                                     {"message": f"Anfrage Nummer {index} zu Versand"})
            self.assertEqual(result.status_code, 302)
        response = self.buy_a.post(reverse("listings:inquiry_submit", args=[self.listing_b.pk]),
                                   {"message": "Sechste Frage zu Versand?"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CustomerInquiry.objects.filter(buyer=self.buyer_a).count(), 5)

    def test_40_versteckte_post_felder_duerfen_keinen_owner_aendern(self):
        result = self.buy_a.post(reverse("listings:inquiry_submit", args=[self.listing_a.pk]), {
            "message": "Ist Versand moeglich?", "listing": self.listing_b.pk,
            "seller": self.seller_b.pk, "buyer": self.buyer_b.pk,
            "private_draft": "INJECTED", "status": "approved",
            "approved_response": "INJECTED-APPROVED",
        })
        self.assertEqual(result.status_code, 302)
        q = CustomerInquiry.objects.get()
        self.assertEqual(q.listing_id, self.listing_a.pk)
        self.assertEqual(q.buyer_id, self.buyer_a.pk)
        self.assertEqual(q.status, "needs_attention")
        self.assertEqual(q.private_draft, "")
        self.assertEqual(q.approved_response, "")

    def test_41_offline_adapter_haelt_preise_und_versand_getrennt(self):
        from .agent_bridge import generate_private_draft
        for listing in (self.listing_a, self.listing_b):
            with self.subTest(listing=listing.pk):
                data = listing_to_agent_input(listing, "Ist Versand moeglich?")
                self.assertEqual(data.product.price_eur, listing.price)
                self.assertEqual(data.product.shipping_available, listing.shipping_available)
                # Echter offline-Agentenlauf ohne Ollama und ohne Mock.
                result = generate_private_draft(listing, "Ist Versand moeglich?", use_llm=False)
                self.assertEqual(result.result.route.source, "rules")
                self.assertIsInstance(result.result.combined_draft, str)

    def test_42_sicherheitswarnung_nicht_durch_statusstart_entfernen(self):
        q = self.submit()
        self.make_ready(q, attention=True)
        self.assertEqual(q.status, "needs_attention")
        self.assertEqual(self.sell_a.post(
            reverse("listings:seller_inquiry_start", args=[q.pk]), {}
        ).status_code, 409)
        q.refresh_from_db()
        self.assertEqual(q.status, "needs_attention")

    def test_43_worker_ausfall_ohne_haengende_kundenanfrage(self):
        q = self.submit()
        with patch("listings.draft_queue.generate_private_draft", side_effect=RuntimeError("OLLAMA_SECRET_24")):
            self.assertTrue(process_inquiry(q.pk))
        q.refresh_from_db()
        self.assertEqual(q.draft_processing, "failed")
        self.assertEqual(q.status, "needs_attention")
        self.assertFalse(InquiryDelivery.objects.filter(inquiry=q).exists())
        buyer_html = self.buy_a.get(reverse("listings:buyer_inquiry_detail", args=[q.pk])).content
        self.assertNotIn(b"OLLAMA_SECRET_24", buyer_html)
        self.assertNotIn(b"Kein automatischer Entwurf", buyer_html)

    def test_44_double_worker_keine_duplicated_events(self):
        q = self.submit()
        self.make_ready(q)
        self.assertEqual(q.draft_attempts, 1)
        self.assertEqual(q.events.filter(kind="draft_created").count(), 1)

    def test_45_stale_freigabe_token_wird_abgelehnt(self):
        q = self.submit()
        self.make_ready(q)
        edit_url = reverse("listings:seller_inquiry_edit", args=[q.pk])
        self.assertEqual(self.sell_a.post(edit_url, {"seller_draft": "Erste Version vom Seller"}).status_code, 302)
        url = reverse("listings:seller_inquiry_approve", args=[q.pk])
        old_token = self.sell_a.get(url).context["form"].initial["draft_token"]
        self.assertEqual(self.sell_a.post(edit_url, {"seller_draft": "Zweite Version vom Seller"}).status_code, 302)
        self.assertEqual(self.sell_a.post(url, {
            "draft_token": old_token, "confirmed": "on", "confirmation_word": "FREIGEBEN",
        }).status_code, 409)
        q.refresh_from_db()
        self.assertIsNone(q.approved_at)

    def test_46_keine_freigabe_ohne_bestaetigungswort(self):
        q = self.submit()
        self.make_ready(q)
        self.assertEqual(self.sell_a.post(reverse("listings:seller_inquiry_edit", args=[q.pk]),
                                          {"seller_draft": "Antwort bitte manuell pruefen"}).status_code, 302)
        url = reverse("listings:seller_inquiry_approve", args=[q.pk])
        token = self.sell_a.get(url).context["form"].initial["draft_token"]
        self.assertEqual(self.sell_a.post(url, {
            "draft_token": token, "confirmed": "on", "confirmation_word": "JA",
        }).status_code, 400)
        q.refresh_from_db()
        self.assertIsNone(q.approved_at)

    def test_47_ausliefern_ohne_freigabe_verboten(self):
        q = self.submit()
        self.make_ready(q)
        url = reverse("listings:seller_inquiry_deliver", args=[q.pk])
        self.assertEqual(self.sell_a.post(url, {"confirmed": "on"}).status_code, 409)
        self.assertFalse(InquiryDelivery.objects.exists())

    def test_48_double_delivery_nur_ein_snapshot(self):
        q = self.submit()
        self.make_ready(q)
        text = "Hallo, wir koennen die Konditionen abstimmen."
        self.edit_and_approve(q, "a", text)
        url = reverse("listings:seller_inquiry_deliver", args=[q.pk])
        self.assertEqual(self.sell_a.post(url, {"confirmed": "on"}).status_code, 302)
        delivered = InquiryDelivery.objects.get(inquiry=q)
        first_when = delivered.delivered_at
        self.assertEqual(self.sell_a.post(url, {"confirmed": "on"}).status_code, 302)
        delivered.refresh_from_db()
        self.assertEqual(delivered.delivered_at, first_when)
        self.assertEqual(InquiryDelivery.objects.filter(inquiry=q).count(), 1)
        self.assertEqual(q.events.filter(kind="delivered").count(), 1)

    def test_49_gekaufte_sicht_keine_original_und_audit_payload(self):
        q = self.submit()
        self.make_ready(q)
        q.audit = [{"code": "INTERNAL_AUDIT_TOKEN_24", "message": "SECRET_TEST_24"}]
        q.save(update_fields=["audit"])
        for browser in (self.buy_a, self.buy_b):
            response = browser.get(reverse("listings:buyer_inquiry_detail", args=[q.pk]))
            if browser is self.buy_a:
                self.assertEqual(response.status_code, 200)
                for secret in ("INTERNAL_AUDIT_TOKEN_24", "SECRET_TEST_24", "NUR-INTERN-24"):
                    self.assertNotContains(response, secret)
            else:
                self.assertEqual(response.status_code, 404)

    def test_50_xss_text_im_gesendeten_snapshot_wird_escaped(self):
        q = self.submit(message="Kann ich <img src=x onerror=alert(24)> abholen?")
        self.make_ready(q)
        content = "Hallo, <img src=x onerror=alert(25)> wird nur als Text gespeichert."
        self.edit_and_approve(q, "a", content)
        self.assertEqual(self.sell_a.post(reverse("listings:seller_inquiry_deliver", args=[q.pk]),
                                          {"confirmed": "on"}).status_code, 302)
        response = self.buy_a.get(reverse("listings:buyer_inquiry_detail", args=[q.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"<img src=x onerror", response.content)
        self.assertIn(b"&lt;img", response.content)

    def test_51_csrf_delivery_ohne_token_verboten(self):
        q = self.submit()
        self.make_ready(q)
        self.edit_and_approve(q, "a", "Hallo, ich habe den Text freigegeben.")
        guarded = Client(enforce_csrf_checks=True)
        guarded.force_login(self.seller_a)
        response = guarded.post(reverse("listings:seller_inquiry_deliver", args=[q.pk]), {"confirmed": "on"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(InquiryDelivery.objects.filter(inquiry=q).exists())

    def test_52_csrf_approve_ohne_token_verboten(self):
        q = self.submit()
        self.make_ready(q)
        self.assertEqual(self.sell_a.post(reverse("listings:seller_inquiry_edit", args=[q.pk]),
                                          {"seller_draft": "Ich habe die Angaben kontrolliert."}).status_code, 302)
        guarded = Client(enforce_csrf_checks=True)
        guarded.force_login(self.seller_a)
        response = guarded.post(reverse("listings:seller_inquiry_approve", args=[q.pk]), {
            "draft_token": "dummy", "confirmed": "on", "confirmation_word": "FREIGEBEN",
        })
        self.assertEqual(response.status_code, 403)
        q.refresh_from_db()
        self.assertIsNone(q.approved_at)

    def test_53_ereignisse_fuer_kaeufer_nur_public_types(self):
        q = self.submit()
        self.make_ready(q)
        self.edit_and_approve(q, "a", "Die Lieferung kann besprochen werden.")
        self.sell_a.post(reverse("listings:seller_inquiry_deliver", args=[q.pk]), {"confirmed": "on"})
        response = self.buy_a.get(reverse("listings:buyer_inquiry_detail", args=[q.pk]))
        self.assertEqual(response.status_code, 200)
        kinds = list(response.context["timeline"].values_list("kind", flat=True))
        self.assertEqual(kinds, ["received", "delivered"])
        self.assertEqual(q.events.count(), 5)

    def test_54_inactive_listing_verhindert_neue_frage(self):
        self.listing_b.is_active = False
        self.listing_b.save(update_fields=["is_active"])
        response = self.buy_a.post(reverse("listings:inquiry_submit", args=[self.listing_b.pk]),
                                   {"message": "Ist der Artikel verfuegbar?"})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(CustomerInquiry.objects.exists())

    def test_55_fremder_kaeufer_sieht_andere_anfrage_nicht_im_postfach(self):
        q = self.submit()
        response = self.buy_b.get(reverse("listings:buyer_inquiries"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, q.message)
        self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_56_fremder_verkaeufer_sieht_kein_postfach_von_a(self):
        q = self.submit()
        response = self.sell_b.get(reverse("listings:seller_inquiries"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, q.message)
        self.assertEqual(response.context["total_count"], 0)


# Diese benannten Einzelfaelle sind echte Django-Tests, nicht subTests.
# Damit meldet der Test-Runner die Gesamtzahl und die genaue Fehlerquelle.
def _add_e2e_scenario(case_number, scenario):
    name, owner, buyer, agents, source, question = scenario

    def run(self):
        self.exercise_full_flow(name, owner, buyer, agents, source, question)

    run.__name__ = f"test_{case_number:02d}_e2e_{name}"
    run.__doc__ = f"Volle Kette: Anzeige {owner.upper()}, Kaeufer {buyer.upper()}, Route {source}."
    setattr(Day24EndToEndTests, run.__name__, run)


for _index, _scenario in enumerate(SCENARIOS, start=1):
    _add_e2e_scenario(_index, _scenario)
