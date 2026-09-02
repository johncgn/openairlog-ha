"""Sensoren: naechster Dienst, Dienstende, Wege, Statistik."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ANFAHRT_MIN, CONF_HEIMWEG_MIN, CONF_LH_ID, DOMAIN
from .entity import OpenAirLogEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    k = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        DienstZeitSensor(k, "naechster_dienst", "Nächster Dienst", "beginn", 0),
        DienstZeitSensor(k, "naechster_dienst_ende", "Dienstende", "ende", 0,
                         object_id="dienstende"),
        DienstZeitSensor(k, "zuhause", "Voraussichtlich zuhause",
                         "ende", int(entry.options.get(CONF_HEIMWEG_MIN, 0)),
                         object_id="voraussichtlich_zuhause"),
        NaechsterSchrittSensor(k,
                               int(entry.options.get(CONF_ANFAHRT_MIN, 0)),
                               int(entry.options.get(CONF_HEIMWEG_MIN, 0))),
        StatistikSensor(k, "flugstunden", "Flugstunden gesamt", "block_minutes", 60,
                        object_id="flugstunden_gesamt"),
        StatistikSensor(k, "landungen", "Landungen gesamt", "landings", 1,
                        object_id="landungen_gesamt"),
    ])
    # Live-Sensoren nur, wenn Lufthansa-Zugangsdaten hinterlegt sind.
    if entry.options.get(CONF_LH_ID):
        async_add_entities([FlugStatusSensor(k), VerspaetungSensor(k)])


class DienstZeitSensor(OpenAirLogEntity, SensorEntity):
    """Zeitpunkt rund um den naechsten (oder laufenden) Dienst."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, koordinator, schluessel, name, feld, versatz_min,
                 object_id=None) -> None:
        super().__init__(koordinator, schluessel, object_id=object_id)
        self._attr_name = name
        self._feld = feld
        self._versatz = timedelta(minutes=versatz_min)
        self._attr_icon = "mdi:airplane-clock"

    @property
    def _dienst(self) -> dict | None:
        daten = self.coordinator.data or {}
        # Laeuft gerade ein Dienst, beziehen sich Dienstende/Heimkehr darauf.
        if self._feld == "ende" and daten.get("aktuell"):
            return daten["aktuell"]
        return daten.get("aktuell") if self._feld == "ende" else daten.get("naechster")

    @property
    def native_value(self):
        d = self._dienst or (self.coordinator.data or {}).get("naechster")
        if not d or not d.get(self._feld):
            return None
        return d[self._feld] + self._versatz

    @property
    def extra_state_attributes(self):
        u = self._dienst or (self.coordinator.data or {}).get("naechster")
        if not u:
            return {}
        return {
            "dienstcode": u.get("code"),
            "kategorie": u.get("kategorie"),
            "von": u.get("von"),
            "nach": u.get("nach"),
            "stationen": " – ".join(x for x in (u.get("stationen") or []) if x),
            "flugnummern": ", ".join(u.get("flugnummern") or []),
            "anzahl_legs": u.get("anzahl_legs"),
            "mehrtaegig": u.get("mehrtaegig"),
            "abflug": u.get("abflug"),
            "ankunft": u.get("ankunft"),
            "datum": u.get("datum"),
            "art": u.get("art"),
            "briefing": u.get("beginn"),
            "vor_ort": u.get("vor_ort"),
            "briefing_minuten": u.get("briefing_minuten"),
            "puffer_minuten": u.get("puffer_minuten"),
            "legs": [
                {
                    "flug": l.get("flugnummer") or l.get("code"),
                    "von": l.get("von"), "nach": l.get("nach"),
                    "ab": l.get("beginn"), "an": l.get("ende"),
                    "muster": l.get("muster"),
                }
                for l in (u.get("legs") or [])
            ],
        }


class NaechsterSchrittSensor(OpenAirLogEntity, SensorEntity):
    """Eine Kachel, die mitdenkt.

    Vor dem Dienst zeigt sie die Losfahrzeit, waehrend des Dienstes die
    voraussichtliche Heimkehr. Name und Symbol wechseln mit.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, koordinator, anfahrt_min: int, heimweg_min: int) -> None:
        super().__init__(koordinator, "naechster_schritt", object_id="losfahren")
        self._anfahrt = timedelta(minutes=anfahrt_min)
        self._heimweg = timedelta(minutes=heimweg_min)

    @property
    def _unterwegs(self) -> bool:
        return bool((self.coordinator.data or {}).get("aktuell"))

    @property
    def name(self) -> str:
        return "Zurück zuhause" if self._unterwegs else "Losfahren"

    @property
    def icon(self) -> str:
        return "mdi:home-clock-outline" if self._unterwegs else "mdi:train-car"

    @property
    def native_value(self):
        daten = self.coordinator.data or {}
        if (u := daten.get("aktuell")):
            return u["ende"] + self._heimweg
        if (u := daten.get("naechster")):
            # Nicht der Dienstbeginn zaehlt, sondern wann man vor Ort sein
            # moechte - also inklusive persoenlichem Puffer.
            return (u.get("vor_ort") or u["beginn"]) - self._anfahrt
        return None

    @property
    def extra_state_attributes(self):
        # "beschriftung" ist fuer die Kachel gedacht: Der Kartenname bleibt fest,
        # die wechselnde Bedeutung steht darunter im Text.
        return {
            "richtung": "heimweg" if self._unterwegs else "anfahrt",
            "beschriftung": "Zurück zuhause" if self._unterwegs else "Losfahren",
        }


class FlugStatusSensor(OpenAirLogEntity, SensorEntity):
    """Live-Status des anstehenden Fluges laut Lufthansa."""

    _attr_name = "Flugstatus"
    _attr_icon = "mdi:airplane-alert"

    def __init__(self, koordinator) -> None:
        super().__init__(koordinator, "flugstatus")

    @property
    def native_value(self):
        live = (self.coordinator.data or {}).get("live")
        return live.get("status") if live else "kein Flug"

    @property
    def icon(self) -> str:
        live = (self.coordinator.data or {}).get("live") or {}
        if live.get("gestrichen"):
            return "mdi:airplane-off"
        if live.get("status_code") == "LD":
            return "mdi:airplane-landing"
        if live.get("status_code") == "DP":
            return "mdi:airplane-takeoff"
        return "mdi:airplane-alert"

    @property
    def extra_state_attributes(self):
        live = (self.coordinator.data or {}).get("live") or {}
        return {k: live.get(k) for k in (
            "flugnummer", "status_code", "gestrichen",
            "abflug_plan", "abflug_ist", "ankunft_plan", "ankunft_ist",
            "terminal_ab", "gate_ab", "terminal_an",
            "zeitstatus_ab", "zeitstatus_an")}


class VerspaetungSensor(OpenAirLogEntity, SensorEntity):
    """Verspaetung beim Abflug in Minuten (Ist gegen Plan)."""

    _attr_name = "Verspätung"
    _attr_icon = "mdi:clock-alert-outline"
    _attr_native_unit_of_measurement = "min"

    def __init__(self, koordinator) -> None:
        super().__init__(koordinator, "verspaetung")

    @property
    def native_value(self):
        return ((self.coordinator.data or {}).get("live") or {}).get("verspaetung_ab")

    @property
    def extra_state_attributes(self):
        live = (self.coordinator.data or {}).get("live") or {}
        v = live.get("verspaetung_ab")
        return {
            "bewertung": None if v is None else (
                "pünktlich" if v <= 5 else
                ("leicht verspätet" if v <= 20 else "verspätet")),
            "verspaetung_ankunft": live.get("verspaetung_an"),
            "flugnummer": live.get("flugnummer"),
        }


class StatistikSensor(OpenAirLogEntity, SensorEntity):
    """Summenwerte aus /statistics."""

    def __init__(self, koordinator, schluessel, name, feld, teiler,
                 object_id=None) -> None:
        super().__init__(koordinator, schluessel, object_id=object_id)
        self._attr_name = name
        self._feld = feld
        self._teiler = teiler
        self._attr_icon = "mdi:chart-timeline-variant"
        if teiler == 60:
            self._attr_native_unit_of_measurement = "h"

    @property
    def native_value(self):
        s = ((self.coordinator.data or {}).get("statistik") or {}).get("summary") or {}
        wert = s.get(self._feld)
        if wert in (None, ""):
            return None
        try:
            return round(float(wert) / self._teiler, 1 if self._teiler == 60 else 0)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self):
        st = (self.coordinator.data or {}).get("statistik") or {}
        if self._feld != "block_minutes":
            return {}
        return {"nach_muster": st.get("by_aircraft_type", [])[:10]}
