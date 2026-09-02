"""Einrichtung ueber die Oberflaeche."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector, NumberSelectorConfig, NumberSelectorMode,
    TextSelector, TextSelectorConfig, TextSelectorType,
)

from .api import AuthFehler, OpenAirLogApi, OpenAirLogFehler
from .const import (
    CONF_ANFAHRT_MIN, CONF_API_KEY, CONF_BASIS, CONF_BRIEFING_MIN,
    CONF_DEBRIEFING_MIN, CONF_HEIMWEG_MIN, CONF_TAGE_RUECK, CONF_TAGE_VORAUS,
    CONF_LH_FENSTER, CONF_LH_ID, CONF_LH_SECRET, CONF_TURNAROUND_MIN,
    DOMAIN, KAT_FREI, KAT_SCHULUNG, KAT_STANDBY,
    STANDARD_BRIEFING_MIN, STANDARD_DEBRIEFING_MIN, STANDARD_KATEGORIEN,
    STANDARD_LH_FENSTER_H, STANDARD_TAGE_RUECK, STANDARD_TAGE_VORAUS,
    STANDARD_TURNAROUND_MIN,
    CONF_BRIEFING_SIM_MIN,
    CONF_CODES_SIM,
    CONF_DEBRIEFING_SIM_MIN,
    CONF_PUFFER_MIN,
    STANDARD_BRIEFING_SIM_MIN,
    STANDARD_CODES_SIM,
    STANDARD_DEBRIEFING_SIM_MIN,
    STANDARD_PUFFER_MIN,
    CONF_CODES_WBT,
    STANDARD_CODES_WBT,
)


def _codes(kat: str) -> str:
    return ", ".join(sorted(c for c, k in STANDARD_KATEGORIEN.items() if k == kat))


def _liste(text: str | list | None) -> list[str]:
    if isinstance(text, list):
        return text
    return [t.strip() for t in (text or "").split(",") if t.strip()]


class OpenAirLogConfigFlow(ConfigFlow, domain=DOMAIN):
    """Fragt den API-Schluessel ab und prueft ihn sofort."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        fehler: dict[str, str] = {}
        if user_input is not None:
            api = OpenAirLogApi(async_get_clientsession(self.hass),
                                user_input[CONF_API_KEY])
            try:
                profil = await api.pruefe_zugang()
            except AuthFehler:
                fehler["base"] = "auth"
            except OpenAirLogFehler:
                fehler["base"] = "verbindung"
            else:
                await self.async_set_unique_id(str(profil.get("id")))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=profil.get("name") or "OpenAirLog", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=fehler,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return OpenAirLogOptionsFlow(entry)


class OpenAirLogOptionsFlow(OptionsFlow):
    """Zwei Schritte: erst Zeiten und Wege, dann die Dienstcodes."""

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._daten: dict[str, Any] = {}

    def _min(self, feld: str, standard: int, maximum: int = 600):
        return vol.Optional(
            feld, default=self.entry.options.get(feld, standard)
        ), NumberSelector(NumberSelectorConfig(
            min=0, max=maximum, step=5, unit_of_measurement="min",
            mode=NumberSelectorMode.BOX))

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Schritt 1: Briefing, Wege, Umlauf-Grenze."""
        if user_input is not None:
            self._daten.update(user_input)
            return await self.async_step_codes()

        o = self.entry.options
        felder: dict = {}
        for feld, standard, maximum in (
            (CONF_BRIEFING_MIN, STANDARD_BRIEFING_MIN, 300),
            (CONF_DEBRIEFING_MIN, STANDARD_DEBRIEFING_MIN, 300),
            (CONF_BRIEFING_SIM_MIN, STANDARD_BRIEFING_SIM_MIN, 300),
            (CONF_DEBRIEFING_SIM_MIN, STANDARD_DEBRIEFING_SIM_MIN, 300),
            (CONF_PUFFER_MIN, STANDARD_PUFFER_MIN, 180),
            (CONF_ANFAHRT_MIN, 0, 600),
            (CONF_HEIMWEG_MIN, 0, 600),
            (CONF_TURNAROUND_MIN, STANDARD_TURNAROUND_MIN, 1440),
        ):
            schluessel, selektor = self._min(feld, standard, maximum)
            felder[schluessel] = selektor
        felder[vol.Optional(CONF_BASIS, default=o.get(CONF_BASIS, ""))] = TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT))
        return self.async_show_form(step_id="init", data_schema=vol.Schema(felder),
                                    last_step=False)

    async def async_step_codes(self, user_input: dict[str, Any] | None = None):
        """Schritt 2: Bedeutung der Dienstcodes und Vorschauzeitraum."""
        if user_input is not None:
            daten = {**self._daten, **user_input}
            for feld in ("codes_frei", "codes_standby", "codes_schulung",
                         CONF_CODES_SIM, CONF_CODES_WBT):
                daten[feld] = _liste(daten.get(feld))
            for feld in (CONF_BRIEFING_MIN, CONF_DEBRIEFING_MIN,
                         CONF_BRIEFING_SIM_MIN, CONF_DEBRIEFING_SIM_MIN,
                         CONF_PUFFER_MIN, CONF_ANFAHRT_MIN,
                         CONF_HEIMWEG_MIN, CONF_TURNAROUND_MIN, CONF_TAGE_VORAUS,
                         CONF_TAGE_RUECK):
                if feld in daten:
                    daten[feld] = int(float(daten[feld]))
            # Bereits hinterlegte Lufthansa-Zugangsdaten nicht verlieren, auch
            # wenn der Schritt derzeit ausgeblendet ist.
            for feld in (CONF_LH_ID, CONF_LH_SECRET, CONF_LH_FENSTER):
                if feld not in daten and feld in self.entry.options:
                    daten[feld] = self.entry.options[feld]
            return self.async_create_entry(title="", data=daten)

        o = self.entry.options
        schema = vol.Schema({
            vol.Optional("codes_frei", default=", ".join(
                _liste(o.get("codes_frei")) or _liste(_codes(KAT_FREI)))): str,
            vol.Optional("codes_standby", default=", ".join(
                _liste(o.get("codes_standby")) or _liste(_codes(KAT_STANDBY)))): str,
            vol.Optional("codes_schulung", default=", ".join(
                _liste(o.get("codes_schulung")) or _liste(_codes(KAT_SCHULUNG)))): str,
            vol.Optional(CONF_CODES_SIM, default=", ".join(
                _liste(o.get(CONF_CODES_SIM)) or STANDARD_CODES_SIM)): str,
            vol.Optional(CONF_CODES_WBT, default=", ".join(
                _liste(o.get(CONF_CODES_WBT)) or STANDARD_CODES_WBT)): str,
            vol.Optional(CONF_TAGE_VORAUS,
                         default=o.get(CONF_TAGE_VORAUS, STANDARD_TAGE_VORAUS)): vol.Coerce(int),
            vol.Optional(CONF_TAGE_RUECK,
                         default=o.get(CONF_TAGE_RUECK, STANDARD_TAGE_RUECK)): vol.Coerce(int),
        })
        return self.async_show_form(step_id="codes", data_schema=schema,
                                    last_step=True)

    async def async_step_lufthansa(self, user_input: dict[str, Any] | None = None):
        """Lufthansa Open API - derzeit NICHT im Dialog verlinkt.

        Lufthansa hat die Entwickler-Registrierung ausgesetzt ("Registration to
        OpenAPI is on hold until further notice"), neue Zugaenge gibt es also
        nicht. Der Schritt bleibt hier stehen, damit er sich mit einer Zeile
        wieder einhaengen laesst: in async_step_codes statt des
        async_create_entry ein "return await self.async_step_lufthansa()".
        Wer bereits Zugangsdaten hat, behaelt sie - sie werden beim Speichern
        mitgenommen und die Live-Sensoren erscheinen weiterhin.
        """
        if user_input is not None:
            daten = {**self._daten, **user_input}
            for feld in (CONF_LH_ID, CONF_LH_SECRET):
                daten[feld] = (daten.get(feld) or "").strip()
            daten[CONF_LH_FENSTER] = int(float(
                daten.get(CONF_LH_FENSTER, STANDARD_LH_FENSTER_H)))
            return self.async_create_entry(title="", data=daten)

        o = self.entry.options
        schema = vol.Schema({
            vol.Optional(CONF_LH_ID, default=o.get(CONF_LH_ID, "")): str,
            vol.Optional(CONF_LH_SECRET,
                         default=o.get(CONF_LH_SECRET, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Optional(CONF_LH_FENSTER,
                         default=o.get(CONF_LH_FENSTER,
                                       STANDARD_LH_FENSTER_H)): NumberSelector(
                NumberSelectorConfig(min=1, max=120, step=1,
                                     unit_of_measurement="h",
                                     mode=NumberSelectorMode.BOX)),
        })
        return self.async_show_form(step_id="lufthansa", data_schema=schema,
                                    last_step=True)
