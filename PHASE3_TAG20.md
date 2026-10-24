# Fundplatz – Phase 3, Tag 20

## Ziel: Freigegebene Antworten dem richtigen Käufer anzeigen

**Wichtig:** Der bisherige Tag-19-Freigabeklick **sendet nicht automatisch**. Tag 20 ergänzt einen **zweiten, expliziten Schritt**: Der Verkäufer bestätigt auf der Detailseite „Antwort an Käufer bereitstellen“. Erst dann ist die Antwort unter `/meine-anfragen/` für genau den Käufer sichtbar. **Keine E-Mail, SMS oder Nachricht an einen externen Marktplatz wird versendet.**

## Technische Trennung

- `CustomerInquiry.private_draft`: ursprünglicher, nur für Verkäufer sichtbarer KI-Entwurf.
- `CustomerInquiry.seller_draft`: nur für Verkäufer sichtbare Bearbeitung.
- `CustomerInquiry.approved_response`: unveränderlich gedachte interne Freigabe, an Tag 19 erstellt.
- **Neu**: `InquiryDelivery.response_text`: eigene Momentaufnahme der tatsächlich bereitgestellten Antwort. Eine `OneToOneField` verhindert mehrere Zustellungen pro Anfrage; `delivered_at` und `delivered_by` dokumentieren die Bereitstellung.
- **Neu**: `buyer_inquiries` und `buyer_inquiry_detail`: nur der `buyer` der Anfrage darf sie lesen. Die Templates geben ausschließlich Kundenfrage und bereits bereitgestellten Antworttext aus.
- **Neu**: `seller_inquiry_deliver`: `@login_required`, `@require_POST`, Anzeigenbesitzer-Check, bestätigte Verkäuferfreigabe, Bestätigungs-Checkbox, Datenbanktransaktion. Erneute POST-Klicks verändern das Ergebnis nicht.

## Dateien

```text
listings/models.py                         + InquiryDelivery
listings/migrations/0006_inquirydelivery.py
listings/forms.py                          + InquiryDeliveryForm
listings/views.py                          + 3 Views
listings/urls.py                           + 3 Routen
listings/admin.py                          + gesperrte Delivery-Ansicht
listings/templates/listings/buyer_inquiries.html       NEU
listings/templates/listings/buyer_inquiry_detail.html  NEU
listings/templates/listings/seller_inquiry_detail.html ERWEITERT
listings/templates/listings/seller_inquiries.html      ERWEITERT
listings/templates/listings/listing_detail.html        Link zu eigenen Anfragen
listings/templates/listings/my_listings.html           Link zu eigenen Anfragen
templates/base.html                       Navigation ergänzt (Desktop ab XL und Mobil)
listings/test_day20.py                     44 neue Django-Tests
```

## Installation (PowerShell / VS Code mit aktivierter `.venv`)

Die Updates von Tag 16–19 müssen vorher bereits installiert sein. Wenn dein Arbeitsverzeichnis ungesicherte Änderungen enthält, sichere sie vor dem Entpacken.

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag20.zip" -DestinationPath "." -Force
python manage.py migrate
python manage.py makemigrations --check --dry-run
python manage.py test listings.test_day20 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
python manage.py runserver
```

Erwartet nach der Migration: `No changes detected`. Wie viele Django-Tests insgesamt laufen, hängt vom zuvor installierten Projektstand ab. Ohne Tag-20-Tests waren es bereits mehr als 100; dieses Paket ergänzt **44**.

## Browser-Test mit zwei Testkonten

1. Käuferkonto: Eine Anfrage stellen über die Detailseite einer **fremden** Anzeige. Unter `http://127.0.0.1:8000/meine-anfragen/` erscheint sie zunächst mit „Noch keine Antwort“.
2. Verkäuferkonto: `http://127.0.0.1:8000/anfragen/` öffnen und eine Anfrage auswählen. Eigene Antwort unter „Antwortentwurf bearbeiten“ speichern und unter „Antwort prüfen und freigeben“ intern freigeben (Tag 18/19).
3. Verkäuferkonto: Auf derselben Detailseite die neue Checkbox aktivieren und auf **„Antwort an Käufer bereitstellen“** klicken.
4. Käuferkonto: `http://127.0.0.1:8000/meine-anfragen/` erneut laden, Anfrage öffnen. Jetzt steht dort ausschließlich der veröffentlichte Antworttext – keine `private_draft`-/`seller_draft`-/`audit`-Information.
5. Anderes Käuferkonto: Dieselbe `/meine-anfragen/ID/`-Adresse muss **404** liefern. Öffentliche Anzeigenseiten zeigen keine Kundenantworten an.
6. Ältere Anfragen, die an Tag 19 lediglich intern freigegeben wurden, bleiben zunächst verborgen, bis ein Verkäufer sie ausdrücklich bereitstellt.

## Warum keine automatische Veröffentlichung?

Eine interne Freigabe aus Tag 19 ist eine menschliche Prüfung; Tag 20 ist ein separater Zustell-Entschluss. Damit können bestehende, intern freigegebene Antworten **nicht unbemerkt** durch ein Softwareupdate öffentlich werden. Außerdem bleiben alle internen Entwürfe auch nach der Zustellung ausschließlich für den Verkäufer zugänglich.

## Grenzen

- Die Antwort wird nur in der eingeloggten Fundplatz-Käuferansicht angezeigt. Keine externe Zustellung, E-Mail oder Push-Nachricht.
- Nach der Bereitstellung gibt es in dieser Version keine nachträgliche Korrektur oder Rücknahme. Solche Schritte brauchen eine eigene, protokollierte Versionierung.
- Das Python-LLM läuft nicht für die Zustellung; die schon freigegebene Antwort wird als Snapshot gespeichert.
- `response_text` ist gegen versehentliche Veränderung über die Views/Admin gesperrt, aber Datenbankadministratoren können Daten weiterhin direkt ändern. Absolute technische Unveränderlichkeit ist nicht behauptet.

## Github

```powershell
git add listings templates/base.html PHASE3_TAG20.md
git commit -m "Phase 3 Tag 20: Kaeuferpostfach und Antwortbereitstellung"
git push
```
