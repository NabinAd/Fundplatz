# Fundplatz – lokaler Marketplace

**Ein eigenständiger Kleinanzeigen-Marketplace mit Django – als Basis für ein späteres Multi-Agent-System.**

**Projektstatus:** Phase 1 (Website) umgesetzt · Phase 2 (lokale KI-Agenten) geplant · Phase 3 (Integration) geplant. **Aktuell enthält die Website keine KI-Funktionen.**

## Was Fundplatz kann

| Bereich | Funktionen |
| --- | --- |
| Anzeigen | Startseite, Übersicht, Detailseite, Produktbilder, Kategorien, Zustand und Preis |
| Verwaltung | Anzeige erstellen, bearbeiten, aktivieren/deaktivieren und nach Bestätigung löschen |
| Suche | Titel und Beschreibung durchsuchen, nach Kategorie und Preis filtern |
| Benutzer | Registrierung, Login, Logout, Verwaltung ausschließlich eigener Anzeigen |
| Qualität | Django-Test-Suite mit 64 Tests, CSRF-Schutz und serverseitiger Validierung |
| Darstellung | Responsives Bootstrap-Layout, kompakte mobile Navigation, lokales CSS ohne CDN |

## Tech-Stack

**Python 3.12 · Django 5.2 LTS · SQLite · Django Templates · Bootstrap 5.3 · Pillow**

Bewusst ohne React, zusätzliche API-Schicht, Cloud-Datenbank oder Agenten-Framework in Phase 1.

## Lokal starten (Windows / VS Code)

Voraussetzung: Python 3.12, Git und ein Terminal (PowerShell).

```powershell
git clone https://github.com/NabinAd/Kleinanzeigen.git
cd Kleinanzeigen
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Die Website läuft unter **http://127.0.0.1:8000/**. Ein Konto kannst du unter `/registrieren/` anlegen. Für die Django-Adminoberfläche optional:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Dann `http://127.0.0.1:8000/admin/` öffnen.

## In 60 Sekunden ausprobieren

1. Unter `/registrieren/` ein Benutzerkonto anlegen.
2. Über **Anzeige erstellen** ein Produkt mit Preis und optionalem Bild hinzufügen.
3. Unter **Meine Anzeigen** Preis ändern oder Anzeige deaktivieren/reaktivieren.
4. Unter **Alle Anzeigen** nach Suchbegriff, Kategorie oder Preis filtern.
5. Eine Anzeige öffnen und anschließend kontrolliert löschen.

## Tests

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test listings
```

**64 Testfälle** für Anzeigen, Login, Filter, Berechtigungen, Datei-Uploads und Sicherheitsgrundlagen. Die Tests laufen lokal, nicht automatisch auf GitHub. Die automatisierten Prüfungen ersetzen keinen Browser-Test bei Desktop- und Smartphone-Breite.

## Projektstruktur

```text
config/                     Django-Einstellungen und URL-Konfiguration
listings/                   Anzeigenmodell, Formulare, Views und Tests
listings/templates/         Anzeige-, Such- und Verwaltungsseiten
templates/                  Basislayout, Login und Registrierung
static/css/site.css         Eigene responsive Styles
static/vendor/              Bootstrap lokal eingebunden
manage.py                   Django-Verwaltungsbefehle
```

## Nächste Schritte

- **Phase 2 (10 Tage):** eigenständiger Python-Orchestrator mit Information-, Negotiation- und Logistics-Agent, lokalem LLM über Ollama und Validierungsregeln.
- **Phase 3 (10 Tage):** Produktfrage über die Website an das Agentensystem übergeben; Antwortentwurf anzeigen und erst nach Verkäuferfreigabe verwenden. Mindestens 30 Szenarien evaluieren.

## Sicherheit und Projektgrenzen

**Lokales Lernprojekt, keine produktionsreife Website.** In `config/settings.py` ist `DEBUG=True` und ein Entwicklungs-`SECRET_KEY` hinterlegt. Vor einem öffentlichen Betrieb wären sichere Secrets, HTTPS, Deployment-Härtung, Datenschutzmaßnahmen und zusätzliche Sicherheitstests nötig. Keine echten Kundendaten verwenden.

`db.sqlite3`, `.env`, lokale Uploads und `.venv/` werden nicht veröffentlicht. Beachte: Beim Löschen einer Anzeige werden vorhandene Bilddateien derzeit nicht automatisch auf dem Datenträger entfernt. Es gibt in Phase 1 weder Bezahlsystem noch Nachrichtenversand oder KI.

**Open Source / Abhängigkeiten:** Bootstrap ist unter der MIT-Lizenz verfügbar. Für Django, Pillow und spätere lokale LLMs gelten deren jeweilige Lizenzen. Für Fundplatz selbst wird hier keine zusätzliche Projektlizenz behauptet.
