"""Tag 25: Release-Audit, Regression fuer synchronen KI-Ausfall und Account-Trennung.

Alle Tests laufen ohne Ollama-Server und ohne externe Services.
Ausfuehrung: python manage.py test listings.test_day25 -v 2
"""
import json
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import F
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .agent_bridge import listing_to_agent_input
from .models import CustomerInquiry, InquiryDelivery, InquiryEvent, Listing


@override_settings(FUNDPLATZ_AGENT_ASYNC=False, FUNDPLATZ_AGENT_USE_LLM=False)
class Day25FinalChecks(TestCase):
    @classmethod
    def setUpTestData(cls):
        U = get_user_model()
        cls.seller = U.objects.create_user(username="day25_seller_a", password="StrongDay25A")
        cls.other_seller = U.objects.create_user(username="day25_seller_b", password="StrongDay25B")
        cls.buyer = U.objects.create_user(username="day25_buyer_a", password="StrongDay25C")
        cls.other_buyer = U.objects.create_user(username="day25_buyer_b", password="StrongDay25D")
        cls.listing = Listing.objects.create(
            seller=cls.seller, title="Fahrrad 5 Euro", description="Ein Rad zum Testen",
            price=Decimal("5.00"), shipping_available=True, pickup_available=False,
            is_negotiable=True,
        )
        cls.other_listing = Listing.objects.create(
            seller=cls.other_seller, title="Notebook 180 Euro", description="Ein Notebook",
            price=Decimal("180.00"), shipping_available=False, pickup_available=True,
            is_negotiable=False,
        )

    def make_inquiry(self, listing=None, buyer=None):
        return CustomerInquiry.objects.create(
            listing=listing or self.listing, buyer=buyer or self.buyer,
            message="Ist Versand moeglich?", private_draft="VERTRAULICH: niemals an Kaeufer",
        )

    def approve(self, inquiry, *, seller=None):
        inquiry.status = CustomerInquiry.Status.APPROVED
        inquiry.approved_response = "Hallo, ich habe deine Frage geprueft. Viele Gruesse!"
        inquiry.approved_at = timezone.now()
        inquiry.approved_by = seller or inquiry.listing.seller
        inquiry.save(update_fields=["status", "approved_response", "approved_at", "approved_by"])
        return inquiry

    def deliver(self, inquiry, *, seller=None, response=None):
        return InquiryDelivery.objects.create(
            inquiry=inquiry, delivered_by=seller or inquiry.listing.seller,
            response_text=response if response is not None else inquiry.approved_response,
        )

    def audit(self, **kwargs):
        output = StringIO()
        call_command("fundplatz_audit", as_json=True, stdout=output, **kwargs)
        return json.loads(output.getvalue())

    def test_01_leere_datenbank_konsistent(self):
        result = self.audit()
        self.assertTrue(result["data_consistent"])
        self.assertFalse(any(result["errors"].values()))

    def test_02_zaehler_ohne_inhalte(self):
        self.make_inquiry()
        result = self.audit()
        self.assertEqual(result["counts"]["listings"], 2)
        self.assertEqual(result["counts"]["inquiries"], 1)
        self.assertEqual(result["counts"]["deliveries"], 0)

    def test_03_freigabe_ohne_text_ist_fehler(self):
        q = self.approve(self.make_inquiry())
        q.approved_response = ""
        q.save(update_fields=["approved_response"])
        self.assertEqual(self.audit()["errors"]["approved_missing_fields"], 1)

    def test_04_freigabe_ohne_zeitpunkt_ist_fehler(self):
        q = self.approve(self.make_inquiry())
        q.approved_at = None
        q.save(update_fields=["approved_at"])
        self.assertEqual(self.audit()["errors"]["approved_missing_fields"], 1)

    def test_05_freigabe_ohne_freigeber_ist_fehler(self):
        q = self.approve(self.make_inquiry())
        q.approved_by = None
        q.save(update_fields=["approved_by"])
        self.assertEqual(self.audit()["errors"]["approved_missing_fields"], 1)

    def test_06_falscher_verkaeufer_in_freigabe_ist_fehler(self):
        self.approve(self.make_inquiry(), seller=self.other_seller)
        self.assertEqual(self.audit()["errors"]["approved_wrong_seller"], 1)

    def test_07_freigabe_payload_ohne_approved_status_ist_fehler(self):
        q = self.make_inquiry()
        q.approved_response = "Vergessener Freigabetext"
        q.save(update_fields=["approved_response"])
        self.assertEqual(self.audit()["errors"]["approval_data_without_approval"], 1)

    def test_08_bereitstellung_ohne_freigabe_ist_fehler(self):
        self.deliver(self.make_inquiry(), response="Falsch bereitgestellt")
        self.assertEqual(self.audit()["errors"]["delivery_without_valid_approval"], 1)

    def test_09_abweichender_kaufertext_ist_fehler(self):
        self.deliver(self.approve(self.make_inquiry()), response="Andere Version!")
        self.assertEqual(self.audit()["errors"]["delivery_text_changed"], 1)

    def test_10_falscher_versender_ist_fehler(self):
        self.deliver(self.approve(self.make_inquiry()), seller=self.other_seller)
        self.assertEqual(self.audit()["errors"]["delivery_wrong_seller"], 1)

    def test_11_bereitstellung_vor_freigabe_ist_fehler(self):
        q = self.approve(self.make_inquiry())
        delivery = self.deliver(q)
        InquiryDelivery.objects.filter(pk=delivery.pk).update(
            delivered_at=q.approved_at - timedelta(minutes=2)
        )
        self.assertEqual(self.audit()["errors"]["delivery_before_approval"], 1)

    def test_12_privates_event_nicht_public(self):
        InquiryEvent.objects.create(
            inquiry=self.make_inquiry(), kind=InquiryEvent.Kind.DRAFT_CREATED,
            audience=InquiryEvent.Audience.BUYER,
        )
        self.assertEqual(self.audit()["errors"]["private_event_marked_public"], 1)

    def test_13_public_event_typen_sind_erlaubt(self):
        q = self.make_inquiry()
        for kind in (InquiryEvent.Kind.RECEIVED, InquiryEvent.Kind.DELIVERED):
            InquiryEvent.objects.create(inquiry=q, kind=kind, audience=InquiryEvent.Audience.BUYER)
        self.assertEqual(self.audit()["errors"]["private_event_marked_public"], 0)

    def test_14_freigegeben_aber_queued_ist_fehler(self):
        q = self.approve(self.make_inquiry())
        q.draft_processing = "queued"
        q.save(update_fields=["draft_processing"])
        self.assertEqual(self.audit()["errors"]["approved_still_queued"], 1)

    def test_15_unbekannter_worker_status_ist_fehler(self):
        q = self.make_inquiry()
        q.draft_processing = "garbage"
        q.save(update_fields=["draft_processing"])
        self.assertEqual(self.audit()["errors"]["unknown_processing_state"], 1)

    def test_16_alter_worker_wird_nur_gemeldet(self):
        q = self.make_inquiry()
        q.draft_processing = "running"
        q.draft_started_at = timezone.now() - timedelta(minutes=50)
        q.save(update_fields=["draft_processing", "draft_started_at"])
        result = self.audit()
        self.assertEqual(result["warnings"]["stale_running"], 1)
        self.assertTrue(result["data_consistent"])

    def test_17_fehlendes_received_event_ist_warnung(self):
        self.make_inquiry()
        self.assertEqual(self.audit()["warnings"]["received_event_missing"], 1)

    def test_18_fehlendes_delivery_event_ist_warnung(self):
        self.deliver(self.approve(self.make_inquiry()))
        self.assertEqual(self.audit()["warnings"]["delivery_event_missing"], 1)

    def test_19_bericht_enthaelt_keine_private_texte(self):
        self.make_inquiry()
        output = StringIO()
        call_command("fundplatz_audit", as_json=True, stdout=output)
        self.assertNotIn("VERTRAULICH", output.getvalue())
        self.assertNotIn("day25_buyer", output.getvalue())
        self.assertNotIn("Fahrrad 5 Euro", output.getvalue())

    def test_20_strict_lehnt_dateninkonsistenz_ab(self):
        self.deliver(self.make_inquiry(), response="Ungerechtfertigt")
        with self.assertRaises(CommandError):
            call_command("fundplatz_audit", strict=True, stdout=StringIO())

    def test_21_strict_laesst_warnung_zu(self):
        self.make_inquiry()  # Kein Received-Event bei direkt angelegter Fixture
        result = self.audit(strict=True)
        self.assertTrue(result["data_consistent"])

    def test_22_stale_grenze_mindestens_fuenf_minuten(self):
        with self.assertRaises(CommandError):
            call_command("fundplatz_audit", stale_minutes=2, stdout=StringIO())

    def test_23_sync_ollama_fehler_ist_failed_nicht_ready(self):
        self.client.force_login(self.buyer)
        with patch("listings.agent_bridge.generate_private_draft", side_effect=RuntimeError("LLM offline")):
            self.client.post(reverse("listings:inquiry_submit", args=[self.listing.pk]),
                             {"message": "Ist das Fahrrad noch da?"})
        q = CustomerInquiry.objects.get()
        self.assertEqual(q.draft_processing, CustomerInquiry.DraftProcessing.FAILED)
        self.assertEqual(q.status, CustomerInquiry.Status.NEEDS_ATTENTION)
        self.assertIsNotNone(q.draft_finished_at)
        self.assertEqual(q.events.filter(kind=InquiryEvent.Kind.DRAFT_FAILED).count(), 1)

    def test_24_sync_erfolg_markiert_ready(self):
        output = SimpleNamespace(
            result=SimpleNamespace(
                combined_draft="Die Versandfrage muss geprueft werden.",
                route=SimpleNamespace(source="rules", agents=("logistics",)), audit=(),
            ), requires_attention=False,
        )
        self.client.force_login(self.buyer)
        with patch("listings.agent_bridge.generate_private_draft", return_value=output):
            self.client.post(reverse("listings:inquiry_submit", args=[self.listing.pk]),
                             {"message": "Ist ein Versand moeglich?"})
        q = CustomerInquiry.objects.get()
        self.assertEqual(q.draft_processing, CustomerInquiry.DraftProcessing.READY)
        self.assertIsNotNone(q.draft_finished_at)
        self.assertEqual(q.events.filter(kind=InquiryEvent.Kind.DRAFT_CREATED).count(), 1)

    def test_25_fremder_seller_sieht_detail_nicht(self):
        q = self.make_inquiry()
        self.client.force_login(self.other_seller)
        self.assertEqual(self.client.get(reverse("listings:seller_inquiry_detail", args=[q.pk])).status_code, 404)

    def test_26_fremder_kaeufer_sieht_detail_nicht(self):
        q = self.make_inquiry()
        self.client.force_login(self.other_buyer)
        self.assertEqual(self.client.get(reverse("listings:buyer_inquiry_detail", args=[q.pk])).status_code, 404)

    def test_27_gueltiger_approved_snapshot_keine_fehler(self):
        self.deliver(self.approve(self.make_inquiry()))
        result = self.audit()
        self.assertFalse(any(result["errors"].values()))

    def test_28_private_drafts_bleiben_nach_delivery_unsichtbar(self):
        q = self.approve(self.make_inquiry())
        self.deliver(q)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("listings:buyer_inquiry_detail", args=[q.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "VERTRAULICH: niemals an Kaeufer")
        self.assertContains(response, "Hallo, ich habe deine Frage")

    def test_29_zwei_inserate_daten_nicht_vermischt(self):
        q1 = self.make_inquiry()
        q2 = self.make_inquiry(listing=self.other_listing)
        a = listing_to_agent_input(q1.listing, q1.message)
        b = listing_to_agent_input(q2.listing, q2.message)
        self.assertEqual((a.product.price_eur, a.product.shipping_available), (Decimal("5.00"), True))
        self.assertEqual((b.product.price_eur, b.product.shipping_available), (Decimal("180.00"), False))
        self.assertNotEqual(a.product.listing_id, b.product.listing_id)

    def test_30_audit_ist_rein_lesend(self):
        q = self.make_inquiry()
        before = (CustomerInquiry.objects.count(), InquiryEvent.objects.count(),
                  InquiryDelivery.objects.count())
        self.audit()
        after = (CustomerInquiry.objects.count(), InquiryEvent.objects.count(),
                 InquiryDelivery.objects.count())
        self.assertEqual(before, after)
        q.refresh_from_db()
        self.assertEqual(q.draft_processing, "ready")
