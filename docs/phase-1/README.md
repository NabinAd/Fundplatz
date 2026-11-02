# Phase 1 – Django-Marktplatz und Benutzeroberfläche

[← Zur Projektübersicht](../../README.md) · [Phase 2 →](../phase-2/README.md) · [Phase 3 →](../phase-3/README.md)

## Zusammenfassung

In Phase 1 entstand die Grundlage von Fundplatz: ein Django-Marktplatz mit Benutzerkonten, Anzeigen, Katalog, Suche, Filtern und responsive gestalteten Seiten. Diese Phase enthält die Grundlagen für die spätere KI-Integration.

**Wichtige Codebereiche:** [Django-Anwendung](../../listings/), [Datenmodelle](../../listings/models.py), [Views](../../listings/views.py), [Templates](../../listings/templates/listings/), [Styles](../../static/css/site.css).

## Entwicklungsabschnitte

| Abschnitt | Dokumentation |
| --- | --- |
| Start | Projektanleitung und Einrichtung |
| TAG2\_ANLEITUNG.md | Katalog und Produktdetails |
| TAG3\_ANLEITUNG.md | Anzeigenverwaltung |
| TAG4\_ANLEITUNG.md | Erweiterungen der Marktplatzoberfläche |
| TAG5\_ANLEITUNG.md | Tests und Phase-1-Abschluss |
| DESIGN\_CHECKLIST.md | Designprüfung |
| ANLEITUNG\_HEADER\_FIX.md | Header- und Layoutkorrektur |

> **Hinweis:** Die folgenden Originalnotizen dokumentieren frühere Zwischenstände, Patch-Schritte und lokale ZIP-Installationsanweisungen. Für die **aktuelle Installation** immer die [Haupt-README](../../README.md) verwenden. Die Notizen wurden inhaltlich unverändert übernommen.

## Originalnotizen (vollständiges Archiv)

<details>
<summary><strong>ANLEITUNG.txt</strong></summary>

Fundplatz – letzte Korrektur für Tag 5

Im VS-Code-PowerShell-Terminal:

cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag5_testfix2.zip" -DestinationPath "." -Force
.\.venv\Scripts\python.exe manage.py test listings

Wenn 64 Tests mit OK abschliessen:
git add listings/tests.py
git commit -m "Fix: Suchtest prueft Ergebnisse statt Platzhalter"
git push

Diese ZIP ersetzt ausschliesslich listings/tests.py; die Datenbank bleibt erhalten.

</details>

<details>
<summary><strong>TAG2_ANLEITUNG.md</strong></summary>

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

</details>

<details>
<summary><strong>TAG3_ANLEITUNG.md</strong></summary>

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

</details>

<details>
<summary><strong>TAG4_ANLEITUNG.md</strong></summary>

# Fundplatz – Phase 1, Tag 4

**Ziel:** Suche über Titel/Beschreibung, Kategorie- und Preisfilter sowie Benutzerregistrierung. Noch **keine KI**.

## Update in das bestehende Projekt übernehmen (Windows / PowerShell)

1. VS Code im **bestehenden** Ordner `C:\Kleinanzeigen` öffnen (dort liegt `manage.py`).
2. Aktuelle Arbeit vorher mit Git sichern: `git status` prüfen; bei ungesicherten Änderungen diese zuerst committen.
3. `fundplatz_tag4_update.zip` herunterladen. Dann im VS-Code-Terminal:

   ```powershell
   cd C:\Kleinanzeigen
   Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag4_update.zip" -DestinationPath "C:\Kleinanzeigen" -Force
   ```

   Falls die ZIP an einem anderen Ort liegt, den Pfad entsprechend ersetzen. **Keinen neuen Projektordner erstellen.**

4. Mit der bereits vorhandenen virtuellen Umgebung testen:

   ```powershell
   .\.venv\Scripts\python.exe manage.py check
   .\.venv\Scripts\python.exe manage.py test listings
   .\.venv\Scripts\python.exe manage.py runserver
   ```

5. Seiten ausprobieren:
   - `http://127.0.0.1:8000/`: Suchfeld auf der Startseite.
   - `http://127.0.0.1:8000/anzeigen/`: Textsuche + Kategorie + Preis von/bis (kombinierbar).
   - `http://127.0.0.1:8000/registrieren/`: Neues Konto erstellen.
   - `http://127.0.0.1:8000/login/`: Anmeldung.
   - `http://127.0.0.1:8000/meine-anzeigen/`: Eigene Anzeigen nach Anmeldung.

## Manuelle Prüfungen

- Zwei Anzeigen mit verschiedenen Kategorien und Preisen erstellen, die Suche/Filter einzeln und kombiniert prüfen.
- Deaktivierte Anzeige bleibt auch bei einer passenden Suche unsichtbar.
- Einen ungültigen Bereich ausprobieren (`von 200`, `bis 100`) -> verständliche Fehlermeldung.
- Mindestens 13 Treffer erzeugen oder die Paginierung mit automatisierten Tests prüfen; Suchfilter bleiben auf Seite 2 erhalten.
- Ausloggen, ein neues Testkonto registrieren, einloggen und eine eigene Anzeige erstellen.
- Fremde Anzeige mit dem neuen Konto nicht bearbeiten oder löschen können (bestehende Sicherheitstests).

## Technische Hinweise

- **Keine Änderungen an `models.py` oder an der Datenbankstruktur.** `makemigrations` ist für Tag 4 nicht notwendig.
- Die vorhandene `db.sqlite3`, Bilder, Benutzerkonten, `.venv` und Git-Historie bleiben erhalten. Das ZIP enthält sie nicht.
- Die Suche erfolgt mit Djangos ORM (`icontains`), für das MVP genügt SQLite. Keine externe Suchmaschine, API oder KI nötig.
- Die Registrierung nutzt Djangos `UserCreationForm` inklusive Passwortvalidierung. **Keine E-Mail-Verifizierung** im lokalen MVP.
- Im bestehenden `config/settings.py` ist `DEBUG=True` und ein nur für lokale Entwicklung vorgesehener Standard-Secret-Key eingestellt. Diese Konfiguration darf so **nicht öffentlich bereitgestellt** werden.

Wenn alle Tests bestehen und die manuellen Prüfungen erfolgreich sind:

```powershell
git add .
git commit -m "Phase 1 Tag 4: Suche Filter Registrierung"
```

**Definition of Done:** Suchen, filtern und registrieren funktionieren; alte CRUD-Funktionen bleiben funktionsfähig und die vollständige Testsuite ist grün.

</details>

<details>
<summary><strong>TAG5_ANLEITUNG.md</strong></summary>

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

</details>

<details>
<summary><strong>DESIGN_CHECKLIST.md</strong></summary>

# Fundplatz – Design-Abnahme

Diese Aktualisierung verändert nur Templates, CSS und README. Die Datenbank, Modelle, Views und Tests bleiben unverändert.

1. Auf `http://127.0.0.1:8000/` Startseite bei 1440 px, 1024 px und 375 px Breite prüfen.
2. Bei 375 px **Menü** öffnen: Startseite, Anzeigen, Login/Registrieren bzw. Meine Anzeigen und Abmelden müssen erreichbar sein.
3. Unter **Alle Anzeigen** bei etwa 1024 px kontrollieren, dass der Button **Suchen** nicht abgeschnitten wird.
4. Anzeige mit langem Titel erstellen: Produktkarte und Detailseite dürfen nicht horizontal überlaufen.
5. Unter **Meine Anzeigen** auf dem Smartphone alle Aktionen (Ansehen, Deaktivieren, Bearbeiten, Löschen) prüfen.
6. Tastaturtest mit Tab / Enter: Menü, Links, Formularfelder und Buttons müssen bedienbar sein.
7. Tests ausführen: `.\.venv\Scripts\python.exe manage.py test listings` (64 Tests erwartet).
8. Bei Problemen CSS/HTML aus `git diff` prüfen; mit `git restore` lassen sich uncommittete Änderungen rückgängig machen.

**GitHub-Auftritt:** Nach erfolgreichem lokalen Test README + UI-Dateien committen und pushen. In GitHub unter *About → Edit* zusätzlich Beschreibung `Responsiver Django-Marketplace mit SQLite – Projektbasis für ein lokales Multi-Agent-System` und Themen `django`, `python`, `sqlite`, `bootstrap`, `marketplace`, `ollama`, `multi-agent` eintragen (die letzten beiden sind als Projektplanung zu verstehen).

**Für echte Screenshots:** Seite lokal im Browser öffnen, Desktop und Mobilansicht aufnehmen und später im Repository als `docs/screenshots/` hinzufügen. Nicht das Admin-Passwort oder private Benutzer-/Anzeigendaten abbilden.

</details>

<details>
<summary><strong>ANLEITUNG_HEADER_FIX.md</strong></summary>

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

</details>

