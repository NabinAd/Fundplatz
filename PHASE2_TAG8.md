# Fundplatz – Phase 2, Tag 8: Orchestrator / Router

**Ziel:** Kundenfragen in **Information**, **Negotiation** und/oder **Logistics** einordnen, Auswahl begründen und unklare Fragen kennzeichnen. Heute werden **keine Agentenantworten** erstellt und **keine Nachrichten versendet**. Die spezialisierte Bearbeitung beginnt an Tag 9.

## 1. Dateien des Updates

- `agent_system/router.py` – `Orchestrator`, `RouteDecision`, JSON-Schema, regelbasierter Offline-Router, Fehlerbehandlung.
- `agent_system/router_demo.py` – Terminal-App, liest die vorhandene Tag-7-Beispieldatei und überschreibt auf Wunsch die Kundenfrage.
- `agent_system/ollama_client.py` – Tag-6-Client mit optionalem `response_format` erweitert; alle bestehenden Aufrufe funktionieren unverändert.
- `agent_system/tests/test_router.py` – Router-/Fallback-/JSON-Tests ohne Ollama-Netzwerk.
- `PHASE2_TAG8.md` – diese Anleitung.

Die Tag-7-Dateien `agent_system/inputs.py` und `agent_system/examples/tag7_input.json` bleiben unberührt. Django, SQLite, HTML, CSS und die 64 Marketplace-Tests ebenfalls.

## 2. Installation in VS Code / PowerShell

Da `(.venv)` bereits im Terminal erscheint, **nur `python` verwenden**:

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase2_tag8.zip" -DestinationPath "." -Force
```

Falls `git status` uncommittete eigene Änderungen zeigt, diese vor dem Entpacken sichern. Dieses Update ersetzt nur den Ollama-Client; es enthält keine Datenbankdateien.

## 3. Erste Entscheidungen OHNE Ollama testen

```powershell
python -m agent_system.router_demo --offline
python -m agent_system.router_demo --offline --frage "Ist Versand möglich?"
python -m agent_system.router_demo --offline --frage "Was ist dein letzter Preis?"
python -m agent_system.router_demo --offline --frage "Ist der Laptop noch da und kannst du ihn verschicken?"
python -m agent_system.router_demo --offline --frage "Hallo!"
```

Du siehst ein JSON mit:

- `agents`: erkannte Anliegen; mehrere Agenten bei kombinierten Kundenfragen.
- `primary_agent`: erster zuständiger Agent (oder `null`).
- `reason`: kurze Begründung.
- `needs_clarification`: `true` für unklare Fragen ohne gewählten Agenten.
- `source`: `rules`, `llm` oder `fallback`.
- `warning`: wenn Ollama fehlgeschlagen ist und die lokalen Heuristiken verwendet wurden.

Der Offline-Router ist bewusst **einfach** und wird komplizierte Fragen nicht immer korrekt klassifizieren. Seine Entscheidungen sind reproduzierbar und werden als Regelentscheidung markiert.

## 4. Routing MIT lokalem Ollama testen

```powershell
ollama list
python -m agent_system.router_demo
python -m agent_system.router_demo --frage "Ist der Laptop noch verfügbar und wäre 180 Euro möglich?"
python -m agent_system.router_demo --frage "Kann ich ihn abholen?"
```

Optional anderes Modell:

```powershell
python -m agent_system.router_demo --modell qwen3:4b-instruct --frage "Ist Versand möglich?"
```

Bei erfolgreicher Modellklassifikation steht `"source": "llm"`. Steht dort `"fallback"`, konnte die LLM-Klassifikation nicht korrekt abgeschlossen werden; die Warnung nennt den Grund. Das Programm **verschweigt** den Fallback nicht.

Das Modell antwortet über Ollamas `/api/chat` mit `format` als JSON-Schema und `temperature: 0`. **Trotz Schema prüft Python den Inhalt nochmals**: unzulässige Agentennamen, Duplikate, fehlende Felder oder widersprüchliche Flags werden abgewiesen.

## 5. Python-Tests

```powershell
python -m unittest discover -s agent_system/tests -v
```

Erwartet (bei unverändertem Tag-6/7-Projekt):

```text
Ran 67 tests
OK
```

Davon sind **32 Tests für Tag 8** und **35 Tests für Tag 6/7**. Die Tests benötigen keinen laufenden Ollama-Server. Die echten Modellentscheidungen musst du separat mit dem Befehl ohne `--offline` prüfen.

**Beispiel** für die Ausgabe:

```json
{
  "agents": ["information", "logistics"],
  "primary_agent": "information",
  "reason": "Kunde fragt nach Produkteigenschaft und Versand.",
  "needs_clarification": false,
  "source": "llm",
  "warning": null
}
```

Das ist ein Beispielformat, **keine garantierte Qwen-Ausgabe**. Die Reihenfolge der Agenten kann zwischen LLM-Läufen variieren. `reason` ist eine Erklärung des Routers, kein Nachweis der sachlichen Korrektheit.

## 6. Kontrolle und Git

Prüfe mindestens eine Informations-, Preis- und Logistikfrage, eine kombinierte Anfrage und eine unklare Frage. Die ausgegebene `source` muss mit deinem tatsächlich verwendeten Modus übereinstimmen.

```powershell
git add agent_system/router.py agent_system/router_demo.py agent_system/ollama_client.py agent_system/tests/test_router.py PHASE2_TAG8.md
git commit -m "Phase 2 Tag 8: structured intent routing"
git push
```

## 7. Wichtige Grenzen

- **Keine Agenten werden aufgerufen:** Das Routing benennt zuständige Fachagenten; deren Bearbeitungslogik kommt an Tag 9–11.
- **Keine verlässliche Confidence-Zahl:** Eine vom LLM behauptete Prozentzahl wäre unkalibriert; wir zeigen stattdessen Entscheidung, Begründung und Herkunft.
- **Keine Faktenprüfung:** Produktdaten und erzeugte Antwortentwürfe werden erst später gegen Regeln validiert (Tag 12).
- **Keine Freigabe/Übermittlung:** Das System versendet keine Nachrichten und macht keine Preiszusagen.
- Eine Prompt-Injection-Abwehr per Anweisung und JSON-Eingrenzung ist keine vollständige Sicherheit; Szenariotests und Validierung folgen.

**Tag 9:** Information Agent – Fragen zu Produktbeschreibung, Zustand, Technik und Verfügbarkeit mit bekannten Fakten beantworten.

Offizielle API-Dokumentation: https://docs.ollama.com/api/chat und https://docs.ollama.com/capabilities/structured-outputs
