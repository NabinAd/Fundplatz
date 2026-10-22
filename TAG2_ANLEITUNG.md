# Phase 1 · Tag 2 – Produktübersicht und Detailseiten

Dieses Update baut auf dem Tag-1-Projekt auf. Es enthält **nur geänderte oder neue Dateien**.

## Installation unter Windows / VS Code

1. VS Code mit deinem bisherigen Fundplatz-Projekt öffnen (dort, wo `manage.py` liegt).
2. Prüfe mit `git status`, dass du keine ungesicherten lokalen Änderungen überschreibst.
3. ZIP `fundplatz_tag2_update.zip` **direkt in diesen Projektordner** entpacken, sodass die ZIP-Datei `listings/views.py` deine bestehende Datei `listings/views.py` ersetzt. Alternative: ZIP in Downloads entpacken und die **enthaltenen** Ordner `listings`, `templates`, `static` sowie `TAG2_ANLEITUNG.md` in deinen Projektordner kopieren und vorhandene Dateien ersetzen lassen. **Nicht** einen zusätzlichen Unterordner `fundplatz_tag2_update` in deinem Projekt anlegen.
4. Die `.venv`, `db.sqlite3`, `media` und `.git` bleiben unangetastet.
5. Im VS-Code-Terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py test listings
python manage.py runserver
```

Wenn PowerShell die Aktivierung blockiert: ` .\.venv\Scripts\python.exe manage.py test listings` und anschließend ` .\.venv\Scripts\python.exe manage.py runserver` verwenden.

**Keine neue Migration nötig:** `models.py`, `settings.py` und `requirements.txt` sind unverändert.

## Neue Seiten

- Startseite: http://127.0.0.1:8000/
- Anzeigenübersicht: http://127.0.0.1:8000/anzeigen/
- Detailseite: `http://127.0.0.1:8000/anzeigen/1/` – nur wenn Anzeige Nr. 1 existiert und aktiv ist
- Verwaltung: http://127.0.0.1:8000/admin/

## Manuell testen

1. In `/admin/` eine aktive Anzeige erstellen und ein Bild hochladen (optional).
2. Startseite öffnen und auf Titel/Karte klicken. Die Detailseite muss Titel, Preis, Beschreibung, Zustand, Standort, Versand und Abholung anzeigen.
3. In der Navigation „Alle Anzeigen“ öffnen. Die Anzeige muss erscheinen.
4. Im Admin „Anzeige aktiv“ deaktivieren. Die Anzeige verschwindet von Startseite und Übersicht. Die alte Detailseiten-URL liefert **404**.
5. Anzeige wieder aktivieren. Die Detailseite ist erneut erreichbar.
6. Für Pagination kann man 13 Anzeigen anlegen – Seite 1 zeigt 12 Karten, Seite 2 eine.

## Automatisierte Tests

```powershell
python manage.py check
python manage.py test listings
```

Erwartet: `Ran 14 tests` und `OK`.

## Git

```powershell
git status
git add listings/views.py listings/urls.py listings/tests.py listings/templates/listings/ templates/base.html static/css/site.css TAG2_ANLEITUNG.md
git commit -m "Phase 1 Tag 2: Anzeigenuebersicht und Detailseiten"
```

**Noch nicht enthalten:** Öffentliche Anzeigenformulare (Tag 3), Suche/Filter (Tag 4), Agenten (Phase 2).
