from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("", views.home, name="home"),
    path("anzeigen/", views.listing_list, name="listing_list"),
    path("anzeigen/neu/", views.listing_create, name="listing_create"),
    path("meine-anzeigen/", views.my_listings, name="my_listings"),
    path("anzeigen/<int:pk>/", views.listing_detail, name="listing_detail"),
    path("anzeigen/<int:pk>/bearbeiten/", views.listing_update, name="listing_update"),
    path("anzeigen/<int:pk>/loeschen/", views.listing_delete, name="listing_delete"),
]
