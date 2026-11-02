# Technische Architektur

[← Projektübersicht](../README.md) · [Tests](testing.md) · [Evaluation](evaluation/README.md)

## Ziel und Systemgrenzen

Fundplatz ist ein lokal betriebener Marktplatz auf Basis von **Django, SQLite und serverseitig gerenderten Templates**. Die KI-Komponente unterstützt Verkäufer beim Formulieren von Antworten auf Käuferanfragen. Antworten werden nicht autonom veröffentlicht und nicht an externe Plattformen versendet.

## Komponenten und Verantwortlichkeiten

| Baustein | Verantwortung | Quellcode |
| --- | --- | --- |
| Django-Konfiguration | URLs, Authentifizierung, Datenbank, optionale Agenten- und Queue-Schalter | [`config/`](../config/) |
| Marktplatz | Registrieren, Inserate, Suche, Formulare, Eigentümer-/Zugriffsprüfung, Verkäufer- und Käuferansichten | [`listings/`](../listings/) |
| Datenmodell | `Listing`, `CustomerInquiry`, `InquiryDelivery`, `InquiryEvent` | [`models.py`](../listings/models.py) |
| Übergang zur KI | Wandelt Anzeige + Anfrage in validierte Agenteneingaben um | [`agent_bridge.py`](../listings/agent_bridge.py) |
| Agentensystem | Routing, drei Spezialagenten, Vorlagen und Validierung | [`agent_system/`](../agent_system/) |
| Ollama | Optionaler lokaler Modellaufruf, zur Standardnutzung nicht nötig | [`ollama_client.py`](../agent_system/ollama_client.py) |
| Async-Verarbeitung | Optionale SQLite-basierte Queue und separater Worker | [`draft_queue.py`](../listings/draft_queue.py), [`process_inquiries.py`](../listings/management/commands/process_inquiries.py) |
| Darstellung | Django-Templates, Bootstrap, eigenes CSS und kleines JS zur Statusaktualisierung | [`templates/`](../templates/), [`static/`](../static/) |

## Daten- und Kontrollfluss

```text
Käufer --> Django: Anfrage zu fremder aktiver Anzeige
       --> CustomerInquiry (privat)
       --> listings.agent_bridge (ProductContext + CustomerRequest)
       --> AgentPipeline: Eingabe-Audit und Orchestrator
           |-- InformationAgent  (Produktdaten)
           |-- NegotiationAgent  (Preis und Verhandlungsbasis)
           |-- LogisticsAgent    (Versand, Abholung)
       --> Prüf- und Validierungsregeln
       --> CustomerInquiry.private_draft
       --> Verkäufer prüft/bearbeitet: seller_draft
       --> Verkäufer bestätigt: approved_response + approved_at/by
       --> Verkäufer stellt separat bereit
       --> InquiryDelivery.response_text (unveränderlicher veröffentlichter Textstand)
       --> Käuferpostfach
```

Die genaue Klassifikation kann mehrere Agenten auswählen. Fehlende Angaben werden nicht einfach aus Titel oder Produktkategorie erfunden: Eine aktive Anzeige bedeutet zum Beispiel **nicht automatisch**, dass die Ware als verfügbar bestätigt ist. Das System benutzt für die sichere Basisantwort ausschließlich hinterlegte beziehungsweise eingegebene Informationen.

## Unterschied zwischen Regeln und LLM

- **Standard (`FUNDPLATZ_AGENT_USE_LLM=0`):** Regelbasierter Router und deterministische Basisantworten, ohne Ollama-Abhängigkeit.
- **Optional (`FUNDPLATZ_AGENT_USE_LLM=1`):** Ollama/Qwen kann Routing unterstützen und zusätzliche Formulierungsvorschläge erstellen. Freie Modellformulierungen werden **nicht automatisch** in die verbindliche, zusammengeführte Antwort übernommen; der Verhandlungsagent verwendet keine freien LLM-Antwortformulierungen.
- **Fallback:** Unverfügbare Modelle, Routingprobleme oder Konflikte werden durch Regelpfade, Rückfragen beziehungsweise Bearbeitungshinweise behandelt. Das ist keine Garantie vollständiger Faktenrichtigkeit.

## Datenabgrenzung und Freigabe

1. Anfragen sind einem Käufer, einer Anzeige und deren Verkäufer zugeordnet; die Django-Views prüfen Besitzerrechte.
2. `private_draft` ist ein interner Vorschlag, `seller_draft` die vom Verkäufer bearbeitete Fassung.
3. `approved_response` ist eine explizit freigegebene interne Momentaufnahme; **Freigabe ist nicht Bereitstellung**.
4. `InquiryDelivery` enthält den separat bereitgestellten Antwort-Snapshot für das Käuferpostfach; spätere Bearbeitungen am privaten Entwurf verändern diesen nicht automatisch.
5. `InquiryEvent` dokumentiert relevante Zustandsübergänge; Käufer und Verkäufer erhalten unterschiedliche Sichten auf den Verlauf.

Die technischen Grenzen und die Absicherung sind durch Regressionstests geprüft, aber nicht als vollständige Sicherheitszertifizierung zu verstehen.

## Optionale Warteschlange

Bei `FUNDPLATZ_AGENT_ASYNC=1` wird die Anfrage eingereiht statt in der HTTP-Anfrage verarbeitet. Ein separater Management-Worker beansprucht den Eintrag und aktualisiert `queued`, `running`, `ready` oder `failed`. Die Implementierung verwendet bedingte Updates und eine Versuchszahl, um bestimmte überholte Worker-Schreibvorgänge zu verhindern. Die Queue ist **lokal mit SQLite** realisiert und kein skalierbares Produktions-Queue-System. Ohne laufenden Worker verbleiben Einträge in der Warteschlange.

## Bewusste Grenzen

- Keine automatische Preiszusage, keine Zahlungsabwicklung und keine Integration mit externen Kleinanzeigen-Nachrichten.
- Keine Garantie, dass eingegebene Produktdetails wahr oder KI-Vorschläge sachlich korrekt sind.
- Entwicklungsbetrieb: SQLite, lokales Medienverzeichnis `media/`, `DEBUG=True` und Development-Secret-Key-Fallback; **nicht** ohne Deployment-Härtung öffentlich betreiben.
- Keine abgeschlossenen Browser-, Last-, Backup-/Restore- oder vollständigen Sicherheitsprüfungen.
- Beim Löschen einer Anzeige werden gespeicherte Bilddateien laut Dokumentation nicht automatisch vom Datenträger entfernt.

[Tests und Abnahme](testing.md) · [Historische Entscheidungen](development-history/README.md)
