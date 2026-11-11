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


# Deutsche Ortsnamen fuer gaengige Ziele, nach IATA-Code. airportsdata liefert
# die Namen bunt gemischt (Munich, Firenze, Napoli, "Bale/Mulhouse", "Luqa"
# statt Malta, sogar "Larnarca"). Was hier fehlt, bleibt wie geliefert.
ORT_DE: dict[str, str] = {
    # Deutschland
    "MUC": "München", "CGN": "Köln", "DUS": "Düsseldorf", "NUE": "Nürnberg",
    "HAJ": "Hannover", "FMO": "Münster", "FDH": "Friedrichshafen",
    # Europa
    "VIE": "Wien", "SZG": "Salzburg", "GRZ": "Graz", "INN": "Innsbruck",
    "ZRH": "Zürich", "GVA": "Genf", "BSL": "Basel", "PRG": "Prag", "WAW": "Warschau",
    "KRK": "Krakau", "WRO": "Breslau", "GDN": "Danzig", "POZ": "Posen",
    "BUD": "Budapest", "OTP": "Bukarest", "SOF": "Sofia", "BEG": "Belgrad",
    "BRU": "Brüssel", "LUX": "Luxemburg", "CPH": "Kopenhagen", "ARN": "Stockholm",
    "GOT": "Göteborg", "OSL": "Oslo", "HEL": "Helsinki", "KEF": "Reykjavík",
    "LHR": "London", "LCY": "London", "LGW": "London", "MAN": "Manchester",
    "EDI": "Edinburgh", "DUB": "Dublin", "CDG": "Paris", "ORY": "Paris",
    "NCE": "Nizza", "LYS": "Lyon", "MRS": "Marseille", "TLS": "Toulouse",
    "BOD": "Bordeaux", "FCO": "Rom", "MXP": "Mailand", "LIN": "Mailand",
    "VCE": "Venedig", "FLR": "Florenz", "NAP": "Neapel", "BLQ": "Bologna",
    "TRN": "Turin", "CTA": "Catania", "PMO": "Palermo", "OLB": "Olbia",
    "CAG": "Cagliari", "BRI": "Bari", "LIS": "Lissabon", "OPO": "Porto",
    "FAO": "Faro", "PMI": "Palma", "AGP": "Málaga", "ATH": "Athen",
    "SKG": "Thessaloniki", "HER": "Heraklion", "RHO": "Rhodos", "CFU": "Korfu",
    "MLA": "Malta", "LCA": "Larnaka", "PFO": "Paphos", "IST": "Istanbul",
    "SAW": "Istanbul", "KBP": "Kiew", "RAK": "Marrakesch",
    "CAI": "Kairo", "TLV": "Tel Aviv",
    # Langstrecke, wo die Datenbank einen Vorort nennt
    "YVR": "Vancouver", "EWR": "New York", "JFK": "New York", "IAD": "Washington",
    "HND": "Tokio", "NRT": "Tokio", "KIX": "Osaka", "ICN": "Seoul",
    "PEK": "Peking", "PKX": "Peking", "MEX": "Mexiko-Stadt", "CPT": "Kapstadt",
    "GRU": "São Paulo", "EZE": "Buenos Aires", "SIN": "Singapur",
}


def ort_deutsch(iata: str | None, sonst: str | None = None) -> str | None:
    """Deutscher Ortsname, sonst was die Quelle geliefert hat."""
    return ORT_DE.get(str(iata or "").upper()) or sonst


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
