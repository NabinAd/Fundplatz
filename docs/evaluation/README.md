# Historische Agenten-Evaluationen

[← Projektübersicht](../../README.md) · [Teststrategie](../testing.md) · [Agentenarchitektur](../../architecktur.md)

## Methode

Die historische Evaluation prüft vordefinierte Produktdaten und Käuferfragen gegen **vorher festgelegte Erwartungen**: ausgewählte Agenten, Rückfragen, erwartete Prüfhinweise, Blockierungen, Textfragmente und auffällige Zahlen beziehungsweise Zusagen. Im Offline-Modus wird der Regelrouter bewertet; im LLM-Modus ist lokales Ollama am Routing beteiligt. Berichte enthalten Markdown-, CSV- und JSON-Ausgaben.

## Dokumentierte Ergebnisse (keine neuen Messungen)

| Bericht | Betriebsart | Vollständig bestandene Szenarien | Einordnung |
| --- | --- | ---: | --- |
| [Tag 14 offline](reports/tag14_offline/report.md) | Regelrouter | **36/40** | Ältere Baseline, u. a. Lücken bei Verfügbarkeit |
| [Tag 14 LLM](reports/tag14_llm/report.md) | Ollama-Routing | **39/40** | Ein zusätzlicher Agent im Fall N04 |
| [Tag 15 vorher](reports/tag15_before/report.md) | Regelrouter | **36/40** | Vergleichsbaseline |
| [Tag 15 nachher](reports/tag15_after/report.md) | Regelrouter | **40/40** | Verbesserungen auf den bekannten Szenarien |
| [Tag 15 zusätzlich](reports/tag15_additional/report.md) | Regelrouter | **18/18** | Bereits zur Verbesserung genutzt, **kein unabhängiger Blindtest** |
| [Tag 15 LLM vollständig](reports/tag15_llm_full/report.md) | Ollama-Routing | **39/40** | Bekannte Abweichung N04 |

Jeder Bericht bleibt mit seinen ursprünglichen `report.md`, `report.json` und `report.csv` erhalten; nur der Speicherort wurde von `evaluation_reports/` nach `docs/evaluation/reports/` geändert.

## Was sich aus den Zahlen *nicht* ableiten lässt

- **40/40** bedeutet nur, dass die definierten Prüfkriterien dieser 40 Fälle erfüllt wurden; es bedeutet nicht 100 % Antwortgenauigkeit im echten Betrieb.
- Stichwort-, Regex- und Zahlenprüfungen sind **keine** vollständige semantische Faktenprüfung.
- Offline-Werte sind keine Aussage über die Qualität von Qwen.
- Die LLM-Berichte bestätigen keine Produktionssicherheit, keine rechtliche Zuverlässigkeit und keine vollautomatische Käuferkommunikation.
- Die zusätzlichen Tag-15-Fälle waren Entwicklungsinput und dürfen nicht als unabhängige Generalisierungsprüfung ausgegeben werden.

## Evaluation erneut ausführen

```powershell
.\.venv\Scripts\python.exe -m agent_system.evaluation --mode offline --out-dir docs/evaluation/local-offline
```

Für eine kleine lokale Modellstichprobe bei laufendem Ollama:

```powershell
.\.venv\Scripts\python.exe -m agent_system.evaluation --mode llm --per-category 1 --out-dir docs/evaluation/local-llm
```

Der Exitcode alleine ersetzt nicht die Auswertung der berichteten Qualitätsabweichungen. Lokale erneute Berichte möglichst in separaten, nicht für Git bestimmten Ordnern ausgeben. Weitere Testbefehle stehen unter [Testing](../testing.md).

