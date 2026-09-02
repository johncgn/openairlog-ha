# OpenAirLog für Home Assistant

Bringt deinen Dienstplan und dein Flugbuch von [OpenAirLog](https://openairlog.de)
nach Home Assistant — als Kalender, Sensoren und eigene Dashboard-Karte. Damit
lassen sich Heizung, Kaffeemaschine oder Benachrichtigungen an deine Dienste
koppeln, ohne den Plan abzutippen.

Die Integration ist **rein lesend** und schreibt nichts in dein Flugbuch zurück.

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

## Lufthansa Live-Status (vorbereitet, derzeit inaktiv)

Für Lufthansa-Crews ist eine Anbindung an die
[Lufthansa Open API](https://developer.lufthansa.com) fertig eingebaut: Sie
liefert `sensor.flugstatus` (*pünktlich · verspätet · gestrichen · gelandet*)
und `sensor.verspaetung`, dazu Gate und Terminal. Anders als reine
Tracking-Dienste liefert sie **geplante und tatsächliche Zeiten** — die
Verspätung ist damit echte Airline-Information.

> **Stand September 2026:** Lufthansa hat die Registrierung für neue Entwickler
> ausgesetzt („Registration to OpenAPI is on hold until further notice").
> Deshalb ist der Einrichtungsschritt aus den Optionen **ausgeblendet** — er
> ließe sich mit einer Zeile in `config_flow.py` wieder einhängen, sobald es
> wieder Zugänge gibt. Wer bereits Zugangsdaten hinterlegt hat, behält sie und
> bekommt die Live-Sensoren weiterhin.

## Serverlast

Die Integration geht bewusst sparsam mit OpenAirLog um — das Projekt ist Freeware:

| Abruf | Häufigkeit | Pro Tag |
|---|---|---|
| `/flights` (Dienste) | alle 30 Minuten | 48 |
| `/statistics` | alle 2 Stunden | 12 |
| `/profile` | einmal je Neustart | ~1 |

Rund **60 Anfragen pro Tag und Nutzer** — weit unter dem Limit von 120 pro Minute.

## Hinweise

* **Zeitzone:** Die API liefert Zeiten in UTC; Home Assistant rechnet sie in deine
  lokale Zeit um.
* **Doppelte Einträge:** Ein Dienst erscheint teils zweimal — einmal aus dem
  Dienstplan, einmal aus dem Flugbuch. Die Integration führt beide zusammen und
  behält den vollständigeren Eintrag.

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
