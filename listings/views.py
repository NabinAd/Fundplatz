"""Marketplace-Views: öffentlich lesen, eigene Anzeigen sicher verwalten."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ListingFilterForm, ListingForm, SignupForm
from .models import Listing


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
    return render(request, "listings/listing_detail.html", {"listing": listing})


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
