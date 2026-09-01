"""Lufthansa Open API: Live-Status zum anstehenden Flug.

Liefert - anders als reine Tracking-Dienste - sowohl die GEPLANTE als auch die
TATSAECHLICHE Zeit sowie echte Statuscodes (verspaetet, gestrichen, gelandet).
Der Zugang ist kostenlos; die Authentifizierung laeuft ueber OAuth
(client_credentials), das Token wird zwischengespeichert.

Abrufbar sind nur 7 Tage rueckwaerts bis 5 Tage voraus - fuer die Dienstplanung
bleibt OpenAirLog die Quelle, die Lufthansa-Daten verfeinern nur den Tag selbst.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiohttp

_LOGGER = logging.getLogger(__name__)

BASIS = "https://api.lufthansa.com/v1"
# Nur diese Codes bewerten wir; alles andere wird als Text durchgereicht.
STATUS_TEXT = {
    "CD": "gestrichen",
    "DP": "abgeflogen",
    "LD": "gelandet",
    "NA": "unbekannt",
    "NO": "keine Angabe",
    "OT": "pünktlich",
    "DL": "verspätet",
    "RT": "umgeleitet",
}


class LhFehler(Exception):
    """Fehler beim Abruf."""


class LhAuthFehler(LhFehler):
    """Zugangsdaten ungueltig."""


class LufthansaApi:
    def __init__(self, session: aiohttp.ClientSession,
                 client_id: str, client_secret: str) -> None:
        self._session = session
        self._id = client_id
        self._secret = client_secret
        self._token: str | None = None
        self._gueltig_bis: datetime | None = None

    async def _token_holen(self) -> str:
        jetzt = datetime.now(timezone.utc)
        if self._token and self._gueltig_bis and jetzt < self._gueltig_bis:
            return self._token
        daten = {"client_id": self._id, "client_secret": self._secret,
                 "grant_type": "client_credentials"}
        try:
            async with self._session.post(
                f"{BASIS}/oauth/token", data=daten,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status in (401, 403):
                    raise LhAuthFehler("Zugangsdaten abgelehnt")
                if resp.status != 200:
                    raise LhFehler(f"Token-Abruf: HTTP {resp.status}")
                antwort = await resp.json()
        except asyncio.TimeoutError as err:
            raise LhFehler("Zeitueberschreitung beim Token-Abruf") from err
        except aiohttp.ClientError as err:
            raise LhFehler(f"Netzwerkfehler: {err}") from err

        self._token = antwort.get("access_token")
        # Sicherheitsabstand, damit wir nie mit abgelaufenem Token anfragen.
        self._gueltig_bis = jetzt + timedelta(
            seconds=max(60, int(antwort.get("expires_in", 3600)) - 300))
        if not self._token:
            raise LhAuthFehler("Kein Token erhalten")
        return self._token

    async def flugstatus(self, flugnummer: str, tag: str) -> dict | None:
        """Holt den Status eines Fluges (z. B. LH440 am 2026-09-04)."""
        token = await self._token_holen()
        kopf = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        url = f"{BASIS}/operations/flightstatus/{flugnummer}/{tag}"
        try:
            async with self._session.get(
                url, headers=kopf, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status in (401, 403):
                    self._token = None          # Token verworfen, naechstes Mal neu
                    raise LhAuthFehler(f"HTTP {resp.status}")
                if resp.status == 404:
                    return None                  # Flug nicht gefunden
                if resp.status == 429:
                    raise LhFehler("Kontingent erschoepft (429)")
                if resp.status != 200:
                    raise LhFehler(f"HTTP {resp.status}")
                return await resp.json()
        except asyncio.TimeoutError as err:
            raise LhFehler("Zeitueberschreitung") from err
        except aiohttp.ClientError as err:
            raise LhFehler(f"Netzwerkfehler: {err}") from err


def _zeit(block: dict | None) -> datetime | None:
    """Liest einen UTC-Zeitstempel aus der verschachtelten Struktur."""
    if not isinstance(block, dict):
        return None
    wert = (block.get("DateTime") if isinstance(block, dict) else None)
    if not wert:
        return None
    try:
        return datetime.fromisoformat(str(wert)).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def auswerten(antwort: dict, geplant_ab: datetime | None) -> dict | None:
    """Formt die Lufthansa-Antwort in flache Werte fuer die Sensoren um."""
    try:
        fluege = antwort["FlightStatusResource"]["Flights"]["Flight"]
    except (KeyError, TypeError):
        return None
    if isinstance(fluege, dict):
        fluege = [fluege]
    if not fluege:
        return None
    f = fluege[0]

    ab, an = f.get("Departure") or {}, f.get("Arrival") or {}
    status_code = (f.get("FlightStatus") or {}).get("Code")
    status_text = STATUS_TEXT.get(status_code) or \
        (f.get("FlightStatus") or {}).get("Definition") or "unbekannt"

    plan_ab = _zeit(ab.get("ScheduledTimeUTC"))
    ist_ab = _zeit(ab.get("ActualTimeUTC")) or _zeit(ab.get("EstimatedTimeUTC"))
    plan_an = _zeit(an.get("ScheduledTimeUTC"))
    ist_an = _zeit(an.get("ActualTimeUTC")) or _zeit(an.get("EstimatedTimeUTC"))

    def diff(ist, plan):
        return round((ist - plan).total_seconds() / 60) if ist and plan else None

    return {
        "status": status_text,
        "status_code": status_code,
        "gestrichen": status_code == "CD",
        "abflug_plan": plan_ab,
        "abflug_ist": ist_ab,
        "ankunft_plan": plan_an,
        "ankunft_ist": ist_an,
        # Verspaetung vorrangig gegen die Airline-Planzeit, ersatzweise gegen
        # den eigenen Dienstplan.
        "verspaetung_ab": diff(ist_ab, plan_ab) if plan_ab else diff(ist_ab, geplant_ab),
        "verspaetung_an": diff(ist_an, plan_an),
        "terminal_ab": ((ab.get("Terminal") or {}).get("Name")),
        "gate_ab": ((ab.get("Terminal") or {}).get("Gate")),
        "terminal_an": ((an.get("Terminal") or {}).get("Name")),
        "zeitstatus_ab": ((ab.get("TimeStatus") or {}).get("Definition")),
        "zeitstatus_an": ((an.get("TimeStatus") or {}).get("Definition")),
    }
