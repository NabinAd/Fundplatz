# Phase 3, Tag 17: zusätzliche, rein interne Statusstufe.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("listings", "0002_customerinquiry")]

    operations = [
        migrations.AlterField(
            model_name="customerinquiry",
            name="status",
            field=models.CharField(
                "Bearbeitungsstatus",
                max_length=24,
                choices=[
                    ("review_required", "Verkäuferprüfung erforderlich"),
                    ("needs_attention", "Manuelle Bearbeitung erforderlich"),
                    ("in_progress", "In Bearbeitung"),
                ],
                default="needs_attention",
            ),
        ),
    ]
