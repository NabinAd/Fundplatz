"""Phase 3 Tag 23: optionale persistente DB-Queue, sichere Worker-Verarbeitung.

Kein echter Ollama-Server erforderlich; das LLM wird ausschliesslich gemockt.
"""
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .draft_queue import next_queued_id, process_inquiry, recover_stale
from .models import CustomerInquiry, InquiryEvent, InquiryDelivery, Listing


@override_settings(FUNDPLATZ_AGENT_USE_LLM=False, FUNDPLATZ_AGENT_ASYNC=True)
class Day23QueueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        U = get_user_model()
        cls.buyer = U.objects.create_user(username="tag23buyer", password="Tag23-test")
        cls.seller = U.objects.create_user(username="tag23seller", password="Tag23-test")
        cls.other = U.objects.create_user(username="tag23other", password="Tag23-test")
        cls.listing = Listing.objects.create(
            seller=cls.seller, title="Fahrrad Tag23", description="Gebraucht",
            price=Decimal("99.00"), shipping_available=False,
        )

    def queued(self):
        return CustomerInquiry.objects.create(
            listing=self.listing, buyer=self.buyer, message="Kann ich es abholen?",
            draft_processing=CustomerInquiry.DraftProcessing.QUEUED,
        )

    def answer(self, *, source="rules", attention=False):
        return SimpleNamespace(
            result=SimpleNamespace(
                combined_draft="Abholung ist laut Anzeige möglich.",
                route=SimpleNamespace(source=source, agents=("logistics",)),
                audit=()),
            requires_attention=attention,
        )

    def test_01_submit_kehrt_zurueck_ohne_modellaufruf(self):
        self.client.force_login(self.buyer)
        with patch("listings.agent_bridge.generate_private_draft") as mock:
            response = self.client.post(
                reverse("listings:inquiry_submit", args=[self.listing.pk]),
                {"message": "Ist Abholung möglich?"},
            )
        self.assertEqual(response.status_code, 302)
        mock.assert_not_called()
        obj = CustomerInquiry.objects.get()
        self.assertEqual(obj.draft_processing, "queued")
        self.assertEqual(obj.private_draft, "")
        self.assertEqual(obj.selected_agents, [])
        self.assertEqual(obj.events.count(), 1)

    def test_02_altbestand_ist_ready(self):
        obj = CustomerInquiry.objects.create(listing=self.listing, buyer=self.buyer, message="Alt")
        self.assertEqual(obj.draft_processing, "ready")
        self.assertIsNone(obj.draft_started_at)

    def test_03_queue_sortierung(self):
        a = self.queued()
        b = self.queued()
        self.assertEqual(next_queued_id(), a.pk)
        self.assertNotEqual(a.pk, b.pk)

    def test_04_worker_generiert_entwurf(self):
        q = self.queued()
        with patch("listings.draft_queue.generate_private_draft", return_value=self.answer()) as gen:
            self.assertTrue(process_inquiry(q.pk))
        self.assertFalse(gen.call_args.kwargs["use_llm"])
        q.refresh_from_db()
        self.assertEqual(q.draft_processing, "ready")
        self.assertEqual(q.route_source, "rules")
        self.assertEqual(q.selected_agents, ["logistics"])
        self.assertEqual(q.status, CustomerInquiry.Status.REVIEW_REQUIRED)
        self.assertIsNotNone(q.draft_finished_at)
        self.assertEqual(q.draft_attempts, 1)
        self.assertEqual(q.events.filter(kind="draft_created").count(), 1)
        self.assertFalse(InquiryDelivery.objects.exists())

    def test_05_zweite_verarbeitung_wird_verhindert(self):
        q = self.queued()
        with patch("listings.draft_queue.generate_private_draft", return_value=self.answer()) as gen:
            self.assertTrue(process_inquiry(q.pk))
            self.assertFalse(process_inquiry(q.pk))
        self.assertEqual(gen.call_count, 1)
        self.assertEqual(q.events.filter(kind="draft_created").count(), 1)

    def test_06_running_job_wird_nicht_erneut_startet(self):
        q = self.queued()
        q.draft_processing = "running"
        q.save(update_fields=["draft_processing"])
        with patch("listings.draft_queue.generate_private_draft") as gen:
            self.assertFalse(process_inquiry(q.pk))
        gen.assert_not_called()

    def test_07_llm_ausfall_markiert_manuelle_bearbeitung(self):
        q = self.queued()
        with patch("listings.draft_queue.generate_private_draft", side_effect=RuntimeError("Ollama nicht da")):
            self.assertTrue(process_inquiry(q.pk))
        q.refresh_from_db()
        self.assertEqual(q.draft_processing, "failed")
        self.assertEqual(q.status, "needs_attention")
        self.assertIn("manuell", q.private_draft)
        self.assertEqual(q.route_source, "")
        self.assertEqual(q.events.filter(kind="draft_failed").count(), 1)
        self.assertFalse(InquiryDelivery.objects.exists())

    def test_08_fallback_bleibt_sichtbar(self):
        q = self.queued()
        with patch("listings.draft_queue.generate_private_draft", return_value=self.answer(source="fallback")):
            process_inquiry(q.pk, use_llm=True)
        q.refresh_from_db()
        self.assertEqual(q.route_source, "fallback")

    def test_09_sicherheitswarnung_bleibt_und_sperrt_nicht_manuell(self):
        q = self.queued()
        with patch("listings.draft_queue.generate_private_draft", return_value=self.answer(attention=True)):
            process_inquiry(q.pk)
        q.refresh_from_db()
        self.assertEqual(q.status, "needs_attention")
        self.assertEqual(q.draft_processing, "ready")

    def test_10_audit_keine_kopierte_antwort_im_event(self):
        q = self.queued()
        with patch("listings.draft_queue.generate_private_draft", return_value=self.answer()):
            process_inquiry(q.pk)
        event = q.events.get(kind="draft_created")
        self.assertEqual(event.audience, "seller")
        self.assertFalse(hasattr(event, "message"))

    def test_11_unbekannte_id_bearbeitet_nichts(self):
        self.assertFalse(process_inquiry(9876543))

    def test_12_approved_wird_nicht_bearbeitet(self):
        q = self.queued()
        q.status = CustomerInquiry.Status.APPROVED
        q.save(update_fields=["status"])
        self.assertFalse(process_inquiry(q.pk))

    def test_13_kein_edit_waehrend_queued(self):
        q = self.queued()
        self.client.force_login(self.seller)
        url = reverse("listings:seller_inquiry_edit", args=[q.pk])
        self.assertEqual(self.client.get(url).status_code, 409)
        self.assertEqual(self.client.post(url, {"seller_draft": "Sichere Antwort"}).status_code, 409)
        q.refresh_from_db()
        self.assertFalse(q.seller_draft)

    def test_14_kein_edit_waehrend_running(self):
        q = self.queued()
        q.draft_processing = "running"
        q.save(update_fields=["draft_processing"])
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post(
            reverse("listings:seller_inquiry_edit", args=[q.pk]),
            {"seller_draft": "Eine sichere Antwort."}).status_code, 409)

    def test_15_keine_freigabe_waehrend_queued(self):
        q = self.queued()
        self.client.force_login(self.seller)
        url = reverse("listings:seller_inquiry_approve", args=[q.pk])
        self.assertEqual(self.client.get(url).status_code, 409)
        self.assertEqual(self.client.post(url, {}).status_code, 409)
        self.assertEqual(q.events.filter(kind="approved").count(), 0)

    def test_16_statusstart_blockiert_waehrend_queued(self):
        q = self.queued()
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post(
            reverse("listings:seller_inquiry_start", args=[q.pk]), {}).status_code, 409)

    def test_17_worker_does_not_publish_to_buyer(self):
        q = self.queued()
        with patch("listings.draft_queue.generate_private_draft", return_value=self.answer()):
            process_inquiry(q.pk)
        self.client.force_login(self.buyer)
        resp = self.client.get(reverse("listings:buyer_inquiry_detail", args=[q.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Abholung ist laut Anzeige möglich.")

    def test_18_seller_kann_queue_status_sehen(self):
        q = self.queued()
        self.client.force_login(self.seller)
        resp = self.client.get(reverse("listings:seller_inquiry_detail", args=[q.pk]))
        # Die neue UI zeigt KI-Verarbeitung getrennt vom Verkäuferstatus.
        self.assertContains(resp, "Wartet auf Worker")
        self.assertContains(resp, 'data-ai-processing-pending="true"')
        self.assertContains(resp, '/static/js/inquiry_processing_refresh.js')
        self.assertNotContains(resp, 'href="' + reverse("listings:seller_inquiry_edit", args=[q.pk]) + '"')

    def test_19_fremder_seller_kann_nicht_queue_sehen(self):
        q = self.queued()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(
            reverse("listings:seller_inquiry_detail", args=[q.pk])).status_code, 404)

    def test_20_nur_alte_running_recovery(self):
        old = self.queued()
        fresh = self.queued()
        CustomerInquiry.objects.filter(pk=old.pk).update(
            draft_processing="running", draft_started_at=timezone.now() - timedelta(minutes=40),
        )
        CustomerInquiry.objects.filter(pk=fresh.pk).update(
            draft_processing="running", draft_started_at=timezone.now() - timedelta(minutes=2),
        )
        self.assertEqual(recover_stale(minutes=30), 1)
        old.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual(old.draft_processing, "queued")
        self.assertEqual(fresh.draft_processing, "running")

    def test_21_recovery_minimum(self):
        with self.assertRaises(ValueError):
            recover_stale(minutes=1)

    def test_22_management_command_once(self):
        q = self.queued()
        with patch("listings.draft_queue.generate_private_draft", return_value=self.answer()) as gen:
            call_command("process_inquiries", once=True, verbosity=0)
        gen.assert_called_once()
        q.refresh_from_db()
        self.assertEqual(q.draft_processing, "ready")

    def test_23_management_command_empty(self):
        with patch("listings.draft_queue.generate_private_draft") as gen:
            call_command("process_inquiries", once=True, verbosity=0)
        gen.assert_not_called()

    def test_24_management_command_conflicting_flags(self):
        with self.assertRaises(CommandError):
            call_command("process_inquiries", once=True, loop=True)

    def test_25_management_command_invalid_limit(self):
        with self.assertRaises(CommandError):
            call_command("process_inquiries", max_jobs=0)

    def test_26_sync_mode_bisherig(self):
        with override_settings(FUNDPLATZ_AGENT_ASYNC=False):
            self.client.force_login(self.buyer)
            resp = self.client.post(reverse("listings:inquiry_submit", args=[self.listing.pk]),
                                    {"message": "Wie funktioniert Abholung?"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(CustomerInquiry.objects.get().draft_processing, "ready")
        self.assertEqual(CustomerInquiry.objects.get().route_source, "rules")

    def test_27_verarbeitung_von_zwei_jobs(self):
        a, b = self.queued(), self.queued()
        with patch("listings.draft_queue.generate_private_draft", return_value=self.answer()) as gen:
            call_command("process_inquiries", max_jobs=2, verbosity=0)
        self.assertEqual(gen.call_count, 2)
        self.assertEqual(CustomerInquiry.objects.filter(draft_processing="ready").count(), 2)
        self.assertEqual(CustomerInquiry.objects.get(pk=a.pk).draft_attempts, 1)
        self.assertEqual(CustomerInquiry.objects.get(pk=b.pk).draft_attempts, 1)

    def test_28_after_recovery_versuchsticket_steigt(self):
        q = self.queued()
        CustomerInquiry.objects.filter(pk=q.pk).update(
            draft_processing="running", draft_started_at=timezone.now() - timedelta(minutes=40),
            draft_attempts=1)
        recover_stale(minutes=30)
        with patch("listings.draft_queue.generate_private_draft", return_value=self.answer()):
            process_inquiry(q.pk)
        q.refresh_from_db()
        self.assertEqual(q.draft_attempts, 2)

    def test_29_keine_modelle_im_sync_modus_vorhanden_noetig(self):
        obj = CustomerInquiry.objects.create(listing=self.listing, buyer=self.buyer, message="Test")
        self.assertFalse(next_queued_id())
        self.assertEqual(obj.draft_processing, "ready")

    def test_30_buyer_sieht_auch_bei_worker_fehler_keinen_entwurf(self):
        q = self.queued()
        with patch("listings.draft_queue.generate_private_draft", side_effect=RuntimeError("SECRET")):
            process_inquiry(q.pk)
        self.client.force_login(self.buyer)
        resp = self.client.get(reverse("listings:buyer_inquiry_detail", args=[q.pk]))
        self.assertNotContains(resp, "Kein automatischer Entwurf verfügbar")
        self.assertNotContains(resp, "SECRET")

    def test_31_approved_queue_item_is_ignored_by_scheduler(self):
        q = self.queued()
        q.status = CustomerInquiry.Status.APPROVED
        q.save(update_fields=["status"])
        self.assertIsNone(next_queued_id())
