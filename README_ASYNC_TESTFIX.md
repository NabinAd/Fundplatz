# Fundplatz – Fix für 5 Testfehler nach Tag 24

## Ursache

Tag 24 aktiviert beim manuellen Testen `FUNDPLATZ_AGENT_ASYNC=1`. Die alten Django-Testklassen für Tag 16 und Tag 21 haben nur das LLM deaktiviert, aber nicht den asynchronen Modus. Deshalb laufen die Tests in einer noch aktiven PowerShell unerwartet im Queue-Modus. Der KI-Entwurf wird dann erst vom Worker erstellt und die Tests finden ihn nicht sofort.

## Änderung

In `listings/test_day16.py` und `listings/test_day21.py` wird jeweils der Klassendekorator erweitert auf:

```python
@override_settings(FUNDPLATZ_AGENT_USE_LLM=False, FUNDPLATZ_AGENT_ASYNC=False)
```

Das ändert ausschließlich die Testkonfiguration. Die Anwendung bleibt im gewählten Modus; der asynchrone Ablauf wird weiter in Tag 23 und Tag 24 getestet. Keine Migration erforderlich.

## Installation in PowerShell bei aktivierter .venv

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag24_async_testfix.zip" -DestinationPath "." -Force
python manage.py test listings.test_day16 listings.test_day21 -v 2
python manage.py test listings
```

Für einen sofortigen Test ohne ZIP genügt alternativ:

```powershell
$env:FUNDPLATZ_AGENT_ASYNC="0"
$env:FUNDPLATZ_AGENT_USE_LLM="0"
python manage.py test listings
```

Das Tag-25-Skript `scripts/tag25_abnahme.ps1` setzt während der Abnahme beide Variablen selbst auf `0` und stellt sie anschließend wieder her.

## Prüfung

Python-Syntax und ZIP-Struktur geprüft. Kein Django-Paket in der Erstellungsumgebung; Testausführung in Windows erforderlich.
