# Fundplatz – Phase 3, Tag 22: Sicherheitsreview

## Ziel

Django-Anfragen, Verkäuferbearbeitung, Freigaben und Käuferpostfach gegen unerlaubte Zugriffe und versehentliche Datenoffenlegung absichern. Alle Antwortentwürfe bleiben privat, bis ein Verkäufer den Text **freigibt und zusätzlich bereitstellt**.

## Sicherheitsverbesserungen

1. **Private Seiten werden nicht zwischengespeichert.** `@never_cache` gilt nun für Verkäuferpostfach, Verkäuferdetail, privaten Editor, Freigabeseite, Käuferpostfach und Käuferdetail. Erwarteter HTTP-Header: `Cache-Control: max-age=0, no-cache, no-store, must-revalidate, private` (Reihenfolge/Schreibweise kann variieren).
2. **Kritischer Status darf nicht durch einen Status-Klick versteckt werden.** Bei `needs_attention` antwortet `/anfragen/<id>/bearbeitung/` mit HTTP 409. Eine manuelle Bearbeitung bleibt möglich, aber die Warnstufe bleibt erhalten.
3. **Keine automatische Vorbelegung bei kritischem KI-Lauf.** Ein gefährdeter Entwurf wird nicht als fertig wirkender Text in den Editor übernommen. Bereits gespeicherte Verkäufertexte bleiben sichtbar.
4. **Cookie- und HTTP-Schutz.** Explizite HttpOnly- und SameSite=Lax-Cookies, `nosniff`, `Referrer-Policy: same-origin`, `X-Frame-Options: DENY`. Django-Middleware für CSRF, Security und Clickjacking bleibt aktiviert.
5. **50 neue Regressionstests.** Für Berechtigungen, CSRF, HTML-Escaping, Statusinvarianten, Overposting, Rate-Limit, Freigabe- und Bereitstellungstrennung sowie Browser-Cache.

## Installation in deinem VS-Code-Terminal

Die virtuelle Umgebung `(.venv)` ist bereits aktiv – nur `python` verwenden.

```powershell
cd C:\Kleinanzeigen
git status
Copy-Item .\db.sqlite3 .\db_backup_vor_tag22.sqlite3
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag22.zip" -DestinationPath "." -Force
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test listings.test_day22 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
```

**Keine Migration** an Tag 22: Nur Views, Template, Einstellungen und Tests ändern sich.

## Manuelle Sicherheitsprüfung

1. Als Käufer anmelden. Eigene Anfrage öffnen. Interne KI-Texte, Verkäufertext und Audit dürfen **nicht** auftauchen. Eine interne Freigabe allein erzeugt keine sichtbare Antwort.
2. Als anderer Käufer dieselbe Detail-URL aufrufen – `404`.
3. Als fremder Verkäufer eine private Verkäuferdetail-URL öffnen – `404`.
4. Als richtiger Verkäufer eine Anfrage mit Status `needs_attention` öffnen. Die Statuswarnung bleibt sichtbar. Der Button „Als In Bearbeitung markieren“ fehlt; der Editor bleibt verfügbar.
5. Im Browser-Entwicklertool im Tab Netzwerk private Seiten prüfen: Response Header `Cache-Control` enthält `no-store`.
6. Eine Antwort erst dann bereitstellen, wenn die Verkäuferfassung ausdrücklich freigegeben wurde. Käufer sieht nur den ausgelieferten Snapshot.

## Wichtige Grenzen

- `DEBUG=True`, Entwicklungs-SECRET_KEY und lokales HTTP sind nur für `localhost` vertretbar, **nicht für öffentliches Hosting**. Für Deployment müssen HTTPS, sichere Secrets, Hosts, Rate-Limiting (auch für parallele Requests), Logging und Upload-Regeln gesondert gehärtet werden.
- Die bestehende Begrenzung von fünf Anfragen pro Käufer und Stunde verwendet SQLite-Zählung. Sie ist kein produktionsreifes, verteiltes oder konkurrenzsicheres Rate-Limit.
- `no-store` reduziert Browser-Caching, verhindert aber nicht Screenshots oder bewusstes Kopieren.
- `autoescape`, CSRF und Zugriffskontrolle ersetzen kein vollständiges Penetration Testing.
- Tests müssen auf deinem Rechner mit Django 5.2 in der aktiven `.venv` ausgeführt werden. Der Archiv-Build kann hier mangels Django-Paket nur statisch geprüft werden.

## Git

Nach erfolgreichen Tests:

```powershell
git add config/settings.py listings/views.py listings/templates/listings/seller_inquiry_detail.html listings/test_day22.py PHASE3_TAG22.md
git commit -m "Phase 3 Tag 22: Security hardening und Tests"
git push
```

## Nächster Schritt – Tag 23

Leistungsfähigkeit und Ausfallverhalten von Ollama bei Webanfragen verbessern: Timeout-Grenzen, Queue/Background-Jobs und Status bei längeren Generierungen. Vorher keine Hintergrundverarbeitung behaupten – Tag 22 ist noch synchron.
