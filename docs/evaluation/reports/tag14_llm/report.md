# Fundplatz – Tag 14 Evaluation (llm)

**Ausgewertet:** 40 Szenarien; vollständig bestandene Prüfpakete: 39.

## Kennzahlen

| Messgröße | Wert |
|---|---:|
| Exakte Agentenmengen | 97.5 % |
| Agenten-Präzision / Recall | 97.6 % / 100.0 % |
| Rückfragen richtig erkannt | 100.0 % |
| Erwartete Audit-Codes gefunden (n=8) | 100.0 % |
| Erwartete Blockierungen gefunden (n=5) | 100.0 % |
| Stichwort-Prüfungen bestanden | 100.0 % |
| Riskante Zusage-Muster im sichtbaren Entwurf | 0 |
| Fälle mit unerwarteten Zahlen | 0 |
| Verkäuferfreigabe erforderlich | 100.0 % |

Router-Herkunft: `{"llm": 40}`

## Kategorien

| Kategorie | Fälle | Komplett bestanden | Exaktes Routing |
|---|---:|---:|---:|
| availability | 4 | 4 | 100.0 % |
| condition | 4 | 4 | 100.0 % |
| conflict | 4 | 4 | 100.0 % |
| injection | 4 | 4 | 100.0 % |
| logistics | 4 | 4 | 100.0 % |
| missing | 4 | 4 | 100.0 % |
| multi | 4 | 4 | 100.0 % |
| negotiation | 4 | 3 | 75.0 % |
| technical | 4 | 4 | 100.0 % |
| unclear | 4 | 4 | 100.0 % |

## Auffällige Fälle

- **N04** (negotiation): Routing erwartet `negotiation`, gefunden `information,negotiation`

## Aussagegrenzen

- Erwartete Agenten und Stichwörter wurden vor dem Test manuell festgelegt; der Router hat sie nicht erzeugt.
- Stichwort-, Zahlen- und Regex-Prüfungen sind **keine** vollständige semantische Faktenprüfung.
- Offline-Messungen bewerten das regelbasierte Routing, **nicht** die Qualität von Qwen.
- Im LLM-Modus stammen einzelne Entscheidungen ggf. aus `fallback`; die Spalte `source` zeigt das an.
- Die Agenten senden keine Nachrichten und geben nichts automatisch frei; Verkäuferprüfung bleibt Pflicht.
