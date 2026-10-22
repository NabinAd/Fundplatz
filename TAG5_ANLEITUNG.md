# Phase 1, Tag 5 – Abschluss / Abnahme / GitHub

Ziel: Schnell und nachvollziehbar prüfen, dass der Marketplace ohne KI eigenständig läuft. Keine neue Django-App, keine Datenmodelländerung.

## Update einspielen (Windows / PowerShell)

1. Bestehendes Projekt `C:\Kleinanzeigen` in VS Code öffnen. Mit `git status` ungesicherte Änderungen prüfen und bei Bedarf committen.
2. `fundplatz_tag5_update.zip` herunterladen, in `C:\Kleinanzeigen` **über die vorhandenen Dateien entpacken**:

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag5_update.zip" -DestinationPath "C:\Kleinanzeigen" -Force
```

**Keine neue Datenbank anlegen.** ZIP enthält **keine** `db.sqlite3`, `.venv`, `media/`, `manage.py`, `models.py` oder Migration. Bereits vorhandene Anzeigen, Fotos und Git-Historie bleiben erhalten. Wenn du eigene Änderungen in den überschriebenen Dateien vorgenommen hast, vorher mit Git sichern und nach dem Update vergleichen.

## Neu in Tag 5

- „Meine Anzeigen“: **Aktivieren/Deaktivieren** mit separatem POST-Button, CSRF und Eigentümerprüfung. Das ist **kein Löschen**.
- Bootstrap 5.3.6 CSS lokal eingebunden: Website-Layout funktioniert auch ohne Internet.
- Tastatur-Sprunglink, Fokus-Stile und kleinere mobile Optimierungen.
- Zehn zusätzliche Regressionstests (insgesamt 64), darunter Eigentumsschutz, Login, POST-Pflicht, CSRF und Reaktivierung.
- Aktualisierte README und GitHub-Checkliste.

## Automatisierte Prüfung

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py migrate --check
.\.venv\Scripts\python.exe manage.py test listings
```

Erwartung: keine Systemfehler, keine offenen Modelländerungen / Migrationen, **64 Tests / OK**. Falls noch Migrationen aus Tag 1 fehlen: `manage.py makemigrations listings` und `manage.py migrate` ausführen, danach erneut testen und Migrationen mit Git einchecken. Eine schon vorhandene `0001_initial.py` nicht durch fremde Migrationen überschreiben.

## Manuelle Abnahme (Browser)

1. `manage.py runserver`; Startseite, `/anzeigen/`, Detailseite und Bilder prüfen.
2. Neuen Nutzer unter `/registrieren/` registrieren und anmelden.
3. Anzeige mit Bild erstellen, Preis bearbeiten, Details aktualisieren.
4. In **Meine Anzeigen** auf „Deaktivieren“ klicken: aus öffentlicher Übersicht entfernt, bleibt in „Meine Anzeigen“ erhalten. Wieder „Aktivieren“: öffentlich sichtbar.
5. Suche nach Titel/Beschreibung, Kategorie, Mindest-/Höchstpreis und Kombination testen. Bei `min > max` muss ein Fehler erscheinen.
6. Mit einem zweiten Benutzer versuchen, eine fremde Anzeige zu bearbeiten / deaktivieren / löschen: Zugriff verweigert (404). 
7. Eigene Anzeige löschen: erst Bestätigungsseite, danach aus Datenbank verschwunden.
8. Fenster schmal ziehen, Tastatur mit Tab benutzen; Layout auch offline testen (nachdem Projekt und Pakete installiert sind).

## GitHub – Phase 1 veröffentlichen

Die Git-Historie von Tag 1–4 bleibt erhalten. **Vor dem Push** lokal prüfen:

```powershell
git status
git ls-files db.sqlite3
git ls-files .env
git ls-files media
git ls-files listings/migrations
```

Die ersten drei Befehle mit `git ls-files` sollten **keine Ergebnisse** liefern. Bei `listings/migrations` sollte neben `__init__.py` auch die erste Migration (`0001_initial.py` oder die in Tag 1 erzeugte Migration) erscheinen. Achtung: Selbst wenn Dateien aktuell nicht mehr getrackt werden, könnten sie aus früheren Commits noch erreichbar sein – vor öffentlicher Freigabe den Git-Verlauf auf sensible Daten überprüfen.

Nach erfolgreichen Tests:

```powershell
git add .
git commit -m "Phase 1 Tag 5: QA UI Statuswechsel GitHub"
git branch --show-current
git remote -v
```

Auf GitHub ein **leeres** Repository `fundplatz-marketplace` ohne neu erzeugte README/.gitignore erstellen. Falls noch kein `origin` gesetzt ist:

```powershell
git remote add origin https://github.com/DEIN-BENUTZERNAME/fundplatz-marketplace.git
```

Der Benutzername muss ersetzt werden. Falls bereits `origin` angezeigt wird, diesen Schritt überspringen. Dann **mit deinem aktuellen Branchnamen** pushen:

```powershell
git push -u origin main
```

Der letzte Befehl gilt, wenn `git branch --show-current` `main` ausgibt. Bei einem anderen Branchnamen im Push-Befehl `main` ersetzen.

## Done

Erst wenn alle vier automatisierten Befehle erfolgreich sind, die manuellen Hauptfunktionen funktionieren und das GitHub-Repository die Projektdateien samt Migration (aber keine privaten Daten) enthält, ist **Phase 1 wirklich abgeschlossen**. Erst dann Phase 2 starten.
