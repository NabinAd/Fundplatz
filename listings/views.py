"""Marketplace-Views: öffentlich lesen, eigene Anzeigen sicher verwalten."""
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import (
    CustomerInquiryForm, ListingFilterForm, ListingForm,
    SellerInquiryFilterForm, SignupForm,
)
from .models import CustomerInquiry, Listing


def home(request):
    active_listings = Listing.objects.filter(is_active=True)
    return render(request, "listings/home.html", {
        "listing_count": active_listings.count(),
        "listings": active_listings[:6],
    })


def listing_list(request):
    """Suche und Filter kombinieren (AND), Titel/Beschreibung als OR."""
    filter_form = ListingFilterForm(request.GET)
    listings = Listing.objects.filter(is_active=True)
    if filter_form.is_valid():
        filters = filter_form.cleaned_data
        if filters["q"]:
            listings = listings.filter(
                Q(title__icontains=filters["q"])
                | Q(description__icontains=filters["q"])
            )
        if filters["category"]:
            listings = listings.filter(category=filters["category"])
        if filters["min_price"] is not None:
            listings = listings.filter(price__gte=filters["min_price"])
        if filters["max_price"] is not None:
            listings = listings.filter(price__lte=filters["max_price"])
    else:
        # Ungültige Parameter nicht stillschweigend ignorieren.
        listings = listings.none()

    paginator = Paginator(listings, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Nur die vier bekannten Filter auf Folgeseiten mitgeben.
    query_params = request.GET.copy()
    for key in list(query_params):
        if key not in {"q", "category", "min_price", "max_price"}:
            del query_params[key]
    return render(request, "listings/listing_list.html", {
        "page_obj": page_obj,
        "filter_form": filter_form,
        "filter_query": query_params.urlencode(),
    })


def listing_detail(request, pk):
    listing = get_object_or_404(
        Listing.objects.select_related("seller"), pk=pk, is_active=True
    )
    return render(request, "listings/listing_detail.html", {
        "listing": listing, "inquiry_form": CustomerInquiryForm(),
    })


# Auch deaktivierte eigene Anzeigen erscheinen in dieser Verwaltung.
@login_required
def my_listings(request):
    listings = Listing.objects.filter(seller=request.user)
    return render(request, "listings/my_listings.html", {"listings": listings})


@login_required
def listing_create(request):
    form = ListingForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        listing = form.save(commit=False)
        listing.seller = request.user  # niemals aus dem Formular übernehmen
        listing.save()
        messages.success(request, "Deine Anzeige wurde erstellt.")
        if listing.is_active:
            return redirect("listings:listing_detail", pk=listing.pk)
        return redirect("listings:my_listings")
    return render(request, "listings/listing_form.html", {
        "form": form, "page_title": "Anzeige erstellen", "submit_label": "Anzeige speichern"
    })


@login_required
def listing_update(request, pk):
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)
    form = ListingForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=listing,
    )
    if request.method == "POST" and form.is_valid():
        listing = form.save()
        messages.success(request, "Deine Änderungen wurden gespeichert.")
        if listing.is_active:
            return redirect("listings:listing_detail", pk=listing.pk)
        return redirect("listings:my_listings")
    return render(request, "listings/listing_form.html", {
        "form": form, "listing": listing, "page_title": "Anzeige bearbeiten",
        "submit_label": "Änderungen speichern",
    })


@login_required
def listing_delete(request, pk):
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)
    if request.method == "POST":
        listing.delete()
        messages.success(request, "Die Anzeige wurde gelöscht.")
        return redirect("listings:my_listings")
    return render(request, "listings/listing_confirm_delete.html", {
        "listing": listing
    })


@login_required
@require_POST
def listing_toggle_active(request, pk):
    """Nur der Eigentümer darf seine Anzeige per POST aktivieren/deaktivieren."""
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)
    listing.is_active = not listing.is_active
    listing.save(update_fields=["is_active", "updated_at"])
    messages.success(
        request, "Anzeige aktiviert." if listing.is_active else "Anzeige deaktiviert."
    )
    return redirect("listings:my_listings")


# Registrierung für lokale Testnutzer; keine externe E-Mail-Bestätigung im MVP.
def signup(request):
    if request.user.is_authenticated:
        return redirect("listings:my_listings")
    form = SignupForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Dein Konto wurde erstellt. Willkommen bei Fundplatz!")
        return redirect("listings:my_listings")
    return render(request, "registration/signup.html", {"form": form})


# Phase 3, Tag 16. Die Frage wird nur gespeichert; sie wird NICHT versendet.
logger = logging.getLogger(__name__)


@login_required
@require_POST
def inquiry_submit(request, pk):
    """Ein Käufer stellt eine Frage. Private Agentenantwort bleibt beim Verkäufer."""
    listing = get_object_or_404(Listing, pk=pk, is_active=True)
    if listing.seller_id == request.user.pk:
        messages.error(request, "Du kannst deine eigene Anzeige nicht anfragen.")
        return redirect("listings:listing_detail", pk=pk)

    form = CustomerInquiryForm(request.POST)
    if not form.is_valid():
        return render(request, "listings/listing_detail.html", {
            "listing": listing, "inquiry_form": form,
        }, status=400)

    # Einfaches Limit gegen versehentliches oder massenhaftes Absenden.
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_count = CustomerInquiry.objects.filter(
        buyer=request.user, created_at__gte=one_hour_ago,
    ).count()
    if recent_count >= 5:
        messages.error(request, "Maximal fünf Anfragen pro Stunde. Bitte versuche es später.")
        return redirect("listings:listing_detail", pk=pk)

    inquiry = CustomerInquiry.objects.create(
        listing=listing, buyer=request.user, message=form.cleaned_data["message"],
    )
    try:
        from .agent_bridge import generate_private_draft

        output = generate_private_draft(
            listing, inquiry.message,
            use_llm=getattr(settings, "FUNDPLATZ_AGENT_USE_LLM", False),
        )
        result = output.result
        inquiry.private_draft = result.combined_draft
        inquiry.route_source = result.route.source
        inquiry.selected_agents = list(result.route.agents)
        inquiry.audit = [item.to_dict() for item in result.audit]
        inquiry.status = (
            CustomerInquiry.Status.NEEDS_ATTENTION
            if output.requires_attention
            else CustomerInquiry.Status.REVIEW_REQUIRED
        )
    except Exception:
        # Die Käuferanfrage bleibt gespeichert, auch wenn der Agentenlauf scheitert.
        # Fehlermeldungen (z. B. von Ollama) nie an den Käufer ausgeben.
        logger.exception("Privater Antwortentwurf für Anfrage %s fehlgeschlagen", inquiry.pk)
        inquiry.private_draft = "Kein automatischer Entwurf verfügbar. Bitte manuell antworten."
        inquiry.status = CustomerInquiry.Status.NEEDS_ATTENTION
    inquiry.save(update_fields=[
        "private_draft", "status", "route_source", "selected_agents", "audit",
    ])
    messages.success(
        request, "Deine Frage wurde gespeichert. Ein Antwortvorschlag wird nur dem Verkäufer angezeigt."
    )
    return redirect("listings:listing_detail", pk=pk)


@login_required
@require_GET
def seller_inquiries(request):
    """Eigene Anfragen filtern und paginieren, niemals fremde Entwürfe laden."""
    own = CustomerInquiry.objects.filter(listing__seller=request.user)
    filter_form = SellerInquiryFilterForm(request.GET)
    inquiries = own.select_related("listing", "buyer")

    if filter_form.is_valid():
        values = filter_form.cleaned_data
        if values["status"]:
            inquiries = inquiries.filter(status=values["status"])
        if values["q"]:
            inquiries = inquiries.filter(
                Q(listing__title__icontains=values["q"])
                | Q(message__icontains=values["q"])
                | Q(buyer__username__icontains=values["q"])
            )
    else:
        # Fehlerhafte Filter führen nicht zur unbemerkten breiten Auflistung.
        inquiries = inquiries.none()

    page_obj = Paginator(inquiries.order_by("-created_at", "-pk"), 10).get_page(
        request.GET.get("page")
    )
    return render(request, "listings/seller_inquiries.html", {
        "page_obj": page_obj,
        "inquiries": page_obj,  # für kompatible Template-Tests aus Tag 16
        "filter_form": filter_form,
        "total_count": own.count(),
        "review_count": own.filter(status=CustomerInquiry.Status.REVIEW_REQUIRED).count(),
        "attention_count": own.filter(status=CustomerInquiry.Status.NEEDS_ATTENTION).count(),
        "progress_count": own.filter(status=CustomerInquiry.Status.IN_PROGRESS).count(),
        "filter_query": _inquiry_filter_query(request),
    })


def _inquiry_filter_query(request):
    """Beim Blättern nur die validen Suchparameter erhalten."""
    allowed = request.GET.copy()
    for key in list(allowed):
        if key not in {"q", "status"}:
            del allowed[key]
    return allowed.urlencode()


@login_required
@require_GET
def seller_inquiry_detail(request, pk):
    """Private Detailansicht; Existenz fremder Anfragen nicht preisgeben."""
    inquiry = get_object_or_404(
        CustomerInquiry.objects.select_related("listing", "buyer"),
        pk=pk,
        listing__seller=request.user,
    )
    return render(request, "listings/seller_inquiry_detail.html", {
        "inquiry": inquiry,
    })


@login_required
@require_POST
def seller_inquiry_start(request, pk):
    """Ausdrücklicher Verkäuferklick setzt nur internen Status, kein Versand."""
    inquiry = get_object_or_404(
        CustomerInquiry,
        pk=pk,
        listing__seller=request.user,
    )
    if inquiry.status != CustomerInquiry.Status.IN_PROGRESS:
        inquiry.status = CustomerInquiry.Status.IN_PROGRESS
        inquiry.save(update_fields=["status"])
        messages.success(request, "Anfrage als 'In Bearbeitung' markiert.")
    return redirect("listings:seller_inquiry_detail", pk=inquiry.pk)
