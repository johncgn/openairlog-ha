"""Nachschlagen von Flugstrecken bei adsbdb.com.

Liefert zu einer Flugnummer die Flughaefen im Klartext - aus "RJTT" wird
"Tokyo Haneda International Airport". Ausserdem das ICAO-Rufzeichen (LH716
fliegt als DLH716), das fuer eine spaetere Live-Verfolgung gebraucht wird.

**Keine Live-Daten.** adsbdb ist eine Nachschlagedatenbank: Strecke, Airline,
Flughafendaten. Keine Position, keine Zeiten, keine Verspaetung.

Der Dienst ist frei und wird privat betrieben, deshalb gehen wir sparsam damit
um: Strecken aendern sich praktisch nie, also wird jede Flugnummer nur EINMAL
je Neustart abgefragt und danach aus dem Speicher bedient. Auch Fehlschlaege
werden gemerkt, damit eine unbekannte Nummer nicht bei jedem Durchlauf erneut
anklopft.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

BASIS_URL = "https://api.adsbdb.com/v0"
ZEITLIMIT = aiohttp.ClientTimeout(total=15)


class AdsbdbApi:
    """Duenner Client mit Gedaechtnis."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._speicher: dict[str, dict[str, Any] | None] = {}
        self._sperre = asyncio.Lock()

    async def strecke(self, flugnummer: str) -> dict[str, Any] | None:
        """Strecke zu einer Flugnummer - None, wenn unbekannt.

        Nimmt IATA (LH716) oder ICAO (DLH716); adsbdb versteht beides.
        """
        if not flugnummer:
            return None
        schluessel = str(flugnummer).replace(" ", "").upper()
        if schluessel in self._speicher:          # auch None wird gemerkt
            return self._speicher[schluessel]

        async with self._sperre:
            if schluessel in self._speicher:      # waehrend des Wartens gefuellt
                return self._speicher[schluessel]
            ergebnis = await self._holen(schluessel)
            self._speicher[schluessel] = ergebnis
            return ergebnis

    async def _holen(self, rufzeichen: str) -> dict[str, Any] | None:
        url = f"{BASIS_URL}/callsign/{rufzeichen}"
        kopf = {"User-Agent": "openairlog-ha (Home-Assistant-Integration)"}
        try:
            async with self._session.get(url, headers=kopf, timeout=ZEITLIMIT) as antwort:
                if antwort.status == 404:
                    return None                   # Nummer nicht in der Datenbank
                if antwort.status == 429:
                    _LOGGER.debug("adsbdb: Anfragegrenze erreicht")
                    return None
                if antwort.status != 200:
                    _LOGGER.debug("adsbdb: HTTP %s fuer %s", antwort.status, rufzeichen)
                    return None
                daten = await antwort.json()
        except Exception as err:  # noqa: BLE001 - darf den Abruf nie kippen
            _LOGGER.debug("adsbdb nicht erreichbar: %s", err)
            return None

        route = (daten.get("response") or {}).get("flightroute")
        if not route:
            return None
        return {
            "rufzeichen_icao": route.get("callsign_icao"),
            "rufzeichen_iata": route.get("callsign_iata"),
            "airline": (route.get("airline") or {}).get("name"),
            "von": _flughafen(route.get("origin")),
            "nach": _flughafen(route.get("destination")),
        }


def _flughafen(roh: dict[str, Any] | None) -> dict[str, Any] | None:
    """Nur die Felder, die wir wirklich anzeigen."""
    if not roh:
        return None
    return {
        "icao": roh.get("icao_code"),
        "iata": roh.get("iata_code"),
        "ort": roh.get("municipality"),
        "name": roh.get("name"),
        "land": roh.get("country_name"),
        "breite": roh.get("latitude"),
        "laenge": roh.get("longitude"),
    }
