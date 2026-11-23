"""Wettervorhersage für die Layover-Orte über Open-Meteo.

Open-Meteo (open-meteo.com) ist frei, braucht kein Konto und keinen Schlüssel
und liefert eine Tagesvorhersage bis 16 Tage voraus - weltweit, also auch für
Hyderabad oder Kapstadt. Die Daten stehen unter CC BY 4.0 ("Weather data by
Open-Meteo.com"), die Nutzung ist für nicht-kommerzielle Zwecke frei.

Sparsam: Eine Vorhersage je Ort wird drei Stunden lang aus dem Speicher
bedient, ein Fehlschlag 30 Minuten lang. Ein Fehler kippt nie den Abruf des
Dienstplans - dann gibt es eben kein Wetter.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

URL = "https://api.open-meteo.com/v1/forecast"
ZEITLIMIT = aiohttp.ClientTimeout(total=15)
GUELTIG_S = 3 * 3600
FEHLER_GUELTIG_S = 30 * 60
VORHERSAGE_TAGE = 16

# WMO-Wettercodes -> (deutscher Text, mdi-Symbol)
WMO: dict[int, tuple[str, str]] = {
    0: ("Klar", "weather-sunny"),
    1: ("Überwiegend klar", "weather-partly-cloudy"),
    2: ("Teils bewölkt", "weather-partly-cloudy"),
    3: ("Bedeckt", "weather-cloudy"),
    45: ("Nebel", "weather-fog"), 48: ("Reifnebel", "weather-fog"),
    51: ("Leichter Niesel", "weather-rainy"), 53: ("Niesel", "weather-rainy"),
    55: ("Starker Niesel", "weather-rainy"),
    56: ("Gefrierender Niesel", "weather-snowy-rainy"), 57: ("Gefrierender Niesel", "weather-snowy-rainy"),
    61: ("Leichter Regen", "weather-rainy"), 63: ("Regen", "weather-rainy"),
    65: ("Starker Regen", "weather-pouring"),
    66: ("Gefrierender Regen", "weather-snowy-rainy"), 67: ("Gefrierender Regen", "weather-snowy-rainy"),
    71: ("Leichter Schnee", "weather-snowy"), 73: ("Schnee", "weather-snowy"),
    75: ("Starker Schnee", "weather-snowy-heavy"), 77: ("Schneegriesel", "weather-snowy"),
    80: ("Regenschauer", "weather-rainy"), 81: ("Regenschauer", "weather-pouring"),
    82: ("Heftige Schauer", "weather-pouring"),
    85: ("Schneeschauer", "weather-snowy"), 86: ("Schneeschauer", "weather-snowy-heavy"),
    95: ("Gewitter", "weather-lightning-rainy"),
    96: ("Gewitter mit Hagel", "weather-hail"), 99: ("Gewitter mit Hagel", "weather-hail"),
}


def beschreibung(code: Any) -> tuple[str, str]:
    try:
        return WMO.get(int(code), ("–", "weather-cloudy"))
    except (TypeError, ValueError):
        return ("–", "weather-cloudy")


def tage_auswerten(daten: dict[str, Any]) -> list[dict[str, Any]]:
    """Open-Meteo-Antwort -> Liste je Tag (Datum in Ortszeit des Ortes)."""
    d = (daten or {}).get("daily") or {}
    zeiten = d.get("time") or []

    def wert(feld: str, i: int):
        reihe = d.get(feld) or []
        return reihe[i] if i < len(reihe) else None

    out = []
    for i, datum in enumerate(zeiten):
        code = wert("weather_code", i)
        text, symbol = beschreibung(code)
        tmax, tmin = wert("temperature_2m_max", i), wert("temperature_2m_min", i)
        regen, chance = wert("precipitation_sum", i), wert("precipitation_probability_max", i)
        out.append({
            "datum": datum,
            "code": code,
            "text": text,
            "symbol": symbol,
            "max": None if tmax is None else round(tmax),
            "min": None if tmin is None else round(tmin),
            "regen_mm": None if regen is None else round(regen, 1),
            "regen_chance": chance,
        })
    return out


class WetterApi:
    """Dünner Open-Meteo-Client mit Gedächtnis je Ort."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._speicher: dict[tuple, tuple[float, list | None]] = {}
        self._sperre = asyncio.Lock()

    async def tage(self, breite: float, laenge: float) -> list[dict[str, Any]] | None:
        """Tagesvorhersage (bis 16 Tage) für einen Ort - None bei Fehler."""
        if breite is None or laenge is None:
            return None
        schluessel = (round(float(breite), 2), round(float(laenge), 2))
        async with self._sperre:
            treffer = self._speicher.get(schluessel)
            if treffer and time.monotonic() < treffer[0]:
                return treffer[1]
            ergebnis = await self._holen(*schluessel)
            dauer = GUELTIG_S if ergebnis is not None else FEHLER_GUELTIG_S
            self._speicher[schluessel] = (time.monotonic() + dauer, ergebnis)
            return ergebnis

    async def _holen(self, breite: float, laenge: float) -> list[dict[str, Any]] | None:
        params = {
            "latitude": breite, "longitude": laenge, "timezone": "auto",
            "forecast_days": VORHERSAGE_TAGE,
            "daily": ",".join(("weather_code", "temperature_2m_max", "temperature_2m_min",
                               "precipitation_sum", "precipitation_probability_max")),
        }
        kopf = {"User-Agent": "openairlog-ha (Home-Assistant-Integration)"}
        try:
            async with self._session.get(URL, params=params, headers=kopf, timeout=ZEITLIMIT) as antwort:
                if antwort.status != 200:
                    _LOGGER.debug("Open-Meteo: HTTP %s", antwort.status)
                    return None
                return tage_auswerten(await antwort.json())
        except Exception as err:  # noqa: BLE001 - darf den Abruf nie kippen
            _LOGGER.debug("Open-Meteo nicht erreichbar: %s", err)
            return None
