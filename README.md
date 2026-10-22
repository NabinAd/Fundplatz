# Fundplatz – Marketplace (Phase 1 abgeschlossen, nach lokaler Abnahme)

Eigenständiger, responsiver Marketplace auf Basis von Django, SQLite, Django Templates, lokal gebündeltem Bootstrap und Pillow. **Phase 1 enthält keine KI-Agenten.** Entwickelt für lokale Ausführung unter Windows / VS Code; **kein produktionssicheres Hosting-Setup**.

## Schnellstart unter Windows (PowerShell)

```powershell
cd C:\Kleinanzeigen
py -3.12 -m venv .venv                    # nur einmal, falls .venv fehlt
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py makemigrations listings   # nur falls 0001_initial.py fehlt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Im Browser `http://127.0.0.1:8000/` aufrufen. Die Registrierung erfolgt unter `/registrieren/`; Admin-Zugang über `python manage.py createsuperuser` und `/admin/`.

## Funktionen

- Anzeigenliste, Detailseiten, optionaler Bild-Upload (bis 5 MB), Preise, Kategorien, Zustand, Versand/Abholung und Verhandlungsbasis
- Erstellen, Bearbeiten, **Aktivieren/Deaktivieren** und bestätigtes Löschen eigener Anzeigen (Login erforderlich)
- Suche in Titel und Beschreibung, Kategorie- und Preisfilter, kombinierbar mit Paginierung
- Registrierung, Anmeldung, Abmeldung; SQLite-Datenbank, Bootstrap-CSS lokal ohne CDN
- Sicherheitsgrundlagen: Eigentümerprüfung für Änderungen, CSRF-Token bei schreibenden Formularen, Django-Formvalidierung

## Tests vor Phasenabschluss

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py migrate --check
.\.venv\Scripts\python.exe manage.py test listings
```

Stand Tag 5: **64 Django-Tests** in `listings/tests.py`. Die Tests müssen auf deinem PC ausgeführt werden; die bereitgestellten Quelldateien allein bestätigen keinen grünen Testlauf. Weitere manuelle Prüfungen und GitHub-Anleitung: `TAG5_ANLEITUNG.md`.

## GitHub und Datenschutz

In `.gitignore` sind `.venv/`, `db.sqlite3`, `.env`, Cache und `media/` ausgeschlossen. **Vor einem öffentlichen Push prüfen**, ob lokale Daten aus älteren Commits noch im Git-Verlauf liegen; eine spätere `.gitignore` entfernt diese nicht rückwirkend. Die initiale Migration `listings/migrations/0001_initial.py` muss eingecheckt sein. **Keine privaten Passwörter, Datenbanken oder hochgeladenen Kundendaten veröffentlichen.**

## Technische Grenzen und Phase 2

- Die Website nutzt eine lokale Entwicklungs-Konfiguration (`DEBUG=True`, Entwicklungs-`SECRET_KEY`). Nicht unverändert öffentlich hosten! Ein öffentliches Deployment benötigt u. a. HTTPS, sichere Secrets, produktionsgeeigneten Betrieb und eine eigene Sicherheitsprüfung.
- Bereits hochgeladene Dateien werden bei Anzeige-Löschung nicht automatisch von der Festplatte entfernt. Kein Dateispeicher-Aufräumdienst im Phase-1-MVP.
- Keine Bezahlfunktion, Echtzeit-Chat, E-Mail-Bestätigung oder AI in Phase 1.
- Phase 2 implementiert separat den Python-Orchestrator, spezialisierte Agenten und Ollama. Erst Phase 3 verbindet ihn mit Fundplatz.

Drittanbieter: `static/vendor/bootstrap.min.css` enthält **Bootstrap 5.3.6**, Copyright Bootstrap Authors, **MIT License** (Lizenzhinweis im CSS-Dateikopf). Django und Pillow siehe jeweilige Projektlizenzen.
