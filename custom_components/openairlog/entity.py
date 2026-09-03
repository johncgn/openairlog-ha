"""Gemeinsame Basis aller OpenAirLog-Entitaeten."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenAirLogCoordinator


class OpenAirLogEntity(CoordinatorEntity[OpenAirLogCoordinator]):
    # HA stellt den Geraetenamen dem Entitaetsnamen voran. Damit daraus keine
    # Bandwurmnamen werden ("OpenAirLog Max Mustermann Losfahren"), heisst das
    # Geraet schlicht "OpenAirLog" - der Kontoinhaber steht im Eintragstitel.
    _attr_has_entity_name = True

    def __init__(self, koordinator: OpenAirLogCoordinator, schluessel: str,
                 object_id: str | None = None) -> None:
        super().__init__(koordinator)
        profil = koordinator.profil or {}
        self._object_id = object_id or schluessel
        self._attr_unique_id = f"{profil.get('id', 'oal')}_{schluessel}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(profil.get("id", "oal")))},
            # Hier haengt keine Hardware, sondern ein Webdienst. Ohne entry_type
            # fuehrt HA den Eintrag unter "Geraete" - das ist irrefuehrend.
            entry_type=DeviceEntryType.SERVICE,
            name="OpenAirLog",
            manufacturer="OpenAirLog",
            # "Modell" beschreibt, WAS der Dienst ist - nicht, wer ihn nutzt.
            # Frueher stand hier crew_role, also schlicht "pilot": eine
            # Eigenschaft des Nutzers, an einer Stelle fuer Geraeteangaben.
            model="Flugbuch & Dienstplan",
            configuration_url="https://openairlog.de",
        )

    @property
    def suggested_object_id(self) -> str | None:
        return self._object_id
