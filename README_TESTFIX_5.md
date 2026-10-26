# Fundplatz – Testfix nach Tag 23 / käuferfreundliche Antworten

## Befund: 340 Django-Tests, 5 Fehler

1. Tag 17 `test_html_in_kundenfrage_und_draft_wird_escaped`: ein **legitimer Inline-Script-Block** am Ende der Verkäuferdetailseite löst `assertNotIn(b"<script>", ...)` aus. Die Kundeninhalte sind schon richtig escaped.
2. Tag 18 `test_html_wird_in_editor_und_detail_escaped`: gleicher Grund auf der Detailseite.
3. Tag 19 `test_html_in_antwort_wird_escaped`: gleicher Grund auf der Detailseite.
4. Tag 18 `test_ki_original_ist_erste_vorbelegung`: der neue käuferfreundliche Vorschlag wird jetzt absichtlich statt der technischen KI-Vorlage vorbefüllt. Der aktualisierte Test prüft den neuen Text und den unveränderten Originalentwurf. Die künstliche Testanzeige bietet explizit Versand an, damit Testdaten und KI-Ausgangstext nicht widersprechen.
5. Tag 23 `test_18_seller_kann_queue_status_sehen`: die Oberfläche heißt nun `Wartet auf Worker`, nicht `KI-Entwurf wartet auf Worker`.

### Korrektur

- `listings/templates/listings/seller_inquiry_detail.html`: Inline-JavaScript durch `defer`-geladenes **lokales** Skript ersetzen. Die Kundentexte bleiben Django-escaped; wir entfernen/entschärfen keine XSS-Tests.
- `static/js/inquiry_processing_refresh.js`: Reload nur bei `queued` oder `running` (über festes Datenattribut im DOM). Kein dynamischer JS-Code aus Anfragen.
- `listings/test_day18.py`: Regressionstest an neue Editor-Funktion anpassen und widersprüchliche Testdaten bereinigen.
- `listings/test_day23.py`: Statusanzeige auf den echten aktuellen Wortlaut und das Reload-Skript prüfen.

Keine Migration, keine Änderungen an Views, Business-Logik, Agenten oder echten Nutzerdaten.

### Installation (Windows / PowerShell, `.venv` aktiv)

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag23_5_django_tests_fix.zip" -DestinationPath "." -Force
python manage.py check
python manage.py test listings.test_day17 listings.test_day18 listings.test_day19 listings.test_day23 -v 2
python manage.py test listings
```

Erwartung: Die fünf vorherigen Testfehler sollten verschwinden. Ein tatsächlicher OK-Status ist erst nach deinem Django-Testlauf bestätigt.

Optionale Prüfung der JS-Datei: Starte `python manage.py runserver`, öffne als Verkäufer eine Anfrage und prüfe im Browser unter `/static/js/inquiry_processing_refresh.js`, ob das Script erreichbar ist. Bei wartender/laufender Verarbeitung wird die Detailseite alle fünf Sekunden aktualisiert.

Wenn alle Tests erfolgreich sind:

```powershell
git add listings/templates/listings/seller_inquiry_detail.html static/js/inquiry_processing_refresh.js listings/test_day18.py listings/test_day23.py
git commit -m "Fix: XSS-Testkollision und Tag23-UI-Regressionen"
git push
```

Die Logs `RuntimeError: LLM offline`, `Ollama nicht da`, `SECRET` kommen aus absichtlich simulierten Fehlerszenarien; allein die `FAIL:`-Einträge waren Testfehler. Logs mit geheimen Werten vor Veröffentlichung prüfen.
