# Phase 3 / Tag 20: Käuferantwort separat und erst nach ausdrücklichem Versand.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0005_customerinquiry_approval"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InquiryDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("response_text", models.TextField(max_length=3000, verbose_name="Bereitgestellte Antwort")),
                ("delivered_at", models.DateTimeField(auto_now_add=True, verbose_name="Bereitgestellt am")),
                ("delivered_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="inquiry_deliveries", to=settings.AUTH_USER_MODEL, verbose_name="Bereitgestellt von")),
                ("inquiry", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="delivery", to="listings.customerinquiry", verbose_name="Kundenanfrage")),
            ],
            options={
                "verbose_name": "Bereitgestellte Antwort",
                "verbose_name_plural": "Bereitgestellte Antworten",
                "ordering": ["-delivered_at"],
            },
        ),
    ]
