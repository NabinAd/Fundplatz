from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("", views.home, name="home"),
    path("anzeigen/", views.listing_list, name="listing_list"),
    path("anzeigen/<int:pk>/", views.listing_detail, name="listing_detail"),
]
