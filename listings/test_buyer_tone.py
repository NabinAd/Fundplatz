"""Tag23 Tonfall: nur private, nicht freigegebene Voransicht."""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Listing, CustomerInquiry


class BuyerFriendlyPreviewTests(TestCase):
    def setUp(self):
        u=get_user_model()
        self.seller=u.objects.create_user(username="tone_seller", password="pwSafe_12345")
        self.buyer=u.objects.create_user(username="tone_buyer", password="pwSafe_12345")
        self.listing=Listing.objects.create(seller=self.seller,title="Beispiel",description="Gebraucht",
            price=Decimal("5.00"),shipping_available=True,is_negotiable=True)
        self.inquiry=CustomerInquiry.objects.create(listing=self.listing,buyer=self.buyer,
            message="Ist Versand möglich, und würdest du 180 € akzeptieren?",
            private_draft="Laut Anzeige ist Versand möglich. Der Preis beträgt 5 €.",
            selected_agents=["logistics","negotiation"],
            status=CustomerInquiry.Status.REVIEW_REQUIRED)

    def test_verkaeufer_sieht_kaeuferfreundliche_variante(self):
        self.client.force_login(self.seller)
        response=self.client.get(reverse("listings:seller_inquiry_detail", args=[self.inquiry.pk]))
        self.assertContains(response,"Käuferfreundliche Formulierung")
        self.assertContains(response,"180,00 € genannt")

    def test_editor_wird_mit_freundlicher_fassung_vorbelegt(self):
        self.client.force_login(self.seller)
        response=self.client.get(reverse("listings:seller_inquiry_edit", args=[self.inquiry.pk]))
        self.assertIn("Hallo!",response.context["form"].initial["seller_draft"])

    def test_ki_original_bleibt_gespeichert(self):
        self.client.force_login(self.seller)
        self.client.get(reverse("listings:seller_inquiry_detail", args=[self.inquiry.pk]))
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.private_draft,"Laut Anzeige ist Versand möglich. Der Preis beträgt 5 €.")
        self.assertIsNone(self.inquiry.seller_draft_updated_at)

    def test_kaeufer_sieht_keinen_privaten_vorschlag(self):
        self.client.force_login(self.buyer)
        response=self.client.get(reverse("listings:buyer_inquiry_detail", args=[self.inquiry.pk]))
        self.assertNotContains(response,"Hallo!",html=False)
        self.assertNotContains(response,"180,00 € genannt",html=False)

    def test_kritischer_fall_keine_auto_vorbelegung(self):
        self.inquiry.status=CustomerInquiry.Status.NEEDS_ATTENTION
        self.inquiry.save(update_fields=["status"])
        self.client.force_login(self.seller)
        response=self.client.get(reverse("listings:seller_inquiry_edit",args=[self.inquiry.pk]))
        self.assertEqual(response.context["form"].initial["seller_draft"],"")
