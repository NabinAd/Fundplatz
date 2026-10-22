"""Öffentliche Ansichten für den Marketplace (Phase 1, Tag 2)."""
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Listing


def home(request):
    """Zeige die sechs neuesten aktiven Anzeigen auf der Startseite."""
    active_listings = Listing.objects.filter(is_active=True)
    context = {
        "listing_count": active_listings.count(),
        "listings": active_listings[:6],
    }
    return render(request, "listings/home.html", context)


def listing_list(request):
    """Zeige aktive Anzeigen in Seiten zu je zwölf Einträgen."""
    active_listings = Listing.objects.filter(is_active=True)
    paginator = Paginator(active_listings, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "listings/listing_list.html", {"page_obj": page_obj})


def listing_detail(request, pk):
    """Zeige Details nur für aktive Anzeigen; sonst HTTP 404."""
    listing = get_object_or_404(
        Listing.objects.select_related("seller"), pk=pk, is_active=True
    )
    return render(request, "listings/listing_detail.html", {"listing": listing})
