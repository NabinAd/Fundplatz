# Tag 21 – Ereignisse und vorsichtige Übernahme vorhandener Zeitpunkte.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def backfill_history(apps, schema_editor):
    Inquiry = apps.get_model("listings", "CustomerInquiry")
    Delivery = apps.get_model("listings", "InquiryDelivery")
    Event = apps.get_model("listings", "InquiryEvent")
    db = schema_editor.connection.alias
    deliveries = {d.inquiry_id: d for d in Delivery.objects.using(db).all()}
    batch = []
    for q in Inquiry.objects.using(db).iterator(chunk_size=200):
        # Der Eingang hat einen tatsächlichen gespeicherten Zeitstempel.
        batch.append(Event(
            inquiry_id=q.pk, kind="received", audience="buyer",
            actor_id=q.buyer_id, occurred_at=q.created_at,
        ))
        # Für alte KI-Entwürfe gibt es kein separates Zeitfeld: keine
        # vermeintlich exakten Zeitpunkte erfinden.
        if q.seller_draft_updated_at is not None:
            batch.append(Event(
                inquiry_id=q.pk, kind="seller_draft_saved", audience="seller",
                actor_id=q.listing.seller_id, occurred_at=q.seller_draft_updated_at,
            ))
        if q.approved_at is not None and q.approved_response:
            batch.append(Event(
                inquiry_id=q.pk, kind="approved", audience="seller",
                actor_id=q.approved_by_id, occurred_at=q.approved_at,
            ))
        delivered = deliveries.get(q.pk)
        if delivered is not None:
            batch.append(Event(
                inquiry_id=q.pk, kind="delivered", audience="buyer",
                actor_id=delivered.delivered_by_id, occurred_at=delivered.delivered_at,
            ))
        if len(batch) >= 500:
            Event.objects.using(db).bulk_create(batch, batch_size=500)
            batch.clear()
    if batch:
        Event.objects.using(db).bulk_create(batch, batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0006_inquirydelivery"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InquiryEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[
                    ("received", "Kundenanfrage eingegangen"),
                    ("draft_created", "Interner Antwortentwurf erstellt"),
                    ("draft_failed", "Automatischer Entwurf fehlgeschlagen"),
                    ("started", "Verkäufer hat Bearbeitung begonnen"),
                    ("seller_draft_saved", "Verkäuferentwurf gespeichert"),
                    ("approved", "Antwort intern freigegeben"),
                    ("delivered", "Antwort für Käufer bereitgestellt"),
                ], max_length=24, verbose_name="Ereignis")),
                ("audience", models.CharField(choices=[
                    ("buyer", "Für Käufer sichtbar"),
                    ("seller", "Nur für Verkäufer"),
                ], default="seller", max_length=8, verbose_name="Sichtbarkeit")),
                ("occurred_at", models.DateTimeField(db_index=True, default=timezone.now, verbose_name="Ereigniszeitpunkt")),
                ("actor", models.ForeignKey(
                    to=settings.AUTH_USER_MODEL, null=True, blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="inquiry_events", verbose_name="Ausgelöst von",
                )),
                ("inquiry", models.ForeignKey(
                    to="listings.customerinquiry", on_delete=django.db.models.deletion.CASCADE,
                    related_name="events", verbose_name="Kundenanfrage",
                )),
            ],
            options={
                "verbose_name": "Anfrageereignis",
                "verbose_name_plural": "Anfrageereignisse",
                "ordering": ["occurred_at", "pk"],
            },
        ),
        migrations.AddIndex(
            model_name="inquiryevent",
            index=models.Index(fields=["inquiry", "occurred_at"], name="inquiry_event_when_idx"),
        ),
        migrations.RunPython(backfill_history, reverse_code=migrations.RunPython.noop),
    ]
