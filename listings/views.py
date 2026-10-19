"""Tag 1: Startseite mit den sechs neuesten aktiven Anzeigen."""
from django.shortcuts import render
from .models import Listing


def home(request):
    active_listings = Listing.objects.filter(is_active=True)
    context = {
        "listing_count": active_listings.count(),
        "listings": active_listings[:6],
    }
    return render(request, "listings/home.html", context)
