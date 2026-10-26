# Fundplatz – Phase 3, Tag 23: asynchrone KI-Entwürfe und Ausfälle

## Ziel

Der Käufer soll beim Senden einer Frage nicht 5–30 Sekunden auf Ollama warten. Deshalb kann die Website eine Kundenanfrage **nur speichern**. Ein **separater Django-Worker** erstellt den privaten Entwurf. Er veröffentlicht niemals etwas an den Käufer und ändert weder die interne Freigabe noch bereitgestellte Antworten.

### Technischer Ablauf

1. HTTP-POST: Login, Formularvalidierung, 5-Anfragen-pro-Stunde-Limit, `CustomerInquiry` + `received`-Ereignis speichern.
2. Bei `FUNDPLATZ_AGENT_ASYNC=1`: `draft_processing='queued'`; sofortiges Redirect. **Kein Ollama-Aufruf** aus der HTTP-View.
3. `python manage.py process_inquiries --loop` läuft in einem **zweiten Terminal**, übernimmt wartende Einträge atomar und setzt `draft_processing='running'`.
4. Der Worker führt `generate_private_draft()` aus. Bei Erfolg: `draft_processing='ready'` und je nach Prüfresultat Verkäuferstatus `review_required`/`needs_attention`; bei Fehler: `draft_processing='failed'` und `needs_attention`. Jeweils ein internes Verlaufsereignis.
5. Verkäufer prüft und bearbeitet die Antwort wie bisher. Nur nach expliziter Freigabe und Bereitstellung wird ein Text für den Käufer sichtbar.

**Wichtig:** Ohne gestarteten Worker bleiben Jobs dauerhaft auf `queued`. Die Queue läuft nicht automatisch im Hintergrund. Das ist ein lokaler Prototyp mit SQLite, keine Produktions-Jobplattform.

## Installation (VS Code / Windows, `.venv` bereits aktiv)

Vor jeder neuen Migration optional eine lokale Sicherung erstellen:

```powershell
cd C:\Kleinanzeigen
Copy-Item .\db.sqlite3 .\db_backup_vor_tag23.sqlite3
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag23.zip" -DestinationPath "." -Force
python manage.py migrate
python manage.py makemigrations --check --dry-run
```

Die Migration `0008_inquiry_draft_queue.py` ergänzt nur Verwaltungsfelder; ältere Anfragen haben als Default `ready`.

## Tests zunächst im bisherigen Modus

```powershell
$env:FUNDPLATZ_AGENT_ASYNC="0"
$env:FUNDPLATZ_AGENT_USE_LLM="0"
python manage.py test listings.test_day23 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
```

Erwartet: 31 neue Django-Tests und 269 Agententests. Hier wurde der Python-Agententeil ausgeführt; **Django-Tests müssen auf deinem PC ausgeführt werden**.

## Asynchronen Modus praktisch starten

**Terminal A: Webserver**

```powershell
cd C:\Kleinanzeigen
$env:FUNDPLATZ_AGENT_ASYNC="1"
python manage.py runserver
```

**Terminal B: Worker (eigene VS-Code-Terminalregisterkarte, `.venv` aktiv)**

```powershell
cd C:\Kleinanzeigen
$env:FUNDPLATZ_AGENT_USE_LLM="1"
$env:OLLAMA_TIMEOUT_SECONDS="45"
python manage.py process_inquiries --loop
```

- Stelle als Käufer eine Frage bei einer fremden aktiven Anzeige. Die Website gibt **sofort** eine Eingangsbestätigung zurück. Sie wartet nicht auf den Worker.
- Im Verkäuferpostfach `/anfragen/` erscheint zuerst `KI wartet auf Worker`, danach `KI verarbeitet` und schließlich der private Entwurf bzw. ein manueller Bearbeitungshinweis.
- Der Käufer sieht in `/meine-anfragen/` **nie** die internen KI-Texte.
- Mit `Strg+C` beendest du Webserver bzw. Worker.

Einmalig oder testweise nur eine Anfrage bearbeiten:

```powershell
python manage.py process_inquiries --once
```

Alle derzeit wartenden Anfragen (maximal 20) bearbeiten und beenden:

```powershell
python manage.py process_inquiries
```

### Fehlerbehandlung und Wiederherstellung

- Ist Ollama nicht erreichbar, kann der Router auf `fallback` (= Regeln) wechseln. In der Verkäuferansicht wird die Quelle nicht als `llm` ausgegeben.
- Schlägt die Pipeline vollständig fehl, erhält nur der Verkäufer den Hinweis `Kein automatischer Entwurf verfügbar. Bitte manuell antworten.`; die Käuferfrage bleibt gespeichert.
- `OLLAMA_TIMEOUT_SECONDS` begrenzt **jeden einzelnen HTTP-Aufruf an Ollama** auf 5–300 Sekunden, nicht die komplette mehrstufige Pipeline. Kürzere Werte können mehr Fallbacks auslösen.
- Nach einem **abgebrochenen Worker-Prozess** können Einträge in `running` bleiben. Bei ausreichend alten Einträgen (mindestens 30 Minuten empfohlen) darfst du ausdrücklich wiederherstellen:

```powershell
python manage.py process_inquiries --recover-stale --stale-minutes 30 --once
```

Die atomare Beanspruchung und ein **Versuchsticket** verhindern das Überschreiben durch einen verspäteten älteren Worker nach dem Wiederanlaufen. Ein manueller Recovery-Befehl kann trotzdem doppelte *LLM-Rechenarbeit* auslösen, wenn der alte Prozess noch lebt; daher nur nach Prüfung benutzen. Fehlgeschlagene Aufträge (`failed`) werden nicht automatisch wiederholt, damit kein Endloslauf entsteht.

### Technische Grenzen

- SQLite reicht für lokale Entwicklung; für parallele Produktionsarbeiter werden PostgreSQL und eine echte Job-Queue (z. B. Celery oder RQ), Monitoring, Backoff und Dead-Letter-Behandlung empfohlen.
- Keine automatische Antwortfreigabe, kein E-Mail-Versand, kein autonomes Preisangebot.
- Die KI erhält die **aktuellen** Angebotsdaten zur Verarbeitungszeit; ein Snapshot der ursprünglichen Anzeige wird an Tag 23 noch nicht eingeführt.
- Beim Testen die asynchrone Umgebungsvariable wieder auf `0` stellen, weil ältere Tests den synchronen Standardmodus erwarten.

## Geänderte Projektdateien

- `config/settings.py`: Feature-Flag `FUNDPLATZ_AGENT_ASYNC` (standardmäßig aus)
- `listings/models.py` und `listings/migrations/0008_inquiry_draft_queue.py`: Queue-Zustand, Start/Ende, Versuchszähler
- `listings/views.py`: schneller HTTP-POST im asynchronen Modus; Sperren gegen Bearbeitung/Freigabe während `queued/running`
- `listings/draft_queue.py`: atomare Worker-Bearbeitung, Fehlermodus, Recovery
- `listings/management/commands/process_inquiries.py`: Worker-CLI
- `listings/templates/listings/seller_inquiries.html`, `seller_inquiry_detail.html`: Fortschritt
- `listings/test_day23.py`: 31 Django-Regressionstests
- `agent_system/ollama_client.py`: konfigurierbares einzelnes HTTP-Timeout
- `agent_system/tests/test_ollama_client.py`: drei neue Timeout-Tests

## GitHub

Nach den bestandenen Tests:

```powershell
git add agent_system/ollama_client.py agent_system/tests/test_ollama_client.py config/settings.py listings PHASE3_TAG23.md
git commit -m "Phase 3 Tag 23: asynchrone KI-Verarbeitung und Worker"
git push
```
