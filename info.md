# OpenAirLog für Home Assistant

**Kein Ersatz für [OpenAirLog](https://openairlog.de) — eine Brücke dorthin.**

Dein Flugbuch weiß, wann du wiederkommst. Deine Heizung weiß es nicht. Diese
Integration schließt genau diese Lücke: Dienste als Kalender und Sensoren in
Home Assistant, damit Automationen daran andocken können. Ausgewertet wird dein
Flugbuch weiterhin bei OpenAirLog — hier wird nur gelesen, nie geschrieben.

**Danke an den Entwickler von OpenAirLog** für das Werkzeug und die offene API.
Dies ist ein privates Projekt und **nicht offiziell** — Fragen dazu bitte ins
Repo, nicht an OpenAirLog.

## In drei Schritten

**1. API-Schlüssel erzeugen** in deinem OpenAirLog-Konto unter *Einstellungen → API*.
Nötig sind nur `profile:read`, `flights:read` und `statistics:read`.

**2. Integration hinzufügen** unter *Einstellungen → Geräte & Dienste* und den
Schlüssel einfügen. Er wird sofort geprüft.

**3. Auf dich einstellen** über *Konfigurieren*: Briefingzeit, Weg zur Basis und
nach Hause, sowie welche Dienstcodes bei deiner Airline *frei*, *Bereitschaft*
oder *Schulung* bedeuten.

## Was du danach hast

Eine mitgelieferte Karte („OpenAirLog Dienst") zeigt den nächsten Umlauf mit allen
Abschnitten, Briefing und Heimkehr. Dazu Sensoren für Dienstbeginn, Dienstende,
Losfahrzeit und Heimkehr, einen Kalender mit dem Dienstplan sowie Flugstunden und
Landungen.

Zusammenhängende Flüge werden zu einem **Umlauf** gebündelt — dem Zeitraum, in dem
du nicht zuhause bist. Genau der eignet sich für Heizung und Benachrichtigungen.
