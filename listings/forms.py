"""Schlankes Anzeigenformular für Phase 1, Tag 3 (ohne KI)."""
from django import forms

from .models import Listing


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        # Absichtlich kein 'seller': Die View setzt den Besitzer selbst.
        fields = [
            "title", "description", "price", "category", "condition", "image",
            "location", "shipping_available", "pickup_available",
            "is_negotiable", "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Das Bild darf höchstens 5 MB groß sein.")
        return image
