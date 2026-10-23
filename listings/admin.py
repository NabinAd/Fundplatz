"""Schlanke Anzeigenverwaltung im eingebauten Django-Admin."""
from django.contrib import admin
from .models import Listing


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title", "price", "category", "condition", "is_active", "created_at"
    )
    list_filter = ("category", "condition", "is_active")
    search_fields = ("title", "description", "location")
    readonly_fields = ("created_at", "updated_at")
    exclude = ("seller",)

    def save_model(self, request, obj, form, change):
        # Bei neuen Anzeigen gehört der Datensatz dem angemeldeten Admin.
        if not change:
            obj.seller = request.user
        super().save_model(request, obj, form, change)


from .models import CustomerInquiry


@admin.register(CustomerInquiry)
class CustomerInquiryAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "buyer", "status", "route_source", "created_at")
    list_filter = ("status", "route_source")
    search_fields = ("message", "listing__title", "buyer__username")
    readonly_fields = (
        "listing", "buyer", "message", "private_draft", "status",
        "route_source", "selected_agents", "audit", "created_at",
    )

    def has_add_permission(self, request):
        return False
