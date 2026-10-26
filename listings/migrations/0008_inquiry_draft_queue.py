# Phase 3 / Tag 23: Queue-Felder. Altbestand bleibt "ready" und unveraendert.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("listings", "0007_inquiryevent")]

    operations = [
        migrations.AddField(
            model_name="customerinquiry", name="draft_processing",
            field=models.CharField(choices=[
                ("ready", "KI-Entwurf abgeschlossen"),
                ("queued", "KI-Entwurf wartet"),
                ("running", "KI-Entwurf wird erstellt"),
                ("failed", "KI-Entwurf fehlgeschlagen"),
            ], db_index=True, default="ready", max_length=12, verbose_name="KI-Verarbeitung"),
        ),
        migrations.AddField(
            model_name="customerinquiry", name="draft_started_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="KI-Lauf gestartet"),
        ),
        migrations.AddField(
            model_name="customerinquiry", name="draft_finished_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="KI-Lauf beendet"),
        ),
        migrations.AddField(
            model_name="customerinquiry", name="draft_attempts",
            field=models.PositiveIntegerField(default=0, verbose_name="Verarbeitungsversuche"),
        ),
    ]
