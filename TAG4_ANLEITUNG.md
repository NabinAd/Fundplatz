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
