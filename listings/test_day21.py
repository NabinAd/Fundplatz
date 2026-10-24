"""Tag 21: Workflows, Datenschutz und Ereignisprotokoll. Kein echtes Ollama."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .inquiry_timeline import buyer_timeline, record_event, seller_timeline
from .models import CustomerInquiry, InquiryDelivery, InquiryEvent, Listing
from .views import _draft_token


@override_settings(FUNDPLATZ_AGENT_USE_LLM=False)
class InquiryTimelineDay21Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        U = get_user_model()
        cls.seller = U.objects.create_user(username="seller21", password="Secure21-password")
        cls.other_seller = U.objects.create_user(username="other_seller21", password="Secure21-password")
        cls.buyer = U.objects.create_user(username="buyer21", password="Secure21-password")
        cls.other_buyer = U.objects.create_user(username="other_buyer21", password="Secure21-password")
        cls.listing = Listing.objects.create(
            seller=cls.seller, title="ThinkPad Timeline", description="16 GB RAM",
            price=Decimal("220.00"), shipping_available=True,
        )
        cls.other_listing = Listing.objects.create(
            seller=cls.other_seller, title="Anderes Produkt", description="Test",
            price=Decimal("50.00"),
        )
        cls.inquiry = CustomerInquiry.objects.create(
            listing=cls.listing, buyer=cls.buyer, message="Ist Versand möglich?",
            private_draft="KI-INTERN-SECRET-21", audit=[{"code": "audit-secret-21"}],
            seller_draft="VERKAEUFER-INTERN-SECRET-21",
            seller_draft_updated_at=timezone.now(),
            status=CustomerInquiry.Status.IN_PROGRESS,
        )
        cls.foreign_inquiry = CustomerInquiry.objects.create(
            listing=cls.other_listing, buyer=cls.other_buyer,
            message="Privat von Fremden", private_draft="FREMD-INTERN-21",
        )

    def detail_seller(self, q=None):
        return reverse("listings:seller_inquiry_detail", args=[(q or self.inquiry).pk])

    def detail_buyer(self, q=None):
        return reverse("listings:buyer_inquiry_detail", args=[(q or self.inquiry).pk])

    def start_url(self, q=None):
        return reverse("listings:seller_inquiry_start", args=[(q or self.inquiry).pk])

    def edit_url(self, q=None):
        return reverse("listings:seller_inquiry_edit", args=[(q or self.inquiry).pk])

    def approve_url(self, q=None):
        return reverse("listings:seller_inquiry_approve", args=[(q or self.inquiry).pk])

    def deliver_url(self, q=None):
        return reverse("listings:seller_inquiry_deliver", args=[(q or self.inquiry).pk])

    def test_01_allowed_kinds_exact(self):
        self.assertEqual(len(InquiryEvent.Kind.values), 7)
        self.assertIn("delivered", InquiryEvent.Kind.values)

    def test_02_actor_and_timestamp(self):
        e = record_event(self.inquiry, InquiryEvent.Kind.STARTED, actor=self.seller)
        self.assertEqual(e.actor, self.seller)
        self.assertIsNotNone(e.occurred_at)

    def test_03_public_on_received(self):
        e = record_event(self.inquiry, InquiryEvent.Kind.RECEIVED, actor=self.buyer)
        self.assertEqual(e.audience, InquiryEvent.Audience.BUYER)

    def test_04_public_on_delivered(self):
        e = record_event(self.inquiry, InquiryEvent.Kind.DELIVERED, actor=self.seller)
        self.assertEqual(e.audience, InquiryEvent.Audience.BUYER)

    def test_05_private_on_all_internal_kinds(self):
        for kind in (
            InquiryEvent.Kind.DRAFT_CREATED, InquiryEvent.Kind.DRAFT_FAILED,
            InquiryEvent.Kind.STARTED, InquiryEvent.Kind.SELLER_DRAFT_SAVED,
            InquiryEvent.Kind.APPROVED,
        ):
            self.assertEqual(record_event(self.inquiry, kind).audience, "seller")

    def test_06_bad_kind_rejected(self):
        with self.assertRaises(ValueError):
            record_event(self.inquiry, "arbitrary_event")

    def test_07_no_duplicated_sensitive_message(self):
        e = record_event(self.inquiry, InquiryEvent.Kind.DRAFT_CREATED)
        self.assertFalse(hasattr(e, "message"))
        self.assertFalse(hasattr(e, "text"))
        self.assertFalse(hasattr(e, "payload"))

    def test_08_buyer_timeline_allowlist_even_with_misconfigured_audience(self):
        record_event(self.inquiry, InquiryEvent.Kind.RECEIVED)
        # Absichtlich falsch gespeicherte Sichtbarkeit darf keine privaten
        # Ereignisse im Käuferkontext freigeben.
        InquiryEvent.objects.create(inquiry=self.inquiry, kind="approved", audience="buyer")
        self.assertEqual(list(buyer_timeline(self.inquiry).values_list("kind", flat=True)), ["received"])

    def test_09_buyer_timeline_restricts_inquiry(self):
        record_event(self.inquiry, InquiryEvent.Kind.RECEIVED)
        record_event(self.foreign_inquiry, InquiryEvent.Kind.RECEIVED)
        self.assertEqual(buyer_timeline(self.inquiry).count(), 1)

    def test_10_seller_timeline_includes_all_kinds(self):
        record_event(self.inquiry, InquiryEvent.Kind.RECEIVED)
        record_event(self.inquiry, InquiryEvent.Kind.DRAFT_CREATED)
        self.assertEqual(seller_timeline(self.inquiry).count(), 2)

    def test_11_ordered_by_event_time(self):
        from datetime import timedelta
        now = timezone.now()
        record_event(self.inquiry, InquiryEvent.Kind.STARTED, occurred_at=now + timedelta(hours=1))
        record_event(self.inquiry, InquiryEvent.Kind.RECEIVED, occurred_at=now)
        self.assertEqual(list(seller_timeline(self.inquiry).values_list("kind", flat=True)), ["received", "started"])

    def test_12_seller_detail_has_internal_history(self):
        record_event(self.inquiry, InquiryEvent.Kind.DRAFT_CREATED)
        self.client.force_login(self.seller)
        r = self.client.get(self.detail_seller())
        self.assertContains(r, "Interner Nachrichten- und Statusverlauf")
        self.assertContains(r, "Interner Antwortentwurf erstellt")

    def test_13_buyer_detail_sees_only_public_events(self):
        record_event(self.inquiry, InquiryEvent.Kind.RECEIVED)
        record_event(self.inquiry, InquiryEvent.Kind.APPROVED)
        self.client.force_login(self.buyer)
        r = self.client.get(self.detail_buyer())
        self.assertContains(r, "Dein Nachrichtenverlauf")
        self.assertContains(r, "Kundenanfrage eingegangen")
        self.assertNotContains(r, "Antwort intern freigegeben")
        self.assertNotContains(r, "Interner Antwortentwurf erstellt")
        self.assertNotContains(r, "audit-secret-21")
        self.assertNotContains(r, "KI-INTERN-SECRET-21")

    def test_14_other_buyer_cannot_access_timeline(self):
        self.client.force_login(self.other_buyer)
        self.assertEqual(self.client.get(self.detail_buyer()).status_code, 404)

    def test_15_other_seller_cannot_access_timeline(self):
        self.client.force_login(self.other_seller)
        self.assertEqual(self.client.get(self.detail_seller()).status_code, 404)

    def test_16_guest_redirected(self):
        self.assertEqual(self.client.get(self.detail_seller()).status_code, 302)
        self.assertEqual(self.client.get(self.detail_buyer()).status_code, 302)

    def test_17_get_does_not_create_events(self):
        self.client.force_login(self.seller)
        self.client.get(self.detail_seller())
        self.client.force_login(self.buyer)
        self.client.get(self.detail_buyer())
        self.assertEqual(InquiryEvent.objects.count(), 0)

    def test_18_start_creates_event(self):
        self.inquiry.status = CustomerInquiry.Status.REVIEW_REQUIRED
        self.inquiry.save(update_fields=["status"])
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post(self.start_url()).status_code, 302)
        self.assertTrue(InquiryEvent.objects.filter(inquiry=self.inquiry, kind="started").exists())

    def test_19_double_start_creates_only_one_event(self):
        self.inquiry.status = CustomerInquiry.Status.REVIEW_REQUIRED
        self.inquiry.save(update_fields=["status"])
        self.client.force_login(self.seller)
        self.client.post(self.start_url())
        self.client.post(self.start_url())
        self.assertEqual(InquiryEvent.objects.filter(inquiry=self.inquiry, kind="started").count(), 1)

    def test_20_start_get_has_no_effect(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(self.start_url()).status_code, 405)
        self.assertFalse(InquiryEvent.objects.exists())

    def test_21_edit_saves_private_event(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post(self.edit_url(), {"seller_draft": "Neue sachliche Verkäuferantwort."}).status_code, 302)
        e = InquiryEvent.objects.get(inquiry=self.inquiry, kind="seller_draft_saved")
        self.assertEqual(e.actor, self.seller)
        self.assertEqual(e.audience, "seller")

    def test_22_invalid_edit_creates_no_event(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post(self.edit_url(), {"seller_draft": "x"}).status_code, 400)
        self.assertFalse(InquiryEvent.objects.exists())

    def test_23_foreign_edit_creates_no_event(self):
        self.client.force_login(self.other_seller)
        self.assertEqual(self.client.post(self.edit_url(), {"seller_draft": "Neue Antwort."}).status_code, 404)
        self.assertFalse(InquiryEvent.objects.exists())

    def test_24_approve_logs_snapshot_and_actor(self):
        self.client.force_login(self.seller)
        response = self.client.post(self.approve_url(), {
            "draft_token": _draft_token(self.inquiry),
            "confirmed": "on", "confirmation_word": "FREIGEBEN",
        })
        self.assertEqual(response.status_code, 302)
        self.inquiry.refresh_from_db()
        e = InquiryEvent.objects.get(inquiry=self.inquiry, kind="approved")
        self.assertEqual(e.actor, self.seller)
        self.assertEqual(e.occurred_at, self.inquiry.approved_at)

    def test_25_invalid_approval_creates_no_event(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post(self.approve_url(), {
            "draft_token": _draft_token(self.inquiry), "confirmed": "on", "confirmation_word": "NEIN",
        }).status_code, 400)
        self.assertFalse(InquiryEvent.objects.exists())

    def test_26_double_approval_has_one_event(self):
        self.client.force_login(self.seller)
        data = {"draft_token": _draft_token(self.inquiry), "confirmed": "on", "confirmation_word": "FREIGEBEN"}
        self.client.post(self.approve_url(), data)
        self.client.post(self.approve_url(), data)
        self.assertEqual(InquiryEvent.objects.filter(inquiry=self.inquiry, kind="approved").count(), 1)

    def test_27_delivery_creates_public_event(self):
        self.inquiry.status = CustomerInquiry.Status.APPROVED
        self.inquiry.approved_at = timezone.now()
        self.inquiry.approved_by = self.seller
        self.inquiry.approved_response = "Ja, Versand ist möglich."
        self.inquiry.save(update_fields=["status", "approved_at", "approved_by", "approved_response"])
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post(self.deliver_url(), {"confirmed": "on"}).status_code, 302)
        e = InquiryEvent.objects.get(inquiry=self.inquiry, kind="delivered")
        delivery = InquiryDelivery.objects.get(inquiry=self.inquiry)
        self.assertEqual(e.occurred_at, delivery.delivered_at)
        self.assertEqual(e.audience, "buyer")

    def test_28_double_delivery_has_one_event(self):
        self.inquiry.status = CustomerInquiry.Status.APPROVED
        self.inquiry.approved_at = timezone.now()
        self.inquiry.approved_by = self.seller
        self.inquiry.approved_response = "Ja, Versand ist möglich."
        self.inquiry.save(update_fields=["status", "approved_at", "approved_by", "approved_response"])
        self.client.force_login(self.seller)
        self.client.post(self.deliver_url(), {"confirmed": "on"})
        self.client.post(self.deliver_url(), {"confirmed": "on"})
        self.assertEqual(InquiryEvent.objects.filter(inquiry=self.inquiry, kind="delivered").count(), 1)

    def test_29_delivery_without_approval_has_no_event(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post(self.deliver_url(), {"confirmed": "on"}).status_code, 409)
        self.assertFalse(InquiryEvent.objects.exists())

    def test_30_buyer_sees_delivery_event_and_text_after_publish(self):
        self.inquiry.status = CustomerInquiry.Status.APPROVED
        self.inquiry.approved_at = timezone.now()
        self.inquiry.approved_by = self.seller
        self.inquiry.approved_response = "Die Antwort ist freigegeben und korrekt."
        self.inquiry.save(update_fields=["status", "approved_at", "approved_by", "approved_response"])
        self.client.force_login(self.seller)
        self.client.post(self.deliver_url(), {"confirmed": "on"})
        self.client.force_login(self.buyer)
        r = self.client.get(self.detail_buyer())
        self.assertContains(r, "Antwort für Käufer bereitgestellt")
        self.assertContains(r, "Die Antwort ist freigegeben und korrekt.")
        self.assertNotContains(r, "VERKAEUFER-INTERN-SECRET-21")

    @patch("listings.agent_bridge.generate_private_draft")
    def test_31_new_request_records_two_events(self, generate):
        generate.return_value = SimpleNamespace(
            result=SimpleNamespace(
                combined_draft="Versand ist laut Anzeige möglich.",
                route=SimpleNamespace(source="rules", agents=("logistics",)),
                audit=(),
            ),
            requires_attention=False,
        )
        self.client.force_login(self.buyer)
        r = self.client.post(reverse("listings:inquiry_submit", args=[self.listing.pk]), {
            "message": "Ist der Versand möglich?",
        })
        self.assertEqual(r.status_code, 302)
        q = CustomerInquiry.objects.exclude(pk__in=[self.inquiry.pk, self.foreign_inquiry.pk]).get()
        self.assertEqual(list(q.events.values_list("kind", flat=True)), ["received", "draft_created"])
        self.assertEqual(q.events.get(kind="received").actor, self.buyer)

    @patch("listings.agent_bridge.generate_private_draft", side_effect=RuntimeError("LLM offline"))
    def test_32_llm_failure_creates_private_failure_event(self, generate):
        self.client.force_login(self.buyer)
        r = self.client.post(reverse("listings:inquiry_submit", args=[self.listing.pk]), {
            "message": "Frage wenn Modell offline ist?",
        })
        self.assertEqual(r.status_code, 302)
        q = CustomerInquiry.objects.exclude(pk__in=[self.inquiry.pk, self.foreign_inquiry.pk]).get()
        self.assertEqual(list(q.events.values_list("kind", flat=True)), ["received", "draft_failed"])
        self.assertEqual(list(buyer_timeline(q).values_list("kind", flat=True)), ["received"])

    def test_33_event_labels_are_escaped(self):
        # Ereignisse speichern keine unkontrollierten Nachrichtentexte.
        record_event(self.inquiry, InquiryEvent.Kind.RECEIVED)
        self.inquiry.message = '<script>alert("bad")</script>'
        self.inquiry.save(update_fields=["message"])
        self.client.force_login(self.buyer)
        r = self.client.get(self.detail_buyer())
        self.assertNotIn(b"<script>", r.content)

    def test_34_empty_timeline_is_supported(self):
        self.client.force_login(self.buyer)
        self.assertContains(self.client.get(self.detail_buyer()), "noch keine Verlaufsereignisse")

    def test_35_events_cascade_when_inquiry_deleted(self):
        record_event(self.inquiry, InquiryEvent.Kind.RECEIVED)
        self.inquiry.delete()
        self.assertEqual(InquiryEvent.objects.count(), 0)

    def test_36_actor_removed_retains_event(self):
        record_event(self.inquiry, InquiryEvent.Kind.RECEIVED, actor=self.other_buyer)
        self.other_buyer.delete()
        e = InquiryEvent.objects.get(inquiry=self.inquiry)
        self.assertIsNone(e.actor)

    def test_37_no_public_events_from_edit(self):
        self.client.force_login(self.seller)
        self.client.post(self.edit_url(), {"seller_draft": "Das ist ein neuer Entwurf."})
        self.assertEqual(buyer_timeline(self.inquiry).count(), 0)

    def test_38_access_control_before_event_lookup(self):
        record_event(self.inquiry, InquiryEvent.Kind.DRAFT_CREATED)
        self.client.force_login(self.other_buyer)
        self.assertEqual(self.client.get(self.detail_buyer()).status_code, 404)
        self.client.force_login(self.other_seller)
        self.assertEqual(self.client.get(self.detail_seller()).status_code, 404)

    def test_39_legacy_backfill_keeps_real_timestamps(self):
        import importlib
        from django.apps import apps
        module = importlib.import_module("listings.migrations.0007_inquiryevent")
        self.inquiry.approved_at = timezone.now()
        self.inquiry.approved_by = self.seller
        self.inquiry.approved_response = "Historische Freigabe"
        self.inquiry.status = CustomerInquiry.Status.APPROVED
        self.inquiry.save(update_fields=[
            "approved_at", "approved_by", "approved_response", "status",
        ])
        delivery = InquiryDelivery.objects.create(
            inquiry=self.inquiry, response_text="Historische Freigabe", delivered_by=self.seller,
        )
        module.backfill_history(apps, SimpleNamespace(connection=SimpleNamespace(alias="default")))
        events = list(self.inquiry.events.values_list("kind", "occurred_at"))
        kinds = [kind for kind, _ in events]
        self.assertEqual(kinds, ["received", "seller_draft_saved", "approved", "delivered"])
        self.assertEqual(events[0][1], self.inquiry.created_at)
        self.assertEqual(events[1][1], self.inquiry.seller_draft_updated_at)
        self.assertEqual(events[2][1], self.inquiry.approved_at)
        self.assertEqual(events[3][1], delivery.delivered_at)
        self.assertNotIn("draft_created", kinds)  # Alte KI-Zeitpunkte unbekannt

    def test_40_failure_while_logging_rolls_back_edit(self):
        old = self.inquiry.seller_draft
        self.client.force_login(self.seller)
        with patch("listings.views.record_event", side_effect=RuntimeError("DB event not saved")):
            with self.assertRaises(RuntimeError):
                self.client.post(self.edit_url(), {"seller_draft": "Dies ist eine geänderte Antwort."})
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.seller_draft, old)
        self.assertEqual(InquiryEvent.objects.count(), 0)
