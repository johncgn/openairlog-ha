# OpenAirLog-Addon für Home Assistant

**ein privates Addon für [OpenAirLog](https://openairlog.de) .**

OpenAirLog ist ein richtig starkes Flugbuch: Dienstplan, Statistiken,
Auswertungen, sauber gemacht und kostenlos. Diese Integration verbindet das Flugbuch
mit dem, was zuhause passieren soll.

Genau dafür ist das hier gedacht: Dienste als Kalender und Sensoren in Home
Assistant, damit Automationen daran andocken können — Heizung hochfahren, bevor
du aus Tokio zurück bist, Kaffee nur an Tagen ohne Frühdienst, eine Nachricht
nach Hause, wenn sich der Umlauf verschiebt.

Ausgewertet, geblättert und gepflegt wird dein Flugbuch weiterhin dort, wo es
hingehört: bei OpenAirLog. Die Integration ist **rein lesend** und schreibt
nichts zurück.

## Danke

Diese Integration lebt vollständig von der Arbeit eines anderen. **Danke an den
Entwickler von OpenAirLog** — für ein Werkzeug, das fliegendem Personal den
Alltag leichter macht, für die Mühe, die darin steckt, und für eine offene API,
die so etwas hier überhaupt erst möglich macht.

> **Kein offizielles Projekt.** Ich bin schlicht Nutzer von OpenAirLog — nicht
> an der Entwicklung beteiligt, in keiner Weise damit verbunden, und profitiere
> einfach von seiner Arbeit. Diese Integration ist privat entstanden und wird
> hier von mir gepflegt. Fragen und Fehler dazu also bitte **ins Repo hier**.


## Entitäten

| Entität | Bedeutung |
|---|---|
| `calendar.dienstplan` | Alle Umläufe und freien Tage als Kalender |
| `binary_sensor.im_dienst` | Läuft gerade ein Dienst? |
| `sensor.naechster_dienst` | **Briefing-Beginn** des nächsten Umlaufs |
| `sensor.dienstende` | Zurück an der Basis |
| `sensor.losfahren` | Wechselt mit: vor dem Dienst die Anfahrt, währenddessen die Heimkehr |
| `sensor.voraussichtlich_zuhause` | Dienstende plus Heimweg |
| `sensor.flugstunden_gesamt` | Blockstunden aus der Statistik |
| `sensor.landungen_gesamt` | Landungen aus der Statistik |

## Dashboard-Karte

Die Integration bringt eine eigene Lovelace-Karte mit — **keine getrennte
HACS-Installation nötig**, sie meldet sich beim Start selbst am Frontend an.
Im Kartenmenü heißt sie **„OpenAirLog Dienst"**.

```yaml
type: custom:openairlog-card
entity: sensor.openairlog_naechster_dienst   # optional, wird sonst gesucht
```

```
✈ Nächster Umlauf                    in 3 Tagen
So 12.07. 12:20 – Mi 15.07. 19:19
[LH716, LH717]  [2 Abschnitte]
──────────────────────────────────────────────
 14:10  EDDF ── LH716 ── RJTT  02:31⁺¹  B748
 04:57  RJTT ── LH717 ── EDDF  19:19    B748
──────────────────────────────────────────────
🚆  Losfahren in 3 Tagen um 10:20
🏠  Du bist Mi 15.07. um 21:49 zurück
```

Die Restzeit färbt sich nach Dringlichkeit — gelb ab drei Stunden, rot ab einer
Stunde, „jetzt los!" wenn die Losfahrzeit überschritten ist. Maßgeblich ist dabei
die **Losfahrzeit**, nicht der Dienstbeginn: Bei langer Anfahrt ist das die Zahl,
die zählt.

## Umläufe statt Einzelflüge

Zusammenhängende Flüge werden zu einem **Umlauf** gebündelt — dem Zeitraum, in dem
du nicht zuhause bist. Genau der zählt für Heizung und Benachrichtigungen.

* Bist du **nicht an der Basis**, läuft der Umlauf weiter (Layover, auch über Tage).
* Bist du **an der Basis**, gehört der nächste Flug nur dazu, wenn die Standzeit
  unter der Turnaround-Grenze liegt (Standard 180 Minuten). So bleibt ein
  Kurzstrecken-Tag mit mehreren Legs ein Umlauf, ein neuer Dienst am Folgetag aber
  ein eigener.
* Der Umlauf beginnt mit dem **Briefing** und endet mit der Ankunft plus
  Debriefing. Beides gilt **nur vor und nach echten Flügen** — ein Bodendienst
  oder Simulator beginnt zur angesetzten Zeit.

Beispiel aus einem echten Dienstplan:

```
Briefing  Di 11:10
  SB_S_LR_FF  EDDF → EDDF   13:00 – 19:50   Bereitschaft
  LH510       EDDF → SAEZ   21:55 – 11:23   abgerufen
  LH511       SAEZ → EDDF   Fr 21:30 – Sa 10:32
zurück an der Basis  Sa 11:02
```

Die Bereitschaft ging in den Flug über — beides gehört zu einem Umlauf.

## Installation über HACS

1. HACS öffnen → oben rechts **⋮** → **Benutzerdefinierte Repositories**
2. URL dieses Repos eintragen, Kategorie **Integration**, hinzufügen
3. **OpenAirLog** suchen und herunterladen
4. Home Assistant **neu starten**

## Einrichtung

**Schritt 1 — Schlüssel erzeugen.** In deinem OpenAirLog-Konto unter
**Einstellungen → API** einen Schlüssel anlegen. Nötige Scopes:
`profile:read`, `flights:read`, `statistics:read`. Mehr braucht die Integration
nicht — Dokumente und Crewlisten bleiben außen vor.

**Schritt 2 — Integration hinzufügen.** Einstellungen → Geräte & Dienste →
**Integration hinzufügen** → *OpenAirLog* → Schlüssel einfügen. Er wird sofort
gegen die API geprüft.

**Schritt 3 — Konfigurieren.** Beim Eintrag auf **Konfigurieren**:

| Einstellung | Bedeutung |
|---|---|
| Briefing / Debriefing | Zählt zum Dienst, nur vor und nach echten Flügen |
| Weg zur Basis / nach Hause | Ergibt „Losfahren" und „Zurück zuhause" |
| Umlauf-Grenze | Ab welcher Standzeit an der Basis ein neuer Dienst beginnt |
| Dienstcodes | Welche Kürzel *frei*, *Bereitschaft* oder *Schulung* bedeuten |

Nicht aufgeführte Dienstcodes gelten als **Dienst** — lieber einmal umsonst
vorheizen als den Dienst verpassen.

## Beispiel-Automation

```yaml
automation:
  - alias: "Heizung vor Heimkehr"
    triggers:
      - trigger: template
        value_template: >
          {{ 0 <= (as_timestamp(states('sensor.openairlog_voraussichtlich_zuhause'))
                   - as_timestamp(now())) / 60 <= 45 }}
    actions:
      - action: climate.set_temperature
        target: { entity_id: climate.wohnzimmer }
        data: { temperature: 21 }
```

## Lizenz
MIT
