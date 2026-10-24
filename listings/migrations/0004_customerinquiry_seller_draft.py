# Phase 3, Tag 18: Verkäufertext getrennt vom originalen KI-Entwurf speichern.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("listings", "0003_customerinquiry_in_progress")]

    operations = [
        migrations.AddField(
            model_name="customerinquiry",
            name="seller_draft",
            field=models.TextField(
                "Vom Verkäufer bearbeiteter Entwurf", blank=True, max_length=3000,
            ),
        ),
        migrations.AddField(
            model_name="customerinquiry",
            name="seller_draft_updated_at",
            field=models.DateTimeField(
                "Entwurf zuletzt gespeichert", blank=True, null=True,
            ),
        ),
    ]
