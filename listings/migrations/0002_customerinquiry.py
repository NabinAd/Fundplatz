# Phase 3, Tag 16: Kundenanfragen und private Antwortentwürfe
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerInquiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.TextField(max_length=2000, verbose_name="Kundenfrage")),
                ("private_draft", models.TextField(blank=True, verbose_name="Privater Antwortentwurf")),
                ("status", models.CharField(choices=[("review_required", "Verkäuferprüfung erforderlich"), ("needs_attention", "Manuelle Bearbeitung erforderlich")], default="needs_attention", max_length=24, verbose_name="Bearbeitungsstatus")),
                ("route_source", models.CharField(blank=True, max_length=12, verbose_name="Routerquelle")),
                ("selected_agents", models.JSONField(blank=True, default=list, verbose_name="Ausgewählte Agenten")),
                ("audit", models.JSONField(blank=True, default=list, verbose_name="Prüfhinweise")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Erstellt")),
                ("buyer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="customer_inquiries", to=settings.AUTH_USER_MODEL, verbose_name="Interessent")),
                ("listing", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="customer_inquiries", to="listings.listing", verbose_name="Anzeige")),
            ],
            options={
                "verbose_name": "Kundenanfrage",
                "verbose_name_plural": "Kundenanfragen",
                "ordering": ["-created_at"],
            },
        ),
    ]
