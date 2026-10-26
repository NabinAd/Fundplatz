# Fundplatz Tag 22 – Testfix für Rate-Limit-Test 35

**Ursache:** `setUpTestData()` legt für `self.stranger` bereits eine `CustomerInquiry` bei `self.other_listing` an. Test 35 legte zusätzlich fünf Anfragen an und erwartete danach fünf statt sechs. Die Implementierung zählt korrekt alle Anfragen desselben Käufers innerhalb einer Stunde, unabhängig von der Anzeige.

**Korrektur:** Test 35 erstellt einen separaten Käufer mit null bisherigen Anfragen, legt fünf an und prüft, dass die sechste abgewiesen und nicht gespeichert wird. Produktivcode und Rate-Limit bleiben unverändert.

## Installation bei bereits aktivierter `.venv`

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag22_testfix.zip" -DestinationPath "." -Force
python manage.py test listings.test_day22.Day22SecurityTests.test_35_inquiry_hourly_limit_rejects_sixth -v 2
python manage.py test listings.test_day22 -v 2
python manage.py test listings
```

Keine Migration. Der Patch ersetzt nur `listings/test_day22.py`.
