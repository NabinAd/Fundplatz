"""Tag 19: ausdrückliche interne Freigabe, KEIN Versand/keine Käuferansicht."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0004_customerinquiry_seller_draft"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="customerinquiry", name="approved_response",
            field=models.TextField("Freigegebene Antwort (nur intern)", blank=True, max_length=3000),
        ),
        migrations.AddField(
            model_name="customerinquiry", name="approved_at",
            field=models.DateTimeField("Freigabezeitpunkt", blank=True, null=True),
        ),
        migrations.AddField(
            model_name="customerinquiry", name="approved_by",
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.SET_NULL,
                blank=True, null=True, related_name="approved_customer_inquiries",
                verbose_name="Freigegeben von",
            ),
        ),
        migrations.AlterField(
            model_name="customerinquiry", name="status",
            field=models.CharField(
                "Bearbeitungsstatus", default="needs_attention", max_length=24,
                choices=[
                    ("review_required", "Verkäuferprüfung erforderlich"),
                    ("needs_attention", "Manuelle Bearbeitung erforderlich"),
                    ("in_progress", "In Bearbeitung"),
                    ("approved", "Vom Verkäufer freigegeben"),
                ],
            ),
        ),
    ]
