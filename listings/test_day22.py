"""Tag 22: Django request/authorization/CSRF/cache/state security regression tests.

All tests run offline in Django's test database; no Ollama required.
"""
import re
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .inquiry_timeline import buyer_timeline, record_event
from .models import CustomerInquiry, InquiryDelivery, InquiryEvent, Listing
from .views import _draft_token


@override_settings(FUNDPLATZ_AGENT_USE_LLM=False)
class Day22SecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        U = get_user_model()
        cls.seller = U.objects.create_user(username="seller22", password="Strong-22-pass")
        cls.foreign_seller = U.objects.create_user(username="foreign_seller22", password="Strong-22-pass")
        cls.buyer = U.objects.create_user(username="buyer22", password="Strong-22-pass")
        cls.stranger = U.objects.create_user(username="stranger22", password="Strong-22-pass")
        cls.listing = Listing.objects.create(
            seller=cls.seller, title="Laptop Sicherheit", description="Guter Zustand",
            price=Decimal("220.00"), shipping_available=True,
        )
        cls.other_listing = Listing.objects.create(
            seller=cls.foreign_seller, title="Fremde Anzeige", description="Privat",
            price=Decimal("42.00"),
        )
        cls.pending = CustomerInquiry.objects.create(
            listing=cls.listing, buyer=cls.buyer, message="Ist Versand möglich?",
            private_draft="KI-GEHEIM-TAG22", seller_draft="Verkäufer-Geheimtext-Tag22",
            seller_draft_updated_at=timezone.now(),
            audit=[{"note": "AUDIT-VERTRAULICH-22"}],
            status=CustomerInquiry.Status.REVIEW_REQUIRED,
        )
        cls.attention = CustomerInquiry.objects.create(
            listing=cls.listing, buyer=cls.buyer, message="Kritische Frage?",
            private_draft="Riskanter KI-Vorschlag", status=CustomerInquiry.Status.NEEDS_ATTENTION,
        )
        cls.approved = CustomerInquiry.objects.create(
            listing=cls.listing, buyer=cls.buyer, message="Ist das Gerät da?",
            private_draft="KI-SUPERGEHEIM-22", seller_draft="Vom Verkäufer gespeichert.",
            seller_draft_updated_at=timezone.now(), approved_response="Offiziell freigegebener, interner Text.",
            approved_at=timezone.now(), approved_by=cls.seller,
            status=CustomerInquiry.Status.APPROVED,
        )
        cls.foreign = CustomerInquiry.objects.create(
            listing=cls.other_listing, buyer=cls.stranger,
            message="Fremde Frage", private_draft="VERBOTEN-22",
        )

    def u(self, name, item=None):
        return reverse("listings:" + name, args=[(item or self.pending).pk])

    def login(self, user):
        self.client.force_login(user)

    # Zugriffsmatrix (privates Verkäuferpostfach, Käuferpostfach)
    def test_01_seller_owns_private_detail(self):
        self.login(self.seller)
        response = self.client.get(self.u("seller_inquiry_detail"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "KI-GEHEIM-TAG22")

    def test_02_other_seller_cannot_read_private_detail(self):
        self.login(self.foreign_seller)
        self.assertEqual(self.client.get(self.u("seller_inquiry_detail")).status_code, 404)

    def test_03_buyer_cannot_read_private_detail(self):
        self.login(self.buyer)
        self.assertEqual(self.client.get(self.u("seller_inquiry_detail")).status_code, 404)

    def test_04_guest_redirected_from_private_detail(self):
        self.assertEqual(self.client.get(self.u("seller_inquiry_detail")).status_code, 302)

    def test_05_buyer_can_read_own_question(self):
        self.login(self.buyer)
        self.assertContains(self.client.get(self.u("buyer_inquiry_detail")), "Ist Versand möglich?")

    def test_06_other_buyer_cannot_read_question(self):
        self.login(self.stranger)
        self.assertEqual(self.client.get(self.u("buyer_inquiry_detail")).status_code, 404)

    def test_07_seller_cannot_read_buyer_private_page(self):
        self.login(self.seller)
        self.assertEqual(self.client.get(self.u("buyer_inquiry_detail")).status_code, 404)

    def test_08_private_text_absent_from_buyer_detail(self):
        self.login(self.buyer)
        body = self.client.get(self.u("buyer_inquiry_detail")).content.decode()
        for secret in ("KI-GEHEIM-TAG22", "Verkäufer-Geheimtext-Tag22", "AUDIT-VERTRAULICH-22"):
            self.assertNotIn(secret, body)

    def test_09_approved_but_not_delivered_is_private(self):
        self.login(self.buyer)
        body = self.client.get(self.u("buyer_inquiry_detail", self.approved)).content.decode()
        self.assertNotIn("Offiziell freigegebener, interner Text.", body)

    def test_10_only_delivery_exposes_response(self):
        InquiryDelivery.objects.create(
            inquiry=self.approved, response_text="Für Käufer freigeschaltet-22", delivered_by=self.seller,
        )
        self.login(self.buyer)
        body = self.client.get(self.u("buyer_inquiry_detail", self.approved)).content.decode()
        self.assertIn("Für Käufer freigeschaltet-22", body)
        self.assertNotIn("KI-SUPERGEHEIM-22", body)

    def test_11_private_timeline_never_public(self):
        record_event(self.pending, InquiryEvent.Kind.APPROVED, actor=self.seller)
        record_event(self.pending, InquiryEvent.Kind.RECEIVED, actor=self.buyer)
        self.assertEqual(list(buyer_timeline(self.pending).values_list("kind", flat=True)), ["received"])

    def test_12_forged_public_audience_not_enough(self):
        InquiryEvent.objects.create(
            inquiry=self.pending, audience=InquiryEvent.Audience.BUYER,
            kind=InquiryEvent.Kind.SELLER_DRAFT_SAVED,
        )
        self.assertFalse(buyer_timeline(self.pending).exists())

    # XSS: escaped data should be text, never active HTML
    def test_13_html_question_escaped_in_buyer_detail(self):
        self.pending.message = '<script>alert("xss-22")</script>'
        self.pending.save(update_fields=["message"])
        self.login(self.buyer)
        html = self.client.get(self.u("buyer_inquiry_detail")).content.decode()
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_14_html_question_escaped_in_seller_detail(self):
        self.pending.message = '<img src=x onerror=alert(22)>'
        self.pending.save(update_fields=["message"])
        self.login(self.seller)
        html = self.client.get(self.u("seller_inquiry_detail")).content.decode()
        self.assertNotIn('<img src=x onerror=alert(22)>', html)
        self.assertIn('&lt;img', html)

    def test_15_delivered_html_escaped(self):
        InquiryDelivery.objects.create(
            inquiry=self.approved, response_text='<svg onload=alert(22)>', delivered_by=self.seller,
        )
        self.login(self.buyer)
        html = self.client.get(self.u("buyer_inquiry_detail", self.approved)).content.decode()
        self.assertNotIn('<svg onload=alert(22)>', html)
        self.assertIn('&lt;svg', html)

    # CSRF and method restrictions
    def test_16_csrf_rejects_buyer_submission(self):
        c = Client(enforce_csrf_checks=True); c.force_login(self.buyer)
        url = reverse("listings:inquiry_submit", args=[self.listing.pk])
        self.assertEqual(c.post(url, {"message": "Ist Versand möglich?"}).status_code, 403)
        self.assertEqual(CustomerInquiry.objects.filter(listing=self.listing).count(), 3)

    def test_17_csrf_rejects_seller_start(self):
        c = Client(enforce_csrf_checks=True); c.force_login(self.seller)
        self.assertEqual(c.post(self.u("seller_inquiry_start")).status_code, 403)

    def test_18_csrf_rejects_seller_edit(self):
        c = Client(enforce_csrf_checks=True); c.force_login(self.seller)
        self.assertEqual(c.post(self.u("seller_inquiry_edit"), {"seller_draft": "Neue Antwort aus CSRF-Test"}).status_code, 403)

    def test_19_csrf_rejects_approval(self):
        c = Client(enforce_csrf_checks=True); c.force_login(self.seller)
        self.assertEqual(c.post(self.u("seller_inquiry_approve"), {
            "draft_token": _draft_token(self.pending), "confirmed": "on", "confirmation_word": "FREIGEBEN",
        }).status_code, 403)

    def test_20_csrf_rejects_delivery(self):
        c = Client(enforce_csrf_checks=True); c.force_login(self.seller)
        self.assertEqual(c.post(self.u("seller_inquiry_deliver", self.approved), {"confirmed": "on"}).status_code, 403)
        self.assertFalse(InquiryDelivery.objects.filter(inquiry=self.approved).exists())

    def test_21_valid_csrf_still_allows_edit(self):
        c = Client(enforce_csrf_checks=True); c.force_login(self.seller)
        page = c.get(self.u("seller_inquiry_edit"))
        self.assertEqual(page.status_code, 200)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page.content.decode())
        self.assertIsNotNone(token)
        posted = c.post(self.u("seller_inquiry_edit"), {
            "csrfmiddlewaretoken": token.group(1), "seller_draft": "Kontrollierte Antwort mit CSRF-Token",
        })
        self.assertEqual(posted.status_code, 302)

    def test_22_submit_get_disallowed(self):
        self.login(self.buyer)
        self.assertEqual(self.client.get(reverse("listings:inquiry_submit", args=[self.listing.pk])).status_code, 405)

    def test_23_deliver_get_disallowed(self):
        self.login(self.seller)
        self.assertEqual(self.client.get(self.u("seller_inquiry_deliver", self.approved)).status_code, 405)

    def test_24_start_get_disallowed(self):
        self.login(self.seller)
        self.assertEqual(self.client.get(self.u("seller_inquiry_start")).status_code, 405)

    def test_25_buyer_detail_post_disallowed(self):
        self.login(self.buyer)
        self.assertEqual(self.client.post(self.u("buyer_inquiry_detail")).status_code, 405)

    # Status invariants and overposting
    def test_26_critical_status_cannot_be_downgraded_by_start(self):
        self.login(self.seller)
        self.assertEqual(self.client.post(self.u("seller_inquiry_start", self.attention)).status_code, 409)
        self.attention.refresh_from_db()
        self.assertEqual(self.attention.status, CustomerInquiry.Status.NEEDS_ATTENTION)
        self.assertFalse(InquiryEvent.objects.filter(inquiry=self.attention, kind=InquiryEvent.Kind.STARTED).exists())

    def test_27_critical_draft_not_autofilled(self):
        self.login(self.seller)
        response = self.client.get(self.u("seller_inquiry_edit", self.attention))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["seller_draft"], "")

    def test_28_saved_seller_draft_still_available_after_warning(self):
        self.attention.seller_draft = "Persönlich kontrollierte Version"
        self.attention.seller_draft_updated_at = timezone.now()
        self.attention.save(update_fields=["seller_draft", "seller_draft_updated_at"])
        self.login(self.seller)
        response = self.client.get(self.u("seller_inquiry_edit", self.attention))
        self.assertEqual(response.context["form"].initial["seller_draft"], "Persönlich kontrollierte Version")

    def test_29_save_cannot_overwrite_private_ai_draft(self):
        self.login(self.seller)
        response = self.client.post(self.u("seller_inquiry_edit"), {
            "seller_draft": "Legitime Verkäuferantwort", "private_draft": "GEFAELSCHT",
            "status": "approved", "approved_response": "GEFAELSCHT",
        })
        self.assertEqual(response.status_code, 302)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.private_draft, "KI-GEHEIM-TAG22")
        self.assertNotEqual(self.pending.status, CustomerInquiry.Status.APPROVED)
        self.assertFalse(self.pending.approved_response)

    def test_30_foreign_seller_cannot_change_status(self):
        self.login(self.foreign_seller)
        self.assertEqual(self.client.post(self.u("seller_inquiry_start")).status_code, 404)

    def test_31_buyer_cannot_approve(self):
        self.login(self.buyer)
        self.assertEqual(self.client.post(self.u("seller_inquiry_approve"), {
            "draft_token": _draft_token(self.pending), "confirmed": "on", "confirmation_word": "FREIGEBEN",
        }).status_code, 404)

    def test_32_buyer_cannot_deliver(self):
        self.login(self.buyer)
        self.assertEqual(self.client.post(self.u("seller_inquiry_deliver", self.approved), {"confirmed": "on"}).status_code, 404)

    def test_33_approval_never_creates_delivery(self):
        self.login(self.seller)
        response = self.client.post(self.u("seller_inquiry_approve"), {
            "draft_token": _draft_token(self.pending), "confirmed": "on", "confirmation_word": "FREIGEBEN",
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(InquiryDelivery.objects.filter(inquiry=self.pending).exists())

    def test_34_delivery_only_one_snapshot(self):
        self.login(self.seller)
        url = self.u("seller_inquiry_deliver", self.approved)
        self.assertEqual(self.client.post(url, {"confirmed": "on"}).status_code, 302)
        self.assertEqual(self.client.post(url, {"confirmed": "on"}).status_code, 302)
        self.assertEqual(InquiryDelivery.objects.filter(inquiry=self.approved).count(), 1)
        self.assertEqual(InquiryDelivery.objects.get(inquiry=self.approved).response_text, self.approved.approved_response)

    def test_35_inquiry_hourly_limit_rejects_sixth(self):
        # Ein eigener Testkäufer verhindert Abhängigkeiten von setUpTestData:
        # self.stranger hat bereits eine Anfrage zur fremden Anzeige.
        buyer = get_user_model().objects.create_user(
            username="rate_limit_buyer22", password="Strong-22-pass"
        )
        for i in range(5):
            CustomerInquiry.objects.create(
                listing=self.listing, buyer=buyer, message=f"Test {i}"
            )
        self.assertEqual(CustomerInquiry.objects.filter(buyer=buyer).count(), 5)
        self.login(buyer)
        url = reverse("listings:inquiry_submit", args=[self.listing.pk])
        response = self.client.post(url, {"message": "Eine weitere Anfrage bitte"})
        self.assertEqual(response.status_code, 302)
        # Die sechste Anfrage wurde NICHT gespeichert.
        self.assertEqual(CustomerInquiry.objects.filter(buyer=buyer).count(), 5)

    # Browser cache and security headers
    def test_36_seller_inbox_not_cached(self):
        self.login(self.seller)
        r = self.client.get(reverse("listings:seller_inquiries"))
        self.assertIn("no-store", r["Cache-Control"])

    def test_37_seller_detail_not_cached(self):
        self.login(self.seller)
        r = self.client.get(self.u("seller_inquiry_detail"))
        self.assertIn("no-store", r["Cache-Control"])

    def test_38_seller_edit_not_cached(self):
        self.login(self.seller)
        r = self.client.get(self.u("seller_inquiry_edit"))
        self.assertIn("no-store", r["Cache-Control"])

    def test_39_seller_approve_not_cached(self):
        self.login(self.seller)
        r = self.client.get(self.u("seller_inquiry_approve"))
        self.assertIn("no-store", r["Cache-Control"])

    def test_40_buyer_inbox_not_cached(self):
        self.login(self.buyer)
        r = self.client.get(reverse("listings:buyer_inquiries"))
        self.assertIn("no-store", r["Cache-Control"])

    def test_41_buyer_detail_not_cached(self):
        self.login(self.buyer)
        r = self.client.get(self.u("buyer_inquiry_detail"))
        self.assertIn("no-store", r["Cache-Control"])

    def test_42_referrer_header_same_origin(self):
        r = self.client.get(reverse("listings:listing_list"))
        self.assertEqual(r["Referrer-Policy"], "same-origin")

    def test_43_nosniff_header(self):
        r = self.client.get(reverse("listings:listing_list"))
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

    def test_44_frame_protection(self):
        r = self.client.get(reverse("listings:listing_list"))
        self.assertEqual(r["X-Frame-Options"], "DENY")

    def test_45_cookie_policy(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, "Lax")

    def test_46_csrf_middleware_present(self):
        self.assertIn("django.middleware.csrf.CsrfViewMiddleware", settings.MIDDLEWARE)

    def test_47_security_middleware_present(self):
        self.assertIn("django.middleware.security.SecurityMiddleware", settings.MIDDLEWARE)

    def test_48_clickjacking_middleware_present(self):
        self.assertIn("django.middleware.clickjacking.XFrameOptionsMiddleware", settings.MIDDLEWARE)

    def test_49_no_email_automatically_sent(self):
        from django.core import mail
        self.login(self.seller)
        self.client.post(self.u("seller_inquiry_deliver", self.approved), {"confirmed": "on"})
        self.assertEqual(len(mail.outbox), 0)

    def test_50_no_hardcoded_publishing_from_buyer(self):
        self.login(self.buyer)
        self.client.post(self.u("buyer_inquiry_detail", self.approved), {
            "approved_response": "PUBLISH-ME", "confirmed": "on",
        })
        self.assertFalse(InquiryDelivery.objects.filter(inquiry=self.approved).exists())
