"""Flughafen-Stammdaten ohne Netz: Ort, Land und Zeitzone.

Grundlage ist das Paket ``airportsdata`` (MIT-Lizenz, rund 28.000 Flughaefen).
Es wird lokal nachgeschlagen - kein Abruf, kein Konto, kein Kontingent.

Zwei Aufgaben:
  * **Zeitzone** des Layover-Ziels, damit die Karte die Ortszeit zeigen kann
    ("In Vancouver ist es 16:47"). adsbdb kennt keine Zeitzonen.
  * **Rueckfallweg fuer den Klartext-Ort**, wenn adsbdb eine Flugnummer nicht
    kennt (alphanumerische Rufzeichen). Die Station steht ja im Dienstplan.

Das Laden der Tabellen liest Dateien von der Platte und darf deshalb nicht im
Event-Loop laufen - ``laden()`` gehoert in einen Executor.
"""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

_IATA: dict[str, dict[str, Any]] | None = None
_ICAO: dict[str, dict[str, Any]] | None = None


def laden() -> bool:
    """Liest beide Tabellen einmalig ein. Blockierend - im Executor aufrufen."""
    global _IATA, _ICAO  # noqa: PLW0603 - bewusst ein Modul-Speicher
    if _IATA is not None:
        return True
    try:
        import airportsdata  # noqa: PLC0415 - erst bei Bedarf laden
        _IATA = airportsdata.load("IATA")
        _ICAO = airportsdata.load("ICAO")
    except Exception as err:  # noqa: BLE001 - fehlt das Paket, gibt es eben keine Ortszeit
        _LOGGER.debug("airportsdata nicht verfuegbar: %s", err)
        _IATA, _ICAO = {}, {}
        return False
    return True


def geladen() -> bool:
    return _IATA is not None


def nachschlagen(code: str | None) -> dict[str, Any] | None:
    """IATA (FRA) oder ICAO (EDDF) -> {iata, icao, ort, name, land_iso, zeitzone}."""
    if not code or _IATA is None:
        return None
    c = str(code).strip().upper()
    roh = (_IATA.get(c) if len(c) == 3 else None) or (_ICAO or {}).get(c)
    if not roh:
        return None
    return {
        "iata": roh.get("iata") or None,
        "icao": roh.get("icao") or None,
        "ort": roh.get("city") or None,
        "name": roh.get("name") or None,
        "land_iso": roh.get("country") or None,
        "zeitzone": roh.get("tz") or None,
    }
