"""Holt die Daten und bereitet sie zu Diensten auf."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AuthFehler, OpenAirLogApi, OpenAirLogFehler, RateLimitFehler
from .adsbdb import AdsbdbApi
from . import flughaefen
from .dienstcodes import ist_simulator, kategorie_vorschlag
from .lufthansa import LhFehler, LufthansaApi, auswerten as lh_auswerten
from .const import (
    ICAO_ZU_IATA,
    KAT_DIENST, KAT_FREI, KAT_SCHULUNG, KAT_STANDBY,
    STANDARD_BRIEFING_MIN, STANDARD_DEBRIEFING_MIN, STANDARD_KATEGORIEN,
    STANDARD_TURNAROUND_MIN, STATISTIK_JEDER_NTE, UPDATE_INTERVALL,
    ART_BODEN,
    ART_FLUG,
    ART_SIM,
    CONF_BRIEFING_SIM_MIN,
    CONF_CODES_SIM,
    CONF_DEBRIEFING_SIM_MIN,
    CONF_PUFFER_MIN,
    STANDARD_BRIEFING_SIM_MIN,
    STANDARD_CODES_SIM,
    STANDARD_DEBRIEFING_SIM_MIN,
    STANDARD_PUFFER_MIN,
    CONF_CODES_WBT,
    KAT_WBT,
    STANDARD_CODES_WBT,
    CONF_LH_TABELLE,
    STANDARD_LH_TABELLE,
)

_LOGGER = logging.getLogger(__name__)


def _zeit(tag: str, hhmm: str | None) -> datetime | None:
    """Baut aus Datum + 'HH:MM[:SS]' einen UTC-Zeitpunkt.

    Nachgerechnet an einem Langstreckenflug (EDDF->KIAH): die Differenz aus
    off_block und on_block entspricht exakt block_minutes. Das geht nur auf,
    wenn beide Zeiten in DERSELBEN Zone stehen - die API liefert UTC.
    ISO-Zeitstempel (mit Offset oder Z) werden direkt uebernommen.
    """
    if not hhmm:
        return None
    roh = str(hhmm).strip()
    if "T" in roh or roh.endswith("Z"):
        try:
            parsed = datetime.fromisoformat(roh.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    teile = roh.split(":")
    try:
        std, minute = int(teile[0]), int(teile[1])
        d = date.fromisoformat(tag)
    except (ValueError, IndexError, TypeError):
        return None
    return datetime(d.year, d.month, d.day, std, minute, tzinfo=timezone.utc)


class OpenAirLogCoordinator(DataUpdateCoordinator):
    """Zentrales Polling; alle Entitaeten lesen aus diesem einen Datensatz."""

    def __init__(self, hass: HomeAssistant, api: OpenAirLogApi,
                 optionen: dict[str, Any],
                 lh: LufthansaApi | None = None,
                 config_entry: ConfigEntry | None = None,
                 adsbdb: AdsbdbApi | None = None) -> None:
        kwargs: dict[str, Any] = {
            "name": "OpenAirLog",
            "update_interval": UPDATE_INTERVALL,
        }
        if config_entry is not None:
            kwargs["config_entry"] = config_entry
        try:
            super().__init__(hass, _LOGGER, **kwargs)
        except TypeError:
            kwargs.pop("config_entry", None)
            super().__init__(hass, _LOGGER, **kwargs)
        self.api = api
        self.lh = lh
        self.adsbdb = adsbdb
        self.optionen = optionen
        self.profil: dict = {}
        self._statistik: dict = {}
        self._durchlauf = 0

    # ------------------------------------------------------------------ Hilfen
    def _codes(self, schluessel: str, standard: list[str] | None = None) -> set[str]:
        """Dienstcodes aus den Optionen, ohne leere Listen still zu ersetzen."""
        if schluessel in self.optionen:
            return {str(c).upper() for c in (self.optionen.get(schluessel) or [])}
        return {str(c).upper() for c in (standard or [])}

    @property
    def _lh_tabelle(self) -> bool:
        """Soll die mitgelieferte Lufthansa-Symbolliste greifen?"""
        return bool(self.optionen.get(CONF_LH_TABELLE, STANDARD_LH_TABELLE))

    def _kategorie(self, eintrag: dict) -> str:
        """Ordnet einen Eintrag einer Kategorie zu."""
        code = eintrag.get("duty_code")
        if not code:
            # Kein Dienstcode, aber Flugnummer -> echter Flug
            return KAT_DIENST if eintrag.get("flight_number") else KAT_FREI
        code_u = str(code).upper()
        if code_u in self._codes("codes_frei"):
            return KAT_FREI
        if code_u in self._codes("codes_standby"):
            return KAT_STANDBY
        if code_u in self._codes(CONF_CODES_WBT, STANDARD_CODES_WBT):
            return KAT_WBT
        if code_u in self._codes("codes_schulung"):
            return KAT_SCHULUNG
        # Eigene Listen haben Vorrang; danach greift - sofern eingeschaltet -
        # die mitgelieferte Lufthansa-Symbolliste. Was auch dort fehlt, gilt
        # als Dienst: lieber einmal zu viel heizen als den Wecker verpassen.
        if not self._lh_tabelle:
            return KAT_DIENST
        return (STANDARD_KATEGORIEN.get(code_u)
                or kategorie_vorschlag(code_u)
                or KAT_DIENST)

    def _ist_sim(self, leg: dict, eigene_codes: set[str]) -> bool:
        """Simulator? Eigene Codeliste zuerst, dann die Lufthansa-Tabelle.

        Geprueft wird der Dienstcode UND das erste Wort der Flugnummer, weil
        SIM-Schichten im Flugbuch als Fluege gefuehrt werden.
        """
        tab = self._lh_tabelle
        code = str(leg.get("code") or "").upper().strip()
        if code and (code in eigene_codes or (tab and ist_simulator(code))):
            return True
        worte = str(leg.get("flugnummer") or "").split()
        if worte:
            erstes = worte[0].upper()
            if erstes in eigene_codes or (tab and ist_simulator(erstes)):
                return True
        return False

    @staticmethod
    def _uhr(wert: Any) -> str:
        """HH:MM aus '13:40' oder ISO-Zeitstempel, fuer die Dubletten-Erkennung."""
        s = str(wert or "")
        if "T" in s:
            try:
                return s.split("T", 1)[1][:5]
            except IndexError:
                return s[:5]
        return s[:5]

    @staticmethod
    def _schluessel(e: dict) -> tuple:
        """Erkennungsmerkmal, um Roster- und Logbuch-Dubletten zu bündeln."""
        start = e.get("scheduled_off_block") or e.get("off_block") or ""
        ende = e.get("scheduled_on_block") or e.get("on_block") or ""
        return (
            e.get("date"),
            e.get("duty_code"),
            e.get("flight_number"),
            OpenAirLogCoordinator._uhr(start),
            OpenAirLogCoordinator._uhr(ende),
        )

    @staticmethod
    def _gehalt(e: dict) -> int:
        """Wie vollstaendig ist ein Eintrag? Der reichere gewinnt beim Dublettenfall."""
        return sum(1 for v in e.values() if v not in (None, "", [], 0))

    # ------------------------------------------------------------------ Abruf
    async def _async_update_data(self) -> dict[str, Any]:
        heute = dt_util.now().date()
        von = heute - timedelta(days=int(self.optionen.get("tage_rueckblick", 7)))
        bis = heute + timedelta(days=int(self.optionen.get("tage_voraus", 60)))

        try:
            roh = await self.api.fluege(von, bis)
            if not self.profil:
                self.profil = await self.api.profil()
            # Statistik aendert sich selten - nicht bei jedem Durchlauf abrufen.
            if self._durchlauf % STATISTIK_JEDER_NTE == 0 or not self._statistik:
                self._statistik = await self.api.statistik()
            self._durchlauf += 1
            statistik = self._statistik
        except AuthFehler as err:
            raise UpdateFailed(f"Zugang abgelehnt: {err}") from err
        except RateLimitFehler as err:
            _LOGGER.warning("Rate-Limit erreicht, warte %ss", err.wartezeit)
            if self.data:
                return self.data
            raise UpdateFailed(str(err)) from err
        except OpenAirLogFehler as err:
            raise UpdateFailed(str(err)) from err

        # --- Dubletten zusammenfuehren ---------------------------------
        gebuendelt: dict[tuple, dict] = {}
        for e in roh:
            k = self._schluessel(e)
            if k not in gebuendelt or self._gehalt(e) > self._gehalt(gebuendelt[k]):
                gebuendelt[k] = e

        # --- zu Diensten aufbereiten ------------------------------------
        dienste: list[dict] = []
        for e in gebuendelt.values():
            tag = e.get("date") or ""
            beginn = _zeit(tag, e.get("scheduled_off_block") or e.get("off_block"))
            ende = _zeit(tag, e.get("scheduled_on_block") or e.get("on_block"))
            if beginn and ende and ende <= beginn:
                ende += timedelta(days=1)          # ueber Mitternacht
            dienste.append({
                "id": e.get("id"),
                "datum": e.get("date"),
                "kategorie": self._kategorie(e),
                "code": e.get("duty_code"),
                "flugnummer": e.get("flight_number"),
                "von": e.get("departure"),
                "nach": e.get("arrival"),
                "muster": e.get("aircraft_type"),
                "kennzeichen": e.get("aircraft_registration"),
                "beginn": beginn,
                "ende": ende,
                "block_minuten": e.get("block_minutes"),
                "bemerkung": e.get("remarks"),
            })
        dienste.sort(key=lambda d: (d["beginn"] or datetime.max.replace(tzinfo=timezone.utc),
                                    d["datum"]))

        umlaeufe = self._umlaeufe(dienste)

        jetzt = datetime.now(timezone.utc)
        aktuell = next((u for u in umlaeufe
                        if u["beginn"] <= jetzt <= u["ende"]), None)
        naechster = next((u for u in umlaeufe if u["beginn"] > jetzt), None)

        # Klarnamen der Flughaefen - nur fuer den laufenden und den naechsten
        # Umlauf, nicht fuer alle 60 Tage. Ergebnisse sind gespeichert.
        for u in (aktuell, naechster):
            await self._orte_anreichern(u)

        live = await self._lh_anreichern(aktuell, naechster, jetzt)

        return {
            "dienste": dienste,
            "live": live,
            "umlaeufe": umlaeufe,
            "aktuell": aktuell,
            "naechster": naechster,
            "statistik": statistik,
            "profil": self.profil,
        }

    # -------------------------------------------------------- Lufthansa
    async def _orte_anreichern(self, umlauf: dict | None) -> None:
        """Ergaenzt Klartext-Ort und Zeitzone zum Ziel eines Umlaufs.

        Das Ziel eines Umlaufs ist NICHT der letzte Halt (das ist die Basis),
        sondern der Flughafen mit der laengsten Standzeit dazwischen - also der
        Layover. Bei einem Hin- und Rueckflug nach Tokio ist das Tokio.

        Zwei Quellen:
          * lokal (airportsdata): Zeitzone und Rueckfall-Ort - aus der Station
            im Dienstplan, ohne Netz und ohne Flugnummer
          * adsbdb: der schoenere Ortsname ("Vancouver" statt "Richmond") und
            das ICAO-Rufzeichen - braucht eine Flugnummer, die adsbdb kennt
        """
        if not umlauf:
            return
        legs = umlauf.get("legs") or []
        fluege = [l for l in legs if l.get("flugnummer")]
        if not fluege:
            return

        # Layover suchen: groesste Luecke zwischen zwei Fluegen
        ziel_leg, groesste = fluege[0], None
        for a, b in zip(fluege, fluege[1:]):
            if a.get("ende") and b.get("beginn"):
                pause = b["beginn"] - a["ende"]
                if groesste is None or pause > groesste:
                    groesste, ziel_leg = pause, a

        if not flughaefen.geladen():
            await self.hass.async_add_executor_job(flughaefen.laden)
        lokal = flughaefen.nachschlagen(ziel_leg.get("nach"))
        if lokal:
            umlauf["ziel_ort"] = lokal["ort"]
            umlauf["ziel_flughafen"] = lokal["name"]
            umlauf["ziel_land"] = lokal["land_iso"]
            umlauf["ziel_iata"] = lokal["iata"]
            umlauf["ziel_land_iso"] = lokal["land_iso"]
            umlauf["ziel_zeitzone"] = lokal["zeitzone"]

        await self._adsbdb_anreichern(umlauf, ziel_leg)
        # Zuletzt: deutscher Ortsname, wenn bekannt - gilt fuer beide Quellen
        if umlauf.get("ziel_iata"):
            umlauf["ziel_ort"] = flughaefen.ort_deutsch(umlauf["ziel_iata"], umlauf.get("ziel_ort"))

    async def _adsbdb_anreichern(self, umlauf: dict, ziel_leg: dict) -> None:
        """Rufzeichen und Ortsname von adsbdb - nur, wenn die Strecke passt.

        Auf der Kurzstrecke fliegt Lufthansa meist mit alphanumerischen
        Rufzeichen (DLH7JF); die Flugnummer aus dem Dienstplan ist dort oft
        unbekannt. Das ist kein Fehler: Ort und Zeitzone stehen dann schon
        aus der lokalen Tabelle fest.
        """
        if not self.adsbdb:
            return
        strecke = await self.adsbdb.strecke(str(ziel_leg.get("flugnummer") or "").split()[0])
        if not strecke:
            return
        nach = strecke.get("nach") or {}
        # Passt die adsbdb-Strecke nicht zur Station im Dienstplan (Umleitung,
        # geaenderte Flugnummer), gewinnt der Dienstplan.
        station = str(ziel_leg.get("nach") or "").upper()
        if station and station not in {str(nach.get("iata") or "").upper(),
                                       str(nach.get("icao") or "").upper()}:
            return
        umlauf["ziel_ort"] = nach.get("ort") or umlauf.get("ziel_ort")
        umlauf["ziel_flughafen"] = nach.get("name") or umlauf.get("ziel_flughafen")
        umlauf["ziel_land"] = nach.get("land") or umlauf.get("ziel_land")
        umlauf["rufzeichen"] = strecke.get("rufzeichen_icao")

    async def _lh_anreichern(self, aktuell, naechster, jetzt):
        """Holt den Live-Status des relevanten Fluges bei der Lufthansa.

        Sparsam: nur ein Abruf fuer genau den Flug, der laeuft oder als
        naechstes ansteht - und nur innerhalb des Zeitfensters. An
        Bodendiensttagen passiert nichts, weil dort keine Flugnummer steht.
        """
        if not self.lh:
            return None
        fenster = timedelta(hours=int(self.optionen.get("lh_fenster_stunden", 24)))

        kandidat = None
        for u in ([aktuell] if aktuell else []) + ([naechster] if naechster else []):
            for leg in u.get("legs", []):
                if not leg.get("flugnummer") or not leg.get("beginn"):
                    continue
                if -timedelta(hours=12) <= (leg["beginn"] - jetzt) <= fenster:
                    kandidat = leg
                    break
            if kandidat:
                break
        if not kandidat:
            return None

        nummer = str(kandidat["flugnummer"]).replace(" ", "")
        tag = kandidat["beginn"].strftime("%Y-%m-%d")
        try:
            antwort = await self.lh.flugstatus(nummer, tag)
        except LhFehler as err:
            _LOGGER.warning("Lufthansa-Status nicht abrufbar: %s", err)
            return None
        if not antwort:
            return {"status": "kein Eintrag", "flugnummer": nummer}

        ergebnis = lh_auswerten(antwort, kandidat["beginn"]) or {}
        ergebnis["flugnummer"] = nummer
        ergebnis["geplant_dienst"] = kandidat["beginn"]
        return ergebnis

    @staticmethod
    def _basis_codes(eingabe: str) -> set[str]:
        """Alle Schreibweisen der Basis: "EDDF" -> {"EDDF", "FRA"}.

        Die Option darf mehrere Codes enthalten ("FRA, EDDF"); jeder bekommt
        sein Gegenstueck aus der Tabelle dazu.
        """
        codes = {c.strip().upper() for c in str(eingabe).replace(";", ",").split(",")
                 if c.strip()}
        iata_zu_icao = {v: k for k, v in ICAO_ZU_IATA.items()}
        for c in list(codes):
            if c in ICAO_ZU_IATA:
                codes.add(ICAO_ZU_IATA[c])
            if c in iata_zu_icao:
                codes.add(iata_zu_icao[c])
        return codes

    # ------------------------------------------------------- Umlaufbildung
    def _umlaeufe(self, dienste: list[dict]) -> list[dict]:
        """Fasst zusammenhaengende Dienste zu Umlaeufen zusammen.

        Ein Umlauf ist die Zeit, in der man NICHT zuhause ist - vom Briefing
        bis zurueck an der Basis. Das ist der Zeitraum, der fuer Heizung,
        Kaffee und Benachrichtigungen zaehlt.

        Regel:
          * Ist man nicht an der Basis, laeuft der Umlauf weiter (Layover).
          * Ist man an der Basis, gehoert der naechste Flug nur dazu, wenn die
            Standzeit unter der Turnaround-Grenze liegt (Kurzstrecken-Umlauf).
        """
        o = self.optionen
        briefing = timedelta(minutes=int(o.get("briefing_minuten", STANDARD_BRIEFING_MIN)))
        debriefing = timedelta(minutes=int(o.get("debriefing_minuten", STANDARD_DEBRIEFING_MIN)))
        briefing_sim = timedelta(
            minutes=int(o.get(CONF_BRIEFING_SIM_MIN, STANDARD_BRIEFING_SIM_MIN)))
        debriefing_sim = timedelta(
            minutes=int(o.get(CONF_DEBRIEFING_SIM_MIN, STANDARD_DEBRIEFING_SIM_MIN)))
        puffer = timedelta(minutes=int(o.get(CONF_PUFFER_MIN, STANDARD_PUFFER_MIN)))
        codes_sim = self._codes(CONF_CODES_SIM, STANDARD_CODES_SIM)
        turnaround = timedelta(minutes=int(o.get("turnaround_minuten", STANDARD_TURNAROUND_MIN)))
        basis = self._basis_codes(o.get("basis_flughafen")
                                  or (self.profil or {}).get("base_airport") or "")

        # Praesenzschulungen zaehlen mit - auch dafuer muss man losfahren.
        # Web Based Training bleibt draussen: das laeuft am Rechner zuhause.
        arbeit = [d for d in dienste
                  if d["kategorie"] in (KAT_DIENST, KAT_STANDBY, KAT_SCHULUNG)
                  and d["beginn"] and d["ende"]]
        arbeit.sort(key=lambda d: d["beginn"])

        umlaeufe: list[dict] = []
        aktuell: dict | None = None

        for d in arbeit:
            if aktuell is None:
                aktuell = {"legs": [d]}
            else:
                letzter = aktuell["legs"][-1]
                an_basis = ((letzter.get("nach") or "").upper().strip() in basis
                            if basis else True)
                pause = d["beginn"] - letzter["ende"]
                if (not an_basis) or pause <= turnaround:
                    aktuell["legs"].append(d)          # gehoert noch dazu
                else:
                    umlaeufe.append(aktuell)
                    aktuell = {"legs": [d]}
        if aktuell:
            umlaeufe.append(aktuell)

        fertig = []
        for u in umlaeufe:
            legs = u["legs"]
            erster, letzter = legs[0], legs[-1]
            # Wie frueh man da sein muss, haengt von der Art des Dienstes ab:
            #   Flug       -> Briefing vor Abflug, kurzes Debriefing danach
            #   Simulator  -> laengere Vor- UND Nachbereitung
            #   Boden      -> Groundcourse, CRM, eCRM: kein Briefing
            # Simulator ZUERST pruefen: SIM-Schichten stehen im Flugbuch als
            # Fluege - mit Flugnummer, Abflug = Ankunft und einer Simulator-
            # Kennung statt eines Flugzeugs (z.B. "TTC B748 748", EDDF->EDDF).
            # Ohne diese Reihenfolge bekaeme eine SIM-Schicht die Briefingzeit
            # eines Fluges.
            if self._ist_sim(erster, codes_sim):
                art = ART_SIM
                vorlauf = briefing_sim
                nachlauf = debriefing_sim
            elif erster.get("flugnummer"):
                art = ART_FLUG
                vorlauf = briefing
                nachlauf = debriefing if letzter.get("flugnummer") else timedelta(0)
            else:
                art = ART_BODEN
                vorlauf = timedelta(0)
                nachlauf = timedelta(0)

            beginn = erster["beginn"] - vorlauf
            fertig.append({
                "art": art,
                "beginn": beginn,
                # Der Puffer zaehlt NICHT zum Dienst - er sagt nur, wann man
                # vor Ort sein moechte, und verschiebt damit die Losfahrzeit.
                "vor_ort": beginn - puffer,
                "puffer_minuten": int(puffer.total_seconds() // 60),
                "briefing_minuten": int(vorlauf.total_seconds() // 60),
                "ende": letzter["ende"] + nachlauf,
                "abflug": erster["beginn"],
                "ankunft": letzter["ende"],
                "von": erster.get("von"),
                "nach": letzter.get("nach"),
                "legs": legs,
                "anzahl_legs": len(legs),
                "mehrtaegig": erster["beginn"].date() != letzter["ende"].date(),
                "kategorie": erster["kategorie"],
                "code": erster.get("code"),
                "flugnummern": [l.get("flugnummer") for l in legs if l.get("flugnummer")],
                "stationen": [erster.get("von")] + [l.get("nach") for l in legs],
                "datum": erster["datum"],
            })
        return fertig
