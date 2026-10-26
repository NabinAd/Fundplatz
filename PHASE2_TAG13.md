# Phase 2 – Tag 13: Robustheit der gesamten Multi-Agent-Pipeline

## Ziel

Wir haben jetzt **Router + Information + Negotiation + Logistics + Validator**. Heute
machen wir die Verbindung robuster. Keine neue Datenbank, keine Django-Änderung,
kein Framework für Multi-Agenten, keine automatische Kundenkommunikation.

## Installation unter Windows (PowerShell in VS Code)

Voraussetzung: Tag 12 ist installiert, die virtuelle Umgebung `(.venv)` ist aktiviert.

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase2_tag13.zip" -DestinationPath "." -Force
python -m agent_system.tag13_demo --alle
python -m unittest discover -s agent_system/tests -v
```

Optional **eine** echte Anfrage mit Ollama:

```powershell
python -m agent_system.tag13_demo --fall mehrfach --mit-ollama
python -m agent_system.tag13_demo --fall mehrfach --mit-ollama --frage "Ist Versand möglich und wäre 180 Euro okay?"
```

Falls du Ollama nicht gestartet hast, bleibt der existierende regelbasierte
Fallback aktiv. `--alle` ist bewusst Offline, damit es schnell bleibt.

## Was wurde geändert?

| Datei | Zweck |
| --- | --- |
| `agent_system/safety.py` | Erkennt einige eindeutige Widersprüche in Produktdaten und prüft LLM-Routing auf fehlende, regelbasiert erkennbare Anliegen |
| `agent_system/pipeline.py` | Protokolliert `audit`, blockiert betroffene Antwortteile, verarbeitet partielle Agenten-/Validator-Ausfälle sicher |
| `agent_system/tag13_demo.py` | Sechs interaktive Testfälle ohne Ollama; optional einer mit Qwen |
| `agent_system/tests/test_safety.py` | Isolierte Tests für Eingabe-Audit und Routing |
| `agent_system/tests/test_integration_day13.py` | Gesamttests für mehrere Agenten, Ausfälle und Unsicherheiten |

## 1. Warum Router-Gegenprüfung?

Eine formal gültige LLM-Entscheidung kann trotzdem ein Anliegen übersehen.

**Kundenfrage:** „Zustand und Versand?“

**LLM-Router (falsche Teilantwort):** `information`

**Regelrouter erkennt:** `information`, `logistics`

**Tag 13:** `logistics` wird ergänzt. Im Feld `audit` steht
`router_missing_intent`; die Router-Ausgabe erhält einen Warnhinweis. Die
ursprüngliche Modellentscheidung ist damit **nicht** als vollständig korrekt
bewiesen. Die Gegenprüfung ist nur für *explizit erkannte* Absichten zuständig.

Der Regelrouter entfernt absichtlich keine Agenten aus der LLM-Liste, da
Heuristiken umschriebene Fragen nicht zuverlässig erkennen. Ein nicht von Regeln
bestätigter Agent wird ggf. mit `router_unconfirmed_agent` protokolliert.

## 2. Warum Eingabe-Audit?

Bei widersprüchlichen Daten dürfen wir keine scheinbar sichere Antwort geben.

**Beispiel:**

- Strukturiertes Feld: `shipping_available = false`
- Produktbeschreibung: `Versand möglich.`
- Anfrage: `Ist Versand möglich?`
- **Ergebnis:** `audit = shipping_conflict`, Antwortteil `blocked`.

Der Audit prüft außerdem einige eindeutige Widersprüche bei Abholung und
Verfügbarkeit. Unbekannte Werte (`null`) gelten **nicht** als Widerspruch.
Bei erkannten Prompt-Injection-Sätzen in Produktbeschreibung oder Kundenfrage
wird ein Warnhinweis protokolliert. Wird eine verdächtige Produktbeschreibung
für eine Informationsantwort benötigt, bleibt dieser Antwortteil blockiert.

Diese Textmuster sind **kein vollständiger semantischer Faktencheck** und
können nicht jede manipulierte oder widersprüchliche Angabe erkennen.

## 3. Warum partielle Fehlerbehandlung?

Wenn der Information Agent funktioniert, aber Logistics intern scheitert,
müssen wir nicht den ganzen Vorgang abbrechen. Die sichere Information kann als
Entwurf bleiben; der Logistikteil wird durch einen neutralen Fehlerhinweis
ersetzt. Im `audit` erscheint `agent_execution_error`.

Bei **Routerfehlern** wird keine freie Antwort erzeugt: Die Pipeline fragt nach,
protokolliert `router_error` und stellt den Vorgang zur Verkäuferprüfung.
Fehlerdetails aus internen Exceptions erscheinen absichtlich **nicht** im
Kundentext oder im JSON-Ergebnis.

## Sechs praktische Szenarien

```powershell
python -m agent_system.tag13_demo --alle
python -m agent_system.tag13_demo --fall widerspruch
python -m agent_system.tag13_demo --fall fehlend
python -m agent_system.tag13_demo --fall manipulation
python -m agent_system.tag13_demo --fall unklar
```

- **mehrfach:** drei Agenten; Preisverhandlung ohne Zusage
- **widerspruch:** Versanddaten widersprechen sich; Logistikentwurf blockiert
- **fehlend:** unbekannte Verfügbarkeit und Zustand werden nicht erfunden
- **unklar:** es kommt eine Rückfrage statt einer erfundenen Antwort
- **manipulation:** eine Steueranweisung wird protokolliert, nicht befolgt
- **verfuegbarkeit:** widersprüchliche Verfügbarkeitsdaten; Information blockiert

## Was im JSON neu ist

`PipelineResult.to_dict()` enthält zusätzlich:

```json
"audit": [
  {
    "code": "shipping_conflict",
    "detail": "Versandangabe und Produktbeschreibung widersprechen sich; Versandantwort zurückhalten.",
    "affected_agents": ["logistics"]
  }
]
```

Die bisherigen Felder (`route`, `replies`, `combined_draft`,
`review_status`, `factual_validation`, `validation`) bleiben erhalten.

**Wichtig:** `validation` meldet nun bei einem von der Eingabeprüfung
zurückgehaltenen Agenten ausdrücklich `draft_status: blocked` und zusätzlich
`conflicting_input_hold`. Der Leser muss sich also nicht allein auf die
separate `audit`-Liste verlassen.

## Definition of Done

- [ ] `python -m agent_system.tag13_demo --alle` zeigt alle sechs Fälle
- [ ] Bei „widerspruch“ erscheint `shipping_conflict` und `blocked`
- [ ] Bei „fehlend“ wird Unbekanntes nicht als Tatsache ausgegeben
- [ ] Bei „unklar“ erscheint eine Rückfrage
- [ ] Bei „manipulation“ wird keine Preiszusage gemacht
- [ ] `python -m unittest discover -s agent_system/tests -v`: **216 Tests, OK**
- [ ] Optional: eine echte Ollama-Frage auf dem eigenen Rechner geprüft

**Git nach erfolgreichen Prüfungen:**

```powershell
git add agent_system PHASE2_TAG13.md
git commit -m "Phase 2 Tag 13: robuste Agenten-Pipeline"
git push
```

## Weiter mit Tag 14

An Tag 14 bauen wir eine **reproduzierbare Szenario-Evaluation** mit
Klassifikations- und Sicherheitsmetriken. Die verpflichtenden 30 repräsentativen
Fälle für das Gesamtprojekt prüfen wir spätestens in Phase 3 zusammen mit
der echten Django-Integration.

**Unveränderte Grenzen:** kein automatischer Versand, keine automatische
Verkäuferfreigabe, keine Preisannahme, keine Änderung von Produktdaten. Die
Regelprüfungen und Beispieltests sind kein Beweis allgemeiner LLM-Zuverlässigkeit.
