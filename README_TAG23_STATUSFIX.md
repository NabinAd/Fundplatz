# Fundplatz Tag 23 – KI-Status im Verkäuferpostfach sichtbar machen

Diese kleine Korrektur ersetzt nur zwei Templates. **Keine Migration, keine Änderung an Django-Views, Agenten oder Datenbank.**

- Zeigt KI-Verarbeitung getrennt vom Verkäufer-Prüfstatus: `queued`, `running`, `ready`, `failed`.
- `ready` wird dauerhaft als **Abgeschlossen** angezeigt. `Prüfung erforderlich` ist die weiterhin nötige menschliche Verkäuferprüfung.
- Während `queued`/`running` aktualisiert sich die private GET-Seite alle 5 Sekunden. Sobald sie fertig ist, stoppt die automatische Aktualisierung.
- Es wird weder eine Nachricht versendet noch ein KI-Entwurf freigegeben.

## Installation – `.venv` ist aktiviert

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag23_statusanzeige_fix.zip" -DestinationPath "." -Force
python manage.py check
python manage.py test listings
```

Danach Django neu laden und mit Strg+F5 die Browserseite öffnen.

## Echten Wartestatus zuverlässig sehen

1. Im Worker-Terminal `Strg+C` drücken, damit **kein Worker läuft**.
2. Django im Terminal A mit asynchroner Verarbeitung neu starten:

```powershell
$env:FUNDPLATZ_AGENT_ASYNC="1"
python manage.py runserver
```

3. Als Käufer **eine neue Frage** absenden, dann als Verkäufer `/anfragen/` öffnen: Die Anfrage sollte **Wartet auf Worker** zeigen. Beachte das Limit von maximal fünf Käuferfragen pro Stunde.
4. Im zweiten Terminal den Worker starten:

```powershell
$env:FUNDPLATZ_AGENT_USE_LLM="1"
python manage.py process_inquiries --loop
```

5. Die Seite aktualisiert sich während der Verarbeitung automatisch, zeigt (sofern schnell genug sichtbar) **Wird verarbeitet** und danach dauerhaft **Abgeschlossen**. Eine kurze `running`-Phase kann zwischen zwei Refreshs liegen, was normal ist.

**Wichtig:** `Router: llm` belegt nur LLM-Routing, nicht ob die Anfrage zuvor asynchron verarbeitet wurde. Ob die Webserver-Einstellung aktiv ist, prüft man in **dem Terminal, in dem `runserver` gestartet wurde**. Wenn das Webserver-Terminal noch `FUNDPLATZ_AGENT_ASYNC=0` hatte, wurden bisherige Anfragen synchron verarbeitet, ohne dass `queued/running` im Browser jemals sichtbar sein konnten.

```powershell
python manage.py shell -c "from listings.models import CustomerInquiry; print(list(CustomerInquiry.objects.order_by('-pk').values('pk','draft_processing','draft_started_at','draft_finished_at')[:6]))"
```

Eine abgeschlossene Worker-Anfrage hat im Normalfall `ready`, `draft_started_at` und `draft_finished_at`. Ältere oder synchrone Anfragen können ebenfalls `ready`, aber ohne diese Zeitstempel sein.
