"""Layover eines Umlaufs finden und das Wetter fuer die Tage des Aufenthalts."""
import asyncio
from datetime import date, timedelta

import pytest

from conftest import leg
from openairlog import flughaefen
from openairlog.wetter import beschreibung, tage_auswerten

pytest.importorskip("airportsdata")

BASIS = {"base_airport": "EDDF"}


class WetterAttrappe:
    """Liefert 16 Tage ab `start` - wie Open-Meteo, Datum in Ortszeit."""

    def __init__(self, start: date, tage: int = 16):
        self.start, self.n = start, tage
        self.gefragt = []

    async def tage(self, breite, laenge):
        self.gefragt.append((round(breite, 1), round(laenge, 1)))
        return [{"datum": (self.start + timedelta(days=i)).isoformat(), "code": 61, "text": "Leichter Regen",
                 "symbol": "weather-rainy", "max": 12 + i, "min": 5, "regen_mm": 1.2, "regen_chance": 60}
                for i in range(self.n)]


def anreichern(k, umlauf):
    asyncio.run(k._orte_anreichern(umlauf))
    return umlauf


def test_mehrere_layover_in_reihenfolge(coordinator):
    # FRA-VIE Nightstop, VIE-MUC Nightstop, MUC-FRA
    u = {"legs": [
        leg(None, "LH1234", "FRA", "VIE", "2026-11-20T17:00", "2026-11-20T18:20"),
        leg(None, "LH1235", "VIE", "MUC", "2026-11-21T06:00", "2026-11-21T07:00"),
        leg(None, "LH2000", "MUC", "FRA", "2026-11-21T19:00", "2026-11-21T20:00"),
    ]}
    u = anreichern(coordinator(profil=BASIS), u)
    assert [l["iata"] for l in u["layover"]] == ["VIE", "MUC"]
    assert u["layover"][0]["ort"] == "Wien" and u["layover"][1]["ort"] == "München"
    assert u["layover"][0]["zeitzone"] == "Europe/Vienna"
    assert u["layover"][0]["stunden"] == pytest.approx(11.7, abs=0.1)


def test_wende_ist_kein_layover(coordinator):
    # FRA-HAM, 1 h Wende, HAM-FRA: kein Layover
    u = {"legs": [
        leg(None, "LH10", "FRA", "HAM", "2026-11-20T06:00", "2026-11-20T07:00"),
        leg(None, "LH11", "HAM", "FRA", "2026-11-20T08:00", "2026-11-20T09:00"),
    ]}
    assert anreichern(coordinator(profil=BASIS), u)["layover"] == []


def test_wetter_nur_fuer_die_tage_des_aufenthalts(coordinator):
    # Ankunft Vancouver 10.11. abends (Ortszeit), Abflug 12.11. abends -> 3 Tage
    wetter = WetterAttrappe(date(2026, 11, 8))
    u = {"legs": [
        leg(None, "LH492", "FRA", "YVR", "2026-11-10T09:40", "2026-11-10T19:45"),
        leg(None, "LH493", "YVR", "FRA", "2026-11-13T05:25", "2026-11-13T15:10"),
    ]}
    u = anreichern(coordinator(profil=BASIS, wetter=wetter), u)
    lo = u["layover"][0]
    assert lo["iata"] == "YVR"
    # 19:45 UTC = 11:45 Ortszeit am 10.11., 05:25 UTC am 13.11. = 21:25 am 12.11. Ortszeit
    assert [t["datum"] for t in lo["wetter"]] == ["2026-11-10", "2026-11-11", "2026-11-12"]
    assert lo["wetter"][0]["symbol"] == "weather-rainy"
    assert wetter.gefragt == [(49.2, -123.2)]


def test_zu_weit_in_der_zukunft_gibt_hinweis(coordinator):
    # Vorhersage reicht bis 16.11., Layover erst ab 30.11.
    wetter = WetterAttrappe(date(2026, 11, 1))
    u = {"legs": [
        leg(None, "LH576", "FRA", "CPT", "2026-11-30T21:15", "2026-12-01T08:35"),
        leg(None, "LH577", "CPT", "FRA", "2026-12-03T17:10", "2026-12-04T04:35"),
    ]}
    lo = anreichern(coordinator(profil=BASIS, wetter=wetter), u)["layover"][0]
    assert lo["wetter"] == []
    assert lo["wetter_ab"] == "2026-11-16"   # 1.12. minus 15 Tage


def test_wetter_abschaltbar(coordinator):
    wetter = WetterAttrappe(date(2026, 11, 8))
    u = {"legs": [
        leg(None, "LH492", "FRA", "YVR", "2026-11-10T09:40", "2026-11-10T19:45"),
        leg(None, "LH493", "YVR", "FRA", "2026-11-13T05:25", "2026-11-13T15:10"),
    ]}
    lo = anreichern(coordinator(profil=BASIS, wetter=wetter, optionen={"wetter_layover": False}), u)["layover"][0]
    assert "wetter" not in lo and wetter.gefragt == []


def test_open_meteo_antwort_auswerten():
    roh = {"daily": {"time": ["2026-11-10", "2026-11-11"], "weather_code": [0, 95],
                     "temperature_2m_max": [14.6, 9.2], "temperature_2m_min": [4.4, 3.0],
                     "precipitation_sum": [0.0, 12.34], "precipitation_probability_max": [5, 90]}}
    t = tage_auswerten(roh)
    assert t[0]["symbol"] == "weather-sunny" and t[0]["max"] == 15 and t[0]["min"] == 4
    assert t[1]["text"] == "Gewitter" and t[1]["regen_mm"] == 12.3
    assert beschreibung(None) == ("–", "weather-cloudy")


def test_koordinaten_aus_flughafentabelle():
    flughaefen.laden()
    yvr = flughaefen.nachschlagen("YVR")
    assert round(yvr["breite"], 1) == 49.2 and round(yvr["laenge"], 1) == -123.2
