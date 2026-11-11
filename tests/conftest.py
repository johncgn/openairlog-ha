"""Testumgebung ohne installiertes Home Assistant.

Die Tests pruefen die Fachlogik (Umlaufbildung, Dienstcodes, Zielort), nicht
das Zusammenspiel mit HA. Deshalb werden die wenigen HA-Bausteine, die der
Coordinator importiert, durch Attrappen ersetzt, und das Paket wird OHNE
seine __init__.py geladen (die zieht Frontend und HTTP von HA nach).
"""
from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

PAKET = Path(__file__).resolve().parents[1] / "custom_components" / "openairlog"


def _attrappen() -> None:
    for name in ("homeassistant", "homeassistant.config_entries", "homeassistant.core",
                 "homeassistant.helpers", "homeassistant.helpers.update_coordinator",
                 "homeassistant.util", "homeassistant.helpers.aiohttp_client"):
        sys.modules.setdefault(name, types.ModuleType(name))

    sys.modules["homeassistant.config_entries"].ConfigEntry = object
    sys.modules["homeassistant.core"].HomeAssistant = object

    class DataUpdateCoordinator:
        def __init__(self, *args, **kwargs):
            pass

        def __class_getitem__(cls, _):
            return cls

    uc = sys.modules["homeassistant.helpers.update_coordinator"]
    uc.DataUpdateCoordinator = DataUpdateCoordinator
    uc.UpdateFailed = Exception
    sys.modules["homeassistant.util"].dt = types.SimpleNamespace(
        now=lambda: datetime.now(timezone.utc))
    sys.modules["homeassistant.helpers.aiohttp_client"].async_get_clientsession = lambda h: None

    if "aiohttp" not in sys.modules:
        aiohttp = types.ModuleType("aiohttp")
        aiohttp.ClientError = Exception
        aiohttp.ClientSession = object
        aiohttp.ClientTimeout = lambda **kwargs: None
        sys.modules["aiohttp"] = aiohttp

    paket = types.ModuleType("openairlog")
    paket.__path__ = [str(PAKET)]
    sys.modules["openairlog"] = paket


_attrappen()


class _Hass:
    """Nur was der Coordinator braucht: Blockierendes im 'Executor'."""

    async def async_add_executor_job(self, funktion, *args):
        return funktion(*args)


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


def leg(code, flugnummer, von, nach, ab, an, kategorie="dienst"):
    return {"kategorie": kategorie, "code": code, "flugnummer": flugnummer,
            "von": von, "nach": nach, "beginn": utc(ab), "ende": utc(an),
            "datum": ab[:10]}


@pytest.fixture
def coordinator():
    """Coordinator ohne __init__ - Optionen und Profil setzt der Test."""
    from openairlog.coordinator import OpenAirLogCoordinator

    def bauen(optionen=None, profil=None, adsbdb=None):
        k = OpenAirLogCoordinator.__new__(OpenAirLogCoordinator)
        k.optionen = optionen or {}
        k.profil = profil or {}
        k.adsbdb = adsbdb
        k.hass = _Hass()
        return k

    return bauen


@pytest.fixture
def dienstplan_november():
    """Echter Dienstplan aus dem November 2026 - SIM, dann drei Langstrecken.

    Basis im Profil: EDDF. Stationen im Plan: FRA. Genau diese Mischung
    liess frueher alles zu einem einzigen Umlauf verschmelzen.
    """
    return [
        leg("SIM", None, "FRA", "FRA", "2026-11-08T22:00", "2026-11-09T02:00"),
        leg(None, "LH492", "FRA", "YVR", "2026-11-10T09:40", "2026-11-10T19:45"),
        leg(None, "LH493", "YVR", "FRA", "2026-11-12T21:25", "2026-11-13T07:10"),
        leg(None, "LH752", "FRA", "HYD", "2026-11-21T11:50", "2026-11-21T20:20"),
        leg(None, "LH753", "HYD", "FRA", "2026-11-22T22:10", "2026-11-23T07:55"),
        leg(None, "LH576", "FRA", "CPT", "2026-11-30T21:15", "2026-12-01T08:35"),
        leg(None, "LH577", "CPT", "FRA", "2026-12-03T17:10", "2026-12-04T04:35"),
    ]
