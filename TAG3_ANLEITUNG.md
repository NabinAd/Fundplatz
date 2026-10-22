# Fundplatz – Phase 1, Tag 3: Anzeigenverwaltung

## Update im bestehenden Projekt installieren

1. Terminal in `C:\Kleinanzeigen` öffnen (`manage.py` muss dort liegen).
2. Sicherstellen, dass die bisherigen Änderungen committed sind (`git status`).
3. ZIP `fundplatz_tag3_update.zip` herunterladen und entpacken. Nur die Dateien aus dem ZIP in den bestehenden Ordner übernehmen, vorhandene Dateien überschreiben.
4. `.venv`, `db.sqlite3`, `media/` und `.git/` weder löschen noch überschreiben.
5. Virtuelle Umgebung aktivieren und Tests durchführen.

PowerShell-Befehle (ZIP im Downloads-Verzeichnis):

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag3_update.zip" -DestinationPath "." -Force
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py test listings
python manage.py runserver
```

Wenn die Aktivierung scheitert:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test listings
.\.venv\Scripts\python.exe manage.py runserver
```

Falls `No module named django` erscheint, installiere mit derselben `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Browser-Test

1. `http://127.0.0.1:8000/login/` öffnen; mit dem Superuser aus Tag 1 anmelden.
2. Unter „+ Anzeige erstellen“ eine Anzeige samt Bild speichern.
3. Prüfen, ob die Anzeige auf der Startseite und auf der Detailseite angezeigt wird.
4. Unter „Meine Anzeigen“ den Preis ändern und speichern.
5. Anzeige bearbeiten und „Anzeige aktiv“ abwählen: Anzeige bleibt unter „Meine Anzeigen“, ist aber öffentlich nicht mehr erreichbar.
6. Anzeige wieder aktivieren. Danach „Löschen“ wählen und das Löschen bestätigen: Die Anzeige verschwindet auch aus „Meine Anzeigen“.
7. Abmelden. Aufruf von `/meine-anzeigen/` soll nun zur Login-Seite führen.

## Veränderte Dateien

- `config/settings.py` – Login-URLs
- `config/urls.py` – Login und Logout
- `listings/forms.py` – neues ModelForm
- `listings/views.py`, `listings/urls.py` – sichere CRUD-Views
- `listings/tests.py` – insgesamt 30 Tests
- `templates/base.html`, `templates/registration/login.html` – Navigation und Login
- `listings/templates/listings/listing_form.html` – gemeinsames Erstellen-/Bearbeiten-Formular
- `listings/templates/listings/my_listings.html` – Verkäuferübersicht
- `listings/templates/listings/listing_confirm_delete.html` – Sicherheitsbestätigung
- `listings/templates/listings/listing_detail.html` – Verkäuferbuttons
- `listings/templates/listings/home.html`, `listing_list.html` – Erstellen-Link zeigt nun auf eigenes Formular
- `static/css/site.css` – Formular-/Verwaltungsdesign
- `README.md` – aktueller Projektstand

Keine Datenbankmigration nötig. Alle Komponenten arbeiten ohne KI.

## Git

```powershell
git add .
git commit -m "Phase 1 Tag 3: Anzeigenverwaltung"
```
