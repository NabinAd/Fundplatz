# Fundplatz – Layoutkorrektur (Phase 1)

Dieses Update ist für das zuletzt gelieferte Design-Update gedacht. Es ersetzt **nur** `static/css/site.css` und `templates/base.html`. Kein Python-Code und keine Datenbankänderung.

## Installation (VS Code / PowerShell)

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_header_fix.zip" -DestinationPath "." -Force
.\.venv\Scripts\python.exe manage.py runserver
```

Dann im Browser `Strg + F5` für eine vollständige Neuladung drücken.

## Was ist behoben?

- „Zum Inhalt springen“ wird visuell verborgen, bleibt aber beim Fokus mit Tab bedienbar.
- Weißer Header besitzt eine verlässliche Höhe von mindestens 82 px (mobil 72–74 px).
- Grüner Sloganbereich beginnt im normalen Dokumentfluss unter dem Header.
- Der CSS-Link in `base.html` erhält einen Versionsparameter, damit Browser alte Styles nicht aus dem Cache verwenden.

## Falls das Layout weiter kaputt ist

**Prüfe, ob CSS wirklich geladen wird:** Im Browser diese beiden Adressen öffnen:
- http://127.0.0.1:8000/static/css/site.css
- http://127.0.0.1:8000/static/vendor/bootstrap.min.css

Beide Seiten müssen CSS-Quelltext anzeigen, **keine** 404-Fehlermeldung und **kein** HTML. Wenn eine Datei 404 liefert, liegt das Problem an der statischen Auslieferung oder am falschen Projektordner; ein CSS-Patch allein kann das nicht lösen.

## Tests / Git

```powershell
.\.venv\Scripts\python.exe manage.py test listings
git status
git add static/css/site.css templates/base.html
git commit -m "Fix header spacing and skip link visibility"
git push
```

Die Tests müssen lokal erfolgreich durchlaufen. Eine Browserprüfung mit sichtbarer Website ist zusätzlich nötig.
