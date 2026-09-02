"""Meldet, ob gerade Dienst ist."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import OpenAirLogEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([ImDienstSensor(hass.data[DOMAIN][entry.entry_id])])


class ImDienstSensor(OpenAirLogEntity, BinarySensorEntity):
    _attr_name = "Im Dienst"
    _attr_icon = "mdi:airplane-takeoff"

    def __init__(self, koordinator) -> None:
        super().__init__(koordinator, "im_dienst")

    @property
    def is_on(self) -> bool:
        return (self.coordinator.data or {}).get("aktuell") is not None

    @property
    def extra_state_attributes(self):
        d = (self.coordinator.data or {}).get("aktuell")
        if not d:
            return {}
        return {"dienstcode": d.get("code"),
                "flugnummern": ", ".join(d.get("flugnummern") or []),
                "von": d.get("von"), "nach": d.get("nach"), "ende": d.get("ende")}
