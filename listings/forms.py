"""Formulare für Anzeigen, Suchfilter und Registrierung (ohne KI)."""
from decimal import Decimal

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import CustomerInquiry, Listing


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


class ListingFilterForm(forms.Form):
    """GET-Parameter explizit validieren, statt Rohdaten in Queries zu übernehmen."""
    q = forms.CharField(
        label="Suchbegriff", max_length=120, required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": "z. B. Fahrrad, Laptop …"
        }),
    )
    category = forms.ChoiceField(
        label="Kategorie", required=False,
        choices=[("", "Alle Kategorien"), *Listing.Category.choices],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    min_price = forms.DecimalField(
        label="Preis ab (€)", required=False, min_value=Decimal("0"),
        max_digits=9, decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "form-control", "min": "0", "step": "0.01", "placeholder": "0"
        }),
    )
    max_price = forms.DecimalField(
        label="Preis bis (€)", required=False, min_value=Decimal("0"),
        max_digits=9, decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "form-control", "min": "0", "step": "0.01", "placeholder": "500"
        }),
    )

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("min_price"), cleaned.get("max_price")
        if low is not None and high is not None and low > high:
            raise forms.ValidationError(
                "Der Mindestpreis darf nicht größer als der Höchstpreis sein."
            )
        return cleaned


class SignupForm(UserCreationForm):
    """Verwendet Djangos Passwort- und Benutzernamenvalidierung."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        labels = {
            "username": "Benutzername",
            "password1": "Passwort",
            "password2": "Passwort wiederholen",
        }
        for name, field in self.fields.items():
            field.label = labels.get(name, field.label)
            field.widget.attrs["class"] = "form-control"
            if name == "username":
                field.widget.attrs["autocomplete"] = "username"
            elif name == "password1":
                field.widget.attrs["autocomplete"] = "new-password"
            elif name == "password2":
                field.widget.attrs["autocomplete"] = "new-password"


class CustomerInquiryForm(forms.Form):
    """Käuferfrage, keine Eingabemöglichkeit für Seller/Status/Preisregeln."""

    message = forms.CharField(
        label="Deine Frage an den Verkäufer",
        min_length=5,
        max_length=2000,
        strip=True,
        widget=forms.Textarea(attrs={
            "class": "form-control", "rows": 4,
            "placeholder": "z. B. Ist Versand möglich und wäre der Preis verhandelbar?",
        }),
    )


class SellerInquiryFilterForm(forms.Form):
    """Nur Listenfilter. Der Verkäufer wird immer serverseitig bestimmt."""

    q = forms.CharField(
        label="Suche", max_length=120, required=False, strip=True,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": "Artikel, Frage oder Käufer",
        }),
    )
    status = forms.ChoiceField(
        label="Status", required=False,
        choices=[("", "Alle Status"), *CustomerInquiry.Status.choices],
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class SellerDraftForm(forms.Form):
    """Nur den privaten Verkäufertext bearbeiten; keine Freigabe-Felder."""

    seller_draft = forms.CharField(
        label="Deine Antwort an den Interessenten (noch nicht gesendet)",
        min_length=5, max_length=3000, strip=True,
        widget=forms.Textarea(attrs={
            "class": "form-control", "rows": 10,
            "placeholder": "Formuliere eine sachliche, korrekte Antwort ...",
            "autocomplete": "off",
        }),
        help_text="5 bis 3000 Zeichen. Der Text wird nur privat gespeichert.",
    )


class SellerApprovalForm(forms.Form):
    """Freigabe erfordert einen bewussten, expliziten Verkäufer-POST."""
    draft_token = forms.CharField(widget=forms.HiddenInput)
    confirmed = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Ich habe den gesamten Antworttext einschließlich Preise, Zustand und Versandbedingungen selbst geprüft.",
    )
    confirmation_word = forms.CharField(
        label='Zur Bestätigung „FREIGEBEN“ eingeben',
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
    )

    def clean_confirmation_word(self):
        value = self.cleaned_data["confirmation_word"].strip()
        if value != "FREIGEBEN":
            raise forms.ValidationError('Bitte genau „FREIGEBEN“ eingeben.')
        return value



class InquiryDeliveryForm(forms.Form):
    """Ausdrückliche Bestätigung unmittelbar vor Sichtbarmachung beim Käufer."""

    confirmed = forms.BooleanField(
        required=True,
        label="Ich möchte diese freigegebene Antwort dem Käufer anzeigen.",
        error_messages={"required": "Bitte bestätige das Bereitstellen der Antwort."},
    )
