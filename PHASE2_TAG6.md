# Fundplatz: Phase 2 / Tag 6 – Lokale LLM-Verbindung

Dieses Update wird **im Wurzelordner deines bestehenden Django-Projekts** entpackt.
Es ergänzt nur `agent_system/` und diese Anleitung. Die Django-Dateien und SQLite-Datenbank bleiben unverändert.

## 1. Hardware und Ollama kontrollieren (PowerShell)

```powershell
cd C:\Kleinanzeigen
ollama --version
nvidia-smi
ollama list
```

Wenn `ollama` nicht gefunden wird: Ollama öffnen und ein neues VS-Code-Terminal starten. Die Windows-App läuft normalerweise im Hintergrund.

## 2. Ein Modell lokal herunterladen und kurz testen

```powershell
ollama pull qwen3:4b-instruct
ollama run qwen3:4b-instruct "Antworte in einem Satz auf Deutsch: Funktioniert Ollama?"
ollama ps
```

Mit `ollama ps` die Spalte `PROCESSOR` prüfen (GPU/CPU-Auslastung des Modells im Speicher).

## 3. Unabhängigen Python-Test starten

Im **Repository-Wurzelordner** (`C:\Kleinanzeigen`):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s agent_system/tests -v
```

Erwartet: **4 Tests, OK**. Diese Tests brauchen keinen Ollama-Server und kosten keine Tokens.

## 4. Erste echte Modellanfrage aus Python

```powershell
.\.venv\Scripts\python.exe -m agent_system.demo
```

Alternativ:

```powershell
.\.venv\Scripts\python.exe -m agent_system.demo --frage "Ist die Abholung möglich?"
```

Die Demo sendet einen Beispielartikel und deine Frage an Ollama `/api/chat`. Sie misst die End-to-End-Antwortzeit.
**Achtung:** Die Demo ist noch kein fertig geprüfter Agent; keine externen Nachrichten versenden oder Preiszusagen automatisieren.

## 5. Git (nach erfolgreichem Test)

```powershell
git add agent_system PHASE2_TAG6.md
git commit -m "Phase 2 Tag 6: local Ollama client and smoke tests"
git push
```

## Fehlerbehebung

- `ollama` unbekannt: Windows-Anwendung starten und Terminal neu öffnen.
- `Ollama ist nicht erreichbar`: Die Ollama-App sollte unter `http://127.0.0.1:11434` erreichbar sein; andernfalls Ollama neu starten.
- `Ollama meldet HTTP 404`: Modellbezeichnung mit `ollama list` vergleichen.
- Zeitüberschreitung: Erst `ollama run` ausprobieren, gegebenenfalls längere Modellladezeit zulassen.
- `100% CPU` bei `ollama ps`: NVIDIA-Treiber/GPU-Nutzung prüfen und andere GPU-intensive Anwendungen schließen.

## Definition of Done

- Qwen3-4B-Instruct läuft lokal.
- `ollama ps` zeigt, wie das Modell CPU und/oder GPU nutzt.
- Die vier Offline-Tests bestehen.
- Die Python-Demo liefert einen Antworttext und zeigt die Zeit.
- Phase-2-Dateien sind separat vom Django-Projekt organisiert.

Nächster Schritt: Tag 7 erstellt getypte `ProductContext`- und `CustomerRequest`-Datenobjekte und prüft die Eingabedaten.
