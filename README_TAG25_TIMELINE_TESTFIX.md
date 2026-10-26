# Fundplatz – Tag-25-Abnahme: letzter Django-Testfehler

## Problem

Beim Abschlusslauf bestanden 30/30 Tag-25-Tests und 281/281 Agententests; der Audit berichtete `data_consistent: true` bei 0 Fehlern und 0 Warnungen. In der Django-Gesamtsuite (430 Tests) scheiterte nur:

`listings.test_day21.InquiryTimelineDay21Tests.test_39_legacy_backfill_keeps_real_timestamps`

Im ursprünglichen `setUpTestData` wird `seller_draft_updated_at=timezone.now()` bereits **vor** dem INSERT der Anfrage ausgewertet. Das Feld `created_at` wird jedoch per `auto_now_add` **erst während** des INSERT gesetzt. Dadurch liegt der künstliche Entwurfszeitpunkt gelegentlich einige Mikrosekunden vor dem künstlichen Eingangszeitpunkt. Die Ereignisse sind nach `occurred_at` sortiert; die Migration verhält sich daher korrekt, aber die Testdaten widersprechen der erwarteten Reihenfolge.

## Korrektur

Nur `listings/test_day21.py` wird ausgetauscht. Test 39 legt vier ausdrücklich chronologische Alt-Zeitstempel an (Eingang, Entwurf, Freigabe, Bereitstellung) und kontrolliert danach weiterhin, dass die Backfill-Migration alle **original gespeicherten** Zeitpunkte unverändert übernimmt.

- Kein Eingriff in `0007_inquiryevent.py`.
- Keine Migration erforderlich.
- Keine Veränderung an echten Kundenanfragen, Anzeigen, Konten oder KI-Entwürfen.
- Vorheriger Async-Testfix für Tag 16/21 bleibt erhalten.

## Installation (PowerShell, `.venv` aktiv)

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag25_timeline_testfix.zip" -DestinationPath "." -Force
python manage.py test listings.test_day21.InquiryTimelineDay21Tests.test_39_legacy_backfill_keeps_real_timestamps -v 2
python manage.py test listings
.\scripts\tag25_abnahme.ps1
```

Das Abnahmeskript schreibt den Diagnosebericht nach `tag25_reports`, siehe Tag-25-Anleitung. Diese Berichte bitte nicht in ein öffentliches GitHub-Repository hochladen.

## Verifikation

Python-Syntax, isolierter Test-Methodenunterschied und ZIP-Integrität wurden in der Erstellungsumgebung geprüft. Django ist dort nicht installiert, daher muss der wirkliche Django-Testlauf auf deinem Windows-PC erfolgen.
