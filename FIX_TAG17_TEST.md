# Fundplatz – Testkorrektur für Tag 17

## Ursache

`listings.test_day16.DjangoAgentBridgeTests.test_anfrage_wird_gespeichert_und_draft_bleibt_privat` erwartet den Offline-Regelrouter (`rules`).
War in PowerShell zuvor `FUNDPLATZ_AGENT_USE_LLM=1` gesetzt, wurde stattdessen real Ollama angesprochen (`llm`).
Der Test durfte nicht von einer Umgebungsvariable abhängen.

## Änderung

In `listings/test_day16.py` bekommt die ganze Testklasse den Dekorator
`@override_settings(FUNDPLATZ_AGENT_USE_LLM=False)`.
Damit sind alle normalen Tests der Klasse deterministisch und verwenden keinen echten Ollama-Aufruf.
Der bewusst eingerichtete Test `test_llm_ist_opt_in` setzt die Einstellung innerhalb der Methode explizit wieder auf `True` und testet diesen Spezialfall mit einem Mock.
Die produktive Django-App, die Datenbank, das Modell und die Agenten ändern sich nicht.

## Installation (virtuelle Umgebung bereits aktiviert)

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag17_testfix.zip" -DestinationPath "." -Force
python manage.py test listings.test_day16 -v 2
python manage.py test listings
```

Danach optional den Tag-18-Stand installieren. Der Testfix ist auch mit Tag 18 kompatibel.
Die absichtlich simulierte Fehlermeldung `RuntimeError: LLM offline` im Testlog
ist kein Testfehlschlag, solange am Ende `OK` steht.
