"""Dienstplan als Kalender - ein Termin je Umlauf, freie Tage ganztaegig."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, KAT_DIENST, KAT_FREI, KAT_SCHULUNG, KAT_STANDBY
from .entity import OpenAirLogEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([DienstplanKalender(hass.data[DOMAIN][entry.entry_id])])


def _titel(u: dict) -> str:
    stationen = [s for s in (u.get("stationen") or []) if s]
    if u.get("flugnummern"):
        return "%s (%s)" % (" – ".join(stationen), ", ".join(u["flugnummern"]))
    if stationen:
        return "%s %s" % (u.get("code") or "Dienst", stationen[0])
    return u.get("code") or "Dienst"


def _beschreibung(u: dict) -> str:
    zeilen = []
    if u.get("anzahl_legs", 0) > 1 or u.get("mehrtaegig"):
        zeilen.append("%d Abschnitte%s" % (
            u["anzahl_legs"], ", mehrtägig" if u.get("mehrtaegig") else ""))
    for l in u.get("legs") or []:
        ab = dt_util.as_local(l["beginn"]).strftime("%d.%m. %H:%M") if l.get("beginn") else "?"
        an = dt_util.as_local(l["ende"]).strftime("%H:%M") if l.get("ende") else "?"
        zeilen.append("%s  %s → %s  %s%s" % (
            ab, l.get("von") or "?", l.get("nach") or "?", an,
            "  " + l["muster"] if l.get("muster") else ""))
    if u.get("abflug"):
        zeilen.append("Abflug %s (Briefing davor)"
                      % dt_util.as_local(u["abflug"]).strftime("%H:%M"))
    return "\n".join(zeilen)


class DienstplanKalender(OpenAirLogEntity, CalendarEntity):
    _attr_name = "Dienstplan"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, koordinator) -> None:
        super().__init__(koordinator, "dienstplan")

    def _termine(self) -> list[CalendarEvent]:
        daten = self.coordinator.data or {}
        termine: list[CalendarEvent] = []

        # Ein Termin je Umlauf: Briefing bis zurueck an der Basis
        for u in daten.get("umlaeufe", []):
            termine.append(CalendarEvent(
                summary=_titel(u), start=u["beginn"], end=u["ende"],
                location=u.get("von") or "", description=_beschreibung(u)))

        # Umlauf-Termine decken timed Dienste/Standby/Schulung bereits ab.
        # Frei, WBT und Eintraege ohne Uhrzeit kommen als ganztaegig dazu.
        for d in daten.get("dienste", []):
            if (d["kategorie"] in (KAT_DIENST, KAT_STANDBY, KAT_SCHULUNG)
                    and d.get("beginn") and d.get("ende")):
                continue
            try:
                tag = date.fromisoformat(d["datum"])
            except (TypeError, ValueError):
                continue
            termine.append(CalendarEvent(
                summary=d.get("code") or ("frei" if d["kategorie"] == KAT_FREI else "Termin"),
                start=tag, end=tag + timedelta(days=1),
                description=d.get("bemerkung") or ""))
        return termine

    @property
    def event(self) -> CalendarEvent | None:
        jetzt = dt_util.utcnow()
        kommend = [t for t in self._termine()
                   if isinstance(t.start, datetime) and t.end >= jetzt]
        return min(kommend, key=lambda t: t.start) if kommend else None

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime,
                               end_date: datetime) -> list[CalendarEvent]:
        raus = []
        for t in self._termine():
            beginn = t.start if isinstance(t.start, datetime) else \
                dt_util.start_of_local_day(t.start)
            ende = t.end if isinstance(t.end, datetime) else \
                dt_util.start_of_local_day(t.end)
            if ende >= start_date and beginn <= end_date:
                raus.append(t)
        return sorted(raus, key=lambda e: (
            e.start if isinstance(e.start, datetime) else dt_util.start_of_local_day(e.start)))
