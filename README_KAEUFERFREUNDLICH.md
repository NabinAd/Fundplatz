# Käuferfreundliche Antwortentwürfe – Ergänzung nach Tag 23

## Warum?

`route_source='llm'` bedeutet nur, dass der Router Qwen benutzt hat. Die
sichtbaren Vorlagen kommen aus `agent_system/agents.py` und sind absichtlich
konservativ. Die neuen Formulierungen sind kurze, natürlich klingende **Entwürfe
für den Verkäufer**, keine freigegebenen, versendeten Kundennachrichten.

## Änderungen

- Neues Modul `agent_system/customer_tone.py`: datengebundene Formulierungen ohne weiteren Modellaufruf.
- Verkäuferdetail zeigt neben dem technischen KI-Text einen verständlicheren Vorschlag.
- Der Editor verwendet bei neuen, normalen Anfragen diese Formulierung als Ausgangstext.
- Original-KI-Text und die bisherigen Prüf- und Freigabeschritte bleiben unverändert.
- Keine automatischen Preissenkungen, Versandkostenzusagen oder Versendungen.
- Bei kritischem Status, KI-Fehler oder blockierten Antwortteilen: **kein automatischer Käufertext**.
- Bereits manuell gespeicherte Entwürfe behalten Vorrang und bleiben unverändert.

Der Tonfall-Generator ist regelbasiert und weder ein semantischer Validator noch
vollständige freie KI-Textgenerierung. Jede Antwort muss weiterhin vom Verkäufer
geprüft und ausdrücklich freigegeben und bereitgestellt werden.

## Installation (PowerShell, .venv bereits aktiv)

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_kaeuferfreundliche_antworten.zip" -DestinationPath "." -Force
python -m unittest discover -s agent_system/tests -v
python manage.py test listings.test_buyer_tone -v 2
python manage.py test listings
python manage.py runserver
```

Als Verkäufer `/anfragen/` öffnen und eine bereits verarbeitete, nicht
freigegebene Anfrage mit erkannten Agenten öffnen. Die neue Karte heißt
**Käuferfreundliche Formulierung (Vorschlag)**. Im Editor wird sie vorbefüllt.

**Keine Datenbankmigration nötig.** Änderungen bitte erst nach erfolgreichem
Django-Testlauf committen.
