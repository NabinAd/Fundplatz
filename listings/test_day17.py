"""Phase 3 / Tag 17: Verkäuferpostfach, Detailrechte und interner Status."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import CustomerInquiry, Listing


class SellerInboxDay17Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username="owner17", password="Secure17-pass")
        cls.other = User.objects.create_user(username="other17", password="Secure17-pass")
        cls.buyer = User.objects.create_user(username="buyer17", password="Secure17-pass")
        cls.first = Listing.objects.create(
            seller=cls.owner, title="Lenovo Notebook", description="Notebook", price=Decimal("100.00"),
        )
        cls.second = Listing.objects.create(
            seller=cls.other, title="Privater Rucksack", description="Anderes", price=Decimal("30.00"),
        )
        cls.own_inquiry = CustomerInquiry.objects.create(
            listing=cls.first, buyer=cls.buyer, message="Wie ist der Zustand des Lenovo?",
            private_draft="Privater Entwurf für Lenovo 789", status=CustomerInquiry.Status.REVIEW_REQUIRED,
            selected_agents=["information"], route_source="rules",
            audit=[{"code": "test_audit", "message": "Manuell prüfen"}],
        )
        cls.other_inquiry = CustomerInquiry.objects.create(
            listing=cls.second, buyer=cls.buyer, message="Wie ist der Zustand?",
            private_draft="Fremder Geheimentwurf 457", status=CustomerInquiry.Status.NEEDS_ATTENTION,
        )

    def inbox(self):
        return reverse("listings:seller_inquiries")

    def detail(self, inquiry=None):
        return reverse("listings:seller_inquiry_detail", args=[(inquiry or self.own_inquiry).pk])

    def start(self, inquiry=None):
        return reverse("listings:seller_inquiry_start", args=[(inquiry or self.own_inquiry).pk])

    def test_verkaeufer_sieht_nur_sein_postfach(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.inbox())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Privater Entwurf für Lenovo")
        self.assertNotContains(response, "Fremder Geheimentwurf")
        self.assertEqual(response.context["total_count"], 1)

    def test_alle_filterzahlen_nur_eigene_anfragen(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.inbox())
        self.assertEqual(response.context["review_count"], 1)
        self.assertEqual(response.context["attention_count"], 0)
        self.assertEqual(response.context["progress_count"], 0)

    def test_verkaeufer_sieht_eigene_detailseite(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.detail())
        self.assertContains(response, "Wie ist der Zustand des Lenovo?")
        self.assertContains(response, "Privater Entwurf für Lenovo 789")
        self.assertContains(response, "test_audit")
        self.assertContains(response, "information")

    def test_detail_fuer_fremden_verkaeufer_404(self):
        self.client.force_login(self.other)
        response = self.client.get(self.detail())
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b"Privater Entwurf", response.content)

    def test_detail_fuer_kaeufer_404(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(self.detail()).status_code, 404)

    def test_detail_ohne_login_umleitung(self):
        response = self.client.get(self.detail())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_unbekannte_detail_id_404(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("listings:seller_inquiry_detail", args=[999999])).status_code, 404)

    def test_detail_get_veraendert_keinen_status(self):
        self.client.force_login(self.owner)
        self.client.get(self.detail())
        self.own_inquiry.refresh_from_db()
        self.assertEqual(self.own_inquiry.status, CustomerInquiry.Status.REVIEW_REQUIRED)

    def test_markieren_in_bearbeitung_mit_post(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.start())
        self.assertRedirects(response, self.detail())
        self.own_inquiry.refresh_from_db()
        self.assertEqual(self.own_inquiry.status, CustomerInquiry.Status.IN_PROGRESS)

    def test_wiederholte_statusaenderung_idempotent(self):
        self.client.force_login(self.owner)
        self.client.post(self.start())
        self.client.post(self.start())
        self.own_inquiry.refresh_from_db()
        self.assertEqual(self.own_inquiry.status, CustomerInquiry.Status.IN_PROGRESS)

    def test_statusaenderung_nur_post(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.start()).status_code, 405)
        self.own_inquiry.refresh_from_db()
        self.assertEqual(self.own_inquiry.status, CustomerInquiry.Status.REVIEW_REQUIRED)

    def test_fremder_kann_status_nicht_aendern(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.start()).status_code, 404)
        self.own_inquiry.refresh_from_db()
        self.assertEqual(self.own_inquiry.status, CustomerInquiry.Status.REVIEW_REQUIRED)

    def test_kaeufer_kann_status_nicht_aendern(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.post(self.start()).status_code, 404)
        self.own_inquiry.refresh_from_db()
        self.assertEqual(self.own_inquiry.status, CustomerInquiry.Status.REVIEW_REQUIRED)

    def test_statusaenderung_ohne_login_umleitung(self):
        response = self.client.post(self.start())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_csrf_schutz_fuer_bearbeitung(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.owner)
        self.assertEqual(csrf_client.post(self.start()).status_code, 403)
        self.own_inquiry.refresh_from_db()
        self.assertEqual(self.own_inquiry.status, CustomerInquiry.Status.REVIEW_REQUIRED)

    def test_filter_nach_status(self):
        self.client.force_login(self.owner)
        filtered = self.client.get(self.inbox(), {"status": "needs_attention"})
        self.assertNotContains(filtered, "Privater Entwurf für Lenovo")
        self.assertContains(filtered, "Keine passenden Kundenanfragen")
        filtered = self.client.get(self.inbox(), {"status": "review_required"})
        self.assertContains(filtered, "Privater Entwurf für Lenovo")

    def test_filter_ungueltiger_status_wird_nicht_ignoriert(self):
        self.client.force_login(self.owner)
        resp = self.client.get(self.inbox(), {"status": "__all__"})
        self.assertContains(resp, "Keine passenden Kundenanfragen")
        self.assertEqual(len(resp.context["page_obj"]), 0)

    def test_suche_nach_artikel_und_kundenfrage(self):
        self.client.force_login(self.owner)
        for needle in ("Lenovo", "Zustand", "buyer17"):
            with self.subTest(needle=needle):
                self.assertContains(self.client.get(self.inbox(), {"q": needle}), "Privater Entwurf für Lenovo")
        self.assertContains(self.client.get(self.inbox(), {"q": "nicht gefunden"}), "Keine passenden Kundenanfragen")

    def test_suche_greift_nicht_auf_fremde_anfragen_zu(self):
        self.client.force_login(self.owner)
        resp = self.client.get(self.inbox(), {"q": "Rucksack"})
        self.assertEqual(len(resp.context["page_obj"]), 0)
        self.assertNotContains(resp, "Fremder Geheimentwurf")

    def test_get_parameter_koennen_keine_fremden_anfragen_einblenden(self):
        self.client.force_login(self.owner)
        resp = self.client.get(self.inbox(), {"seller": self.other.pk, "user": self.other.pk})
        self.assertNotContains(resp, "Fremder Geheimentwurf")

    def test_paginierung_und_filter_bleiben_erhalten(self):
        for index in range(15):
            CustomerInquiry.objects.create(
                listing=self.first, buyer=self.buyer, message=f"Lenovo Frage {index}",
                status=CustomerInquiry.Status.REVIEW_REQUIRED,
            )
        self.client.force_login(self.owner)
        first = self.client.get(self.inbox(), {"status": "review_required", "q": "Lenovo"})
        self.assertEqual(len(first.context["page_obj"]), 10)
        self.assertContains(first, "page=2")
        self.assertContains(first, "status=review_required")
        second = self.client.get(self.inbox(), {"status": "review_required", "q": "Lenovo", "page": 2})
        self.assertEqual(len(second.context["page_obj"]), 6)

    def test_nur_statusaenderung_keine_kundenantwort(self):
        original_draft = self.own_inquiry.private_draft
        self.client.force_login(self.owner)
        self.client.post(self.start(), {"private_draft": "Manipulierter Text", "status": "approved"})
        self.own_inquiry.refresh_from_db()
        self.assertEqual(self.own_inquiry.private_draft, original_draft)
        self.assertEqual(self.own_inquiry.status, CustomerInquiry.Status.IN_PROGRESS)
        self.assertEqual(self.own_inquiry.approved_response, "")
        self.assertIsNone(self.own_inquiry.approved_at)

    def test_html_in_kundenfrage_und_draft_wird_escaped(self):
        suspicious = CustomerInquiry.objects.create(
            listing=self.first, buyer=self.buyer,
            message='<script>alert("message")</script>',
            private_draft='<script>alert("draft")</script>',
        )
        self.client.force_login(self.owner)
        resp = self.client.get(self.detail(suspicious))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(b"<script>", resp.content)
        self.assertContains(resp, "&lt;script&gt;", html=False)

    def test_ueberlange_suche_zeigt_nicht_ungefiltert_alle_anfragen(self):
        self.client.force_login(self.owner)
        resp = self.client.get(self.inbox(), {"q": "x" * 121})
        self.assertEqual(len(resp.context["page_obj"]), 0)
        self.assertNotContains(resp, "Privater Entwurf für Lenovo")

    def test_post_auf_detailseite_nicht_erlaubt(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(self.detail()).status_code, 405)
