# Fundplatz – Phase 2, Tag 7: Strukturierte Eingaben

**Ziel:** Produktfakten und Kundenfragen unabhängig von Django und Ollama prüfen.
Diese ZIP-Datei ist ein **Update** für dein bestehendes Tag-6-Projekt und überschreibt nur `agent_system/demo.py`. Alle anderen Tag-6-Dateien, die Django-Website und deine SQLite-Datenbank bleiben erhalten.

## 1. Installation unter Windows / VS Code

Terminal in VS Code öffnen, dann:

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase2_tag7.zip" -DestinationPath "." -Force
```

Falls du `agent_system/ollama_client.py` noch nicht hast, zunächst das Tag-6-Paket installieren.
Es werden **keine zusätzlichen pip-Pakete** benötigt. Die vier Tag-6-Tests bleiben erhalten.

## 2. Strukturierte Eingaben ohne Ollama testen

```powershell
.\.venv\Scripts\python.exe -m agent_system.demo --nur-pruefen
```

Das Programm liest `agent_system/examples/tag7_input.json`. Erwarte `Eingaben gültig` und `Validierung OK. Kein Ollama-Aufruf ausgeführt.`

**Beispiel:**

```json
{
  "product": {
    "listing_id": 1,
    "title": "Lenovo ThinkPad T480",
    "description": "16 GB RAM, 512 GB SSD",
    "condition": "Gut, gebraucht",
    "price_eur": "220.00",
    "shipping_available": true,
    "pickup_available": true,
    "location": null,
    "is_negotiable": false,
    "availability": null
  },
  "request": {
    "message": "Wie viel RAM hat der Laptop und ist Versand möglich?"
  }
}
```

Bedeutung: `null` = unbekannt, `false` = ausdrücklich nein. Eine Anzeige mit `is_active=True` beweist **nicht**, dass ein Artikel noch verfügbar ist. Deswegen wird `availability` nicht automatisch aus dem Django-Modell abgeleitet.

`price_eur` ist aus Genauigkeitsgründen als String mit Punkt gespeichert, z. B. `"220.00"`, nicht als JSON-Fließkommazahl. Gültiger Preisbereich: 0 bis 9999999.99, höchstens zwei Nachkommastellen.

## 3. Einen Fehler absichtlich auslösen

Öffne `agent_system/examples/tag7_input.json` in VS Code und ändere den Preis testweise auf `"-30"`. Danach erneut:

```powershell
.\.venv\Scripts\python.exe -m agent_system.demo --nur-pruefen
```

Erwartet: `EINGABEFEHLER: product.price_eur: Preis muss zwischen 0 und 9999999.99 liegen.` und Exit-Code 1. **Danach Preis wieder auf `"220.00"` setzen.**

Du kannst auch `availability` auf `"sold"` setzen. Das ist gültig, bedeutet aber, dass ein Verkäufer den Artikel ausdrücklich als verkauft gekennzeichnet hat – nicht dass Ollama den Status bestimmen dürfte.

## 4. Erste echte Ollama-Anfrage mit geprüften Daten

Wenn Ollama läuft und dein Tag-6-Modell installiert ist:

```powershell
.\.venv\Scripts\python.exe -m agent_system.demo --frage "Ist Versand möglich?"
```

Ein alternatives Modell wählst du mit `--modell MODELLNAME`. Ohne `--modell` verwendet das Programm die Modellwahl aus `agent_system/ollama_client.py` (Tag 6).

Die Antwort ist **noch nicht vom Validator geprüft**. Diese Sicherheitskomponente implementieren wir an Tag 12; der Router kommt an Tag 8. Versende die Antwort nicht automatisiert an Kunden.

## 5. Python-Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s agent_system/tests -v
```

Erwartet: **35 Tests, OK** (31 neue Tag-7-Tests + 4 bestehende Tag-6-Tests). Die 35 Tests wurden für dieses Paket hier erfolgreich ausgeführt. Sie benötigen **kein Ollama** und **kein Django**.

Optional: Django separat weiter prüfen:

```powershell
.\.venv\Scripts\python.exe manage.py test listings
```

## 6. Dateien und Funktionen

- `agent_system/inputs.py`: `ProductContext`, `CustomerRequest`, `AgentInput`, `InputValidationError` und Feldvalidierungen; Standardbibliothek mit `dataclasses`, `decimal`, `json`.
- `agent_system/examples/tag7_input.json`: bearbeitbare Beispieldaten.
- `agent_system/demo.py`: aktualisierte Tag-6-Demo; zuerst Eingabeprüfung, optional Ollama.
- `agent_system/tests/test_inputs.py`: neue Offline-Tests für gültige/ungültige JSON-Felder.
- `PHASE2_TAG7.md`: diese Anleitung.

Die Eingaben sind **unveränderlich** (frozen dataclasses). Für eine andere Frage ein neues `CustomerRequest`-Objekt erstellen statt bestehende Daten umzuschreiben.

## 7. Definition of Done

- [ ] JSON-Beispiel wird ohne Ollama als gültig erkannt.
- [ ] Negativer Preis wird abgelehnt.
- [ ] `null` und `false` sind eindeutig voneinander unterscheidbar.
- [ ] Eine eigene Frage kann mit `--frage` geprüft werden.
- [ ] Der lokale Ollama-Aufruf funktioniert (wenn Tag 6 funktioniert hat).
- [ ] 35 Python-Tests sind grün.
- [ ] Auf GitHub gesichert.

```powershell
git add agent_system/inputs.py agent_system/demo.py agent_system/examples/tag7_input.json agent_system/tests/test_inputs.py PHASE2_TAG7.md
git commit -m "Phase 2 Tag 7: structured product and request inputs"
git push
```

**Tag 8:** Router klassifiziert Kundenanfragen und gibt eine begründete, testbare Agentenwahl zurück. Bis dahin noch keine Agentenauswahl und keine automatisierten Preiszusagen.
