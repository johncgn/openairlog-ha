# OpenAirLog für Home Assistant

Holt deinen **Dienstplan und dein Flugbuch** von [OpenAirLog](https://openairlog.de)
nach Home Assistant — rein lesend.

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
