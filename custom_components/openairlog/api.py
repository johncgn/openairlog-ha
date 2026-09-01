"""Schlanker REST-Client fuer die OpenAirLog-API (nur lesend)."""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any

import aiohttp

from .const import BASIS_URL

_LOGGER = logging.getLogger(__name__)


class OpenAirLogFehler(Exception):
    """Allgemeiner API-Fehler."""


class AuthFehler(OpenAirLogFehler):
    """Schluessel ungueltig, gesperrt oder ohne noetigen Scope."""


class RateLimitFehler(OpenAirLogFehler):
    """Kontingent erschoepft (HTTP 429)."""

    def __init__(self, wartezeit: int) -> None:
        super().__init__(f"Rate-Limit erreicht, erneut in {wartezeit}s")
        self.wartezeit = wartezeit


class OpenAirLogApi:
    """Kapselt alle HTTP-Aufrufe."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        self._session = session
        self._key = api_key

    async def _get(self, pfad: str, params: dict[str, Any] | None = None) -> dict:
        kopf = {"Authorization": f"Bearer {self._key}", "Accept": "application/json"}
        try:
            async with self._session.get(
                f"{BASIS_URL}{pfad}", headers=kopf, params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status in (401, 403):
                    raise AuthFehler(f"HTTP {resp.status} fuer {pfad}")
                if resp.status == 429:
                    # Die API nennt die Wartezeit im Header - den respektieren wir.
                    raise RateLimitFehler(int(resp.headers.get("Retry-After", "60")))
                if resp.status != 200:
                    raise OpenAirLogFehler(f"HTTP {resp.status} fuer {pfad}")
                return await resp.json()
        except asyncio.TimeoutError as err:
            raise OpenAirLogFehler(f"Zeitueberschreitung bei {pfad}") from err
        except aiohttp.ClientError as err:
            raise OpenAirLogFehler(f"Netzwerkfehler bei {pfad}: {err}") from err

    async def profil(self) -> dict:
        return (await self._get("/profile")).get("data", {})

    async def statistik(self) -> dict:
        return (await self._get("/statistics")).get("data", {})

    async def fluege(self, von: date, bis: date) -> list[dict]:
        """Holt alle Eintraege im Zeitraum und folgt dabei der Paginierung."""
        eintraege: list[dict] = []
        seite = 1
        while True:
            antwort = await self._get("/flights", {
                "from": von.isoformat(), "to": bis.isoformat(),
                "per_page": 200, "page": seite,
            })
            eintraege += antwort.get("data", [])
            meta = antwort.get("meta", {})
            if seite >= int(meta.get("last_page", 1)) or seite > 20:
                break
            seite += 1
        return eintraege

    async def pruefe_zugang(self) -> dict:
        """Fuer den Config-Flow: Schluessel testen und Profil zurueckgeben."""
        profil = await self.profil()
        # Ein Minimalabruf zeigt, ob auch der Scope flights:read vorhanden ist.
        heute = date.today()
        await self.fluege(heute, heute + timedelta(days=1))
        return profil
