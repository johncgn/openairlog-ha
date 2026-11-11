"""Zielort und Ortszeit eines Umlaufs: Layover finden, Quellen zusammenfuehren."""
import asyncio

import pytest

from conftest import leg
from openairlog import flughaefen

pytest.importorskip("airportsdata")


class AdsbdbAttrappe:
    def __init__(self, antworten):
        self.antworten = antworten
        self.gefragt = []

    async def strecke(self, flugnummer):
        self.gefragt.append(flugnummer)
        return self.antworten.get(flugnummer)


VANCOUVER = {
    "rufzeichen_icao": "DLH492",
    "nach": {"iata": "YVR", "icao": "CYVR", "ort": "Vancouver",
             "name": "Vancouver International Airport", "land": "Canada"},
}


def umlauf_vancouver():
    return {"legs": [
        leg(None, "LH492", "FRA", "YVR", "2026-11-10T09:40", "2026-11-10T19:45"),
        leg(None, "LH493", "YVR", "FRA", "2026-11-12T21:25", "2026-11-13T07:10"),
    ]}


def anreichern(k, umlauf):
    asyncio.run(k._orte_anreichern(umlauf))
    return umlauf


def test_flughafen_nachschlagen():
    flughaefen.laden()
    assert flughaefen.nachschlagen("FRA")["zeitzone"] == "Europe/Berlin"
    assert flughaefen.nachschlagen("eddf")["iata"] == "FRA"
    assert flughaefen.nachschlagen("HYD")["zeitzone"] == "Asia/Kolkata"
    assert flughaefen.nachschlagen("XYZQ") is None
    assert flughaefen.nachschlagen(None) is None


def test_layover_ist_ziel_nicht_der_letzte_halt(coordinator):
    u = anreichern(coordinator(adsbdb=AdsbdbAttrappe({"LH492": VANCOUVER})), umlauf_vancouver())
    assert u["ziel_ort"] == "Vancouver"
    assert u["ziel_iata"] == "YVR"
    assert u["ziel_zeitzone"] == "America/Vancouver"
    assert u["ziel_land_iso"] == "CA"
    assert u["rufzeichen"] == "DLH492"


def test_ohne_adsbdb_trotzdem_ort_und_zeitzone(coordinator):
    # Alphanumerisches Rufzeichen o. ae.: adsbdb kennt den Flug nicht
    u = anreichern(coordinator(adsbdb=AdsbdbAttrappe({})), umlauf_vancouver())
    assert u["ziel_zeitzone"] == "America/Vancouver"
    assert u["ziel_ort"]                    # lokaler Ortsname (Richmond)
    assert "rufzeichen" not in u


def test_adsbdb_widerspricht_dem_dienstplan(coordinator):
    # adsbdb meldet ein anderes Ziel (z. B. geaenderte Flugnummer) - der Plan gewinnt
    falsch = {"rufzeichen_icao": "DLH492",
              "nach": {"iata": "SEA", "icao": "KSEA", "ort": "Seattle", "land": "United States"}}
    u = anreichern(coordinator(adsbdb=AdsbdbAttrappe({"LH492": falsch})), umlauf_vancouver())
    assert u["ziel_iata"] == "YVR" and u["ziel_ort"] != "Seattle"


def test_ohne_flugnummern_kein_ziel(coordinator):
    sim = {"legs": [leg("SIM", None, "FRA", "FRA", "2026-11-08T22:00", "2026-11-09T02:00")]}
    u = anreichern(coordinator(adsbdb=AdsbdbAttrappe({})), sim)
    assert "ziel_ort" not in u


def test_kurzstrecke_mit_mehreren_halten_nimmt_laengste_pause(coordinator):
    # FRA-MUC (1 h Pause) - MUC-FRA ... Ziel ist der Ort mit der laengsten Standzeit
    u = {"legs": [
        leg(None, "LH100", "FRA", "HAM", "2026-11-20T06:00", "2026-11-20T07:00"),
        leg(None, "LH101", "HAM", "FRA", "2026-11-20T08:00", "2026-11-20T09:00"),
        leg(None, "LH102", "FRA", "VIE", "2026-11-20T09:45", "2026-11-20T11:00"),
        leg(None, "LH103", "VIE", "FRA", "2026-11-20T16:00", "2026-11-20T17:30"),
    ]}
    u = anreichern(coordinator(adsbdb=None), u)
    assert u["ziel_iata"] == "VIE" and u["ziel_zeitzone"] == "Europe/Vienna"


def test_kurzstrecke_mit_alphanumerischem_rufzeichen(coordinator):
    # Kurzstrecken-Nightstop FRA-VIE / VIE-FRA: adsbdb kennt die Flugnummern
    # nicht (in der Luft heisst der Flug DLH7JF). Ort und Zeitzone kommen
    # trotzdem - aus der Station im Dienstplan.
    adsbdb = AdsbdbAttrappe({})
    u = {"legs": [
        leg(None, "LH1234", "FRA", "VIE", "2026-11-20T17:00", "2026-11-20T18:20"),
        leg(None, "LH1235", "VIE", "FRA", "2026-11-21T06:00", "2026-11-21T07:25"),
    ]}
    u = anreichern(coordinator(adsbdb=adsbdb), u)
    assert adsbdb.gefragt == ["LH1234"]          # einmal gefragt, keine Antwort
    assert u["ziel_ort"] == "Wien"
    assert u["ziel_land_iso"] == "AT"
    assert u["ziel_zeitzone"] == "Europe/Vienna"
    assert "rufzeichen" not in u


@pytest.mark.parametrize("iata, ort", [
    ("MUC", "München"), ("FLR", "Florenz"), ("MLA", "Malta"), ("LCA", "Larnaka"),
    ("BSL", "Basel"), ("YVR", "Vancouver"), ("HND", "Tokio"),
])
def test_deutsche_ortsnamen(coordinator, iata, ort):
    u = {"legs": [leg(None, "LH1", "FRA", iata, "2026-11-20T08:00", "2026-11-20T10:00"),
                  leg(None, "LH2", iata, "FRA", "2026-11-21T08:00", "2026-11-21T10:00")]}
    assert anreichern(coordinator(adsbdb=None), u)["ziel_ort"] == ort


def test_adsbdb_name_wird_eingedeutscht(coordinator):
    u = anreichern(coordinator(adsbdb=AdsbdbAttrappe({"LH492": VANCOUVER})), umlauf_vancouver())
    assert u["ziel_ort"] == "Vancouver" and u["rufzeichen"] == "DLH492"


def test_unbekannter_ort_bleibt_wie_geliefert(coordinator):
    u = {"legs": [leg(None, "LH1", "FRA", "TRF", "2026-11-20T08:00", "2026-11-20T10:00"),
                  leg(None, "LH2", "TRF", "FRA", "2026-11-21T08:00", "2026-11-21T10:00")]}
    assert anreichern(coordinator(adsbdb=None), u)["ziel_ort"]   # Sandefjord o. ae., nicht leer
