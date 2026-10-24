# Fundplatz – Phase 3, Tag 21: Nachrichten- und Statusverlauf

## Ziel

Nachvollziehbarer Ablauf für eine Kundenanfrage: Eingang → privater Agentenlauf → Bearbeitungsbeginn → Verkäuferentwurf → interne Freigabe → Bereitstellung an Käufer.

Wir speichern **Ereignisse** (`InquiryEvent`) zusätzlich zu `CustomerInquiry` und `InquiryDelivery`. Ein Event enthält nur: Anfrage, Ereignistyp, Sichtbarkeit, auslösender Benutzer und Zeitpunkt. Es enthält **keine Kopie von KI-Entwürfen, Kundenfragen, persönlichen Nachrichten oder Audit-Daten**.

Die Verkäufer-Detailseite zeigt alle Ereignisse der eigenen Anzeige. Die Käufer-Detailseite zeigt **nur zwei** Ereignistypen: „Kundenanfrage eingegangen“ und „Antwort für Käufer bereitgestellt“. Bei Freigabe ohne Bereitstellung sieht der Käufer noch nichts von der Verkäuferantwort.

## Installation (Windows, PowerShell, aktivierte .venv)

**Voraussetzung: Tag 20 ist installiert, Migration 0006 wurde ausgeführt.**

```powershell
cd C:\Kleinanzeigen
git status
```

Lokale Datenbank vor der Migration sichern, falls vorhanden:

```powershell
Copy-Item .\db.sqlite3 .\db_backup_vor_tag21.sqlite3
```

Dateien aus `fundplatz_phase3_tag21.zip` entpacken:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag21.zip" -DestinationPath "." -Force
python manage.py migrate
python manage.py makemigrations --check --dry-run
```

## Tests

```powershell
python manage.py test listings.test_day21 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
```

Es gibt **40 neue Django-Tests** in `listings/test_day21.py`, unter anderem zu Zugriffsrechten, erzeugten Events, doppelten Aktionen, altem Datenbestand und Rollback beim Protokollfehler.

In der Entwicklungsumgebung, in der das ZIP erstellt wurde, ist Django nicht installiert und konnte auch nicht nachinstalliert werden. **Der Django-Testlauf konnte daher hier nicht ausgeführt werden.** Die Python-Dateien wurden auf Syntax und das ZIP auf Integrität geprüft. Bitte den Django-Teststatus auf deinem Windows-Rechner kontrollieren.

## Im Browser ausprobieren

```powershell
python manage.py runserver
```

1. Als Käufer eine Frage zu einer fremden Anzeige stellen. Die Frage erscheint unter `http://127.0.0.1:8000/meine-anfragen/`.
2. Als Verkäufer `http://127.0.0.1:8000/anfragen/` öffnen, die neue Frage auswählen und den **internen Verlauf** ansehen. „Anfrage eingegangen“ und „Interner Antwortentwurf erstellt“ (oder „Automatischer Entwurf fehlgeschlagen“) sind sichtbar.
3. „Als In Bearbeitung markieren“, privaten Verkäufertext bearbeiten und speichern. Beide Aktionen erzeugen separate Zeitpunkte.
4. Die Antwort ausdrücklich freigeben. Der Käufer sieht **noch keine** freigegebene Antwort.
5. Erst bei „Antwort an Käufer bereitstellen“ wird ein öffentlicher Verlaufseintrag erzeugt; der Käufer sieht dann auch die Antwort.
6. Eine beliebige fremde Anfragen-ID in der URL darf kein anderer Nutzer öffnen (404).

## Dateien und Architektur

```text
listings/
├── models.py                          # InquiryEvent
├── inquiry_timeline.py                # Event-Helfer und Sichtbarkeitsfilter
├── views.py                           # atomare Ereignisaufzeichnung in bestehenden Aktionen
├── admin.py                           # Ereignisse im Admin nur lesbar
├── migrations/
│   └── 0007_inquiryevent.py          # Tabelle + Übernahme alter Zeitstempel
├── test_day21.py                      # 40 neue Django-Tests
└── templates/listings/
    ├── seller_inquiry_detail.html    # vollständiger interner Verlauf
    └── buyer_inquiry_detail.html     # nur öffentlicher Verlauf
```

### Wieso getrennte Tabelle?

Eine Anfrage hat **einen aktuellen Status**, aber **mehrere historische Ereignisse**. Daher `InquiryEvent.inquiry = ForeignKey(CustomerInquiry, related_name="events")`. Ein separates Event ermöglicht eine geordnete Zeitleiste und verhindert, dass frühere Schritte bei jeder Statusänderung überschrieben werden.

### Wieso `transaction.atomic()`?

Bei Statuswechseln sollen Datenänderung und Ereigniseintrag **gemeinsam** in die Datenbank geschrieben werden. Falls das Anlegen des Events misslingt, wird die zugehörige Bearbeitungsaktion zurückgerollt. Bei einem neuen Kundenanliegen wird zuerst der Eingang gespeichert, dann der (ggf. langsame) KI-Aufruf außerhalb der Datenbanktransaktion durchgeführt und anschließend Erfolg oder Fehler protokolliert.

### Warum kein vollständiges „Audit-Log“?

Es ist ein **fachliches, append-orientiertes Ereignisprotokoll**, kein manipulationssicheres Audit-System: Administratoren mit direktem Datenbankzugriff könnten Einträge verändern. Es fehlen noch digitale Signaturen, externe Archivierung und eine Datenaufbewahrungsrichtlinie.

### Was passiert mit alten Anfragen?

Die Datenmigration legt einen Eingangs-Event zum bekannten `created_at` an. Falls vorhanden, werden die **tatsächlich gespeicherten** Zeitpunkte für die Verkäuferfassung (`seller_draft_updated_at`), Freigabe (`approved_at`) und Käuferbereitstellung (`delivered_at`) übernommen. Für ältere KI-Läufe und früheren Bearbeitungsbeginn ist kein eigener Zeitstempel vorhanden – hierfür werden **keine Zeitpunkte erfunden**.

Die neue Migration ist datenändernd: Vorher die SQLite-Datei sichern. Bei einem Rollback der Migration würde die Ereignistabelle gelöscht; die alten Anfragen/Antworten bleiben in ihren Ursprungstabellen.

## Nach erfolgreicher Abnahme

```powershell
git add listings PHASE3_TAG21.md
git commit -m "Phase 3 Tag 21: Nachrichten- und Statusverlauf"
git push
```

**Tag 22:** Sicherheitsreview der gesamten Anfragekette (CSRF, Autorisierung, Eingabevalidierung, Tests gegen unerlaubte Statuswechsel und unerwünschte Informationsfreigabe).
