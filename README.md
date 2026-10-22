# Fundplatz – eigener Marketplace (Phase 1, Tag 3)

Lokale Django-Website mit SQLite-Datenbank. Ohne KI-Funktionen.

## Voraussetzungen

- Windows 10/11, VS Code und Python 3.12
- Django und Pillow aus `requirements.txt`
- Internet für das Bootstrap-CDN, sofern CSS nicht lokal zwischengespeichert wurde

## Vorhandenes Tag-2-Projekt auf Tag 3 aktualisieren

Kopiere die Dateien aus `fundplatz_tag3_update.zip` in den bestehenden Projektordner (dort, wo `manage.py` liegt), und bestätige das Überschreiben. **Die Dateien `db.sqlite3`, `.venv/`, `media/` und `.git/` sind nicht im Update und bleiben erhalten.**

PowerShell in VS Code, im Projektordner:

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py test listings
python manage.py runserver
```

Wenn `.venv` nicht aktiviert ist, nutze die Python-Exe direkt:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Django neu installieren (nur falls notwendig):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Funktionen

- Startseite `/` und öffentliche Übersicht `/anzeigen/`
- Aktive Anzeigen öffentlich unter `/anzeigen/<id>/`
- Anmelden mit vorhandenem Django-User: `/login/`
- Eigene Anzeigen: `/meine-anzeigen/`
- Anzeige anlegen: `/anzeigen/neu/`
- Eigene Anzeige ändern: `/anzeigen/<id>/bearbeiten/`
- Eigene Anzeige löschen: `/anzeigen/<id>/loeschen/` (POST nach Bestätigung)
- Abmelden über POST-Formular in der Navigation
- Django-Admin bleibt unter `/admin/`

Nur angemeldete Verkäufer können neue Anzeigen erstellen oder ihre eigenen bearbeiten/löschen. Das Besitzerfeld (`seller`) kommt aus `request.user`, nicht aus Formulardaten. Auch deaktivierte Anzeigen sind unter „Meine Anzeigen“ bearbeitbar. Bilder optional, max. 5 MB.

Falls noch kein Benutzer vorhanden ist: `python manage.py createsuperuser`.

## Tests und Git

```powershell
python manage.py check
python manage.py test listings
python manage.py makemigrations --check --dry-run

git status
git add .
git commit -m "Phase 1 Tag 3: Anzeigenverwaltung"
```

Erwartung: 30 Django-Tests erfolgreich. Keine Modelländerungen / neuen Migrationen an Tag 3.

## Lokale Entwicklungsgrenzen

`DEBUG=True`, der Standard-SECRET_KEY und SQLite sind nur für den lokalen Projektbetrieb konfiguriert. Für einen öffentlichen Betrieb wäre zusätzliche Absicherung notwendig. Es gibt noch keine Selbstregistrierung, keine Suche und keine KI-Agenten. Die Produktbilder werden lokal im `media/`-Ordner gespeichert, der absichtlich nicht eingecheckt wird. Beim Löschen einer Anzeige entfernt Django den Datenbankeintrag; bereits hochgeladene Bilddateien können als Datei im Medienordner verbleiben (Aufräumen ist nicht Bestandteil des Tag-3-MVP).


## Phase 1, Tag 4: Suche / Filter / Registrierung

- Unter `/anzeigen/` kannst du aktive Anzeigen nach Titel/Beschreibung suchen und nach Kategorie und Preis filtern.
- Unter `/registrieren/` kannst du ein lokales Verkäuferkonto mit Benutzername und Passwort anlegen.
- Installations- und Testschritte stehen in `TAG4_ANLEITUNG.md`.
- Es gibt weiterhin **keine KI-Komponenten**.
