"""OpenAirLog - Flugbuch und Dienstplan in Home Assistant."""
from __future__ import annotations

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OpenAirLogApi
from .const import CONF_API_KEY, CONF_LH_ID, CONF_LH_SECRET, DOMAIN
from .coordinator import OpenAirLogCoordinator
from .lufthansa import LufthansaApi

PLATTFORMEN = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CALENDAR]


KARTE_URL = "/openairlog/openairlog-card.js"


async def _karte_bereitstellen(hass: HomeAssistant) -> None:
    """Liefert die Lovelace-Karte aus der Integration aus.

    So muss die Karte nicht getrennt ueber HACS installiert werden - sie kommt
    mit der Integration mit und meldet sich selbst beim Frontend an.
    """
    if hass.data.setdefault(DOMAIN, {}).get("_karte"):
        return
    pfad = hass.config.path(f"custom_components/{DOMAIN}/www/openairlog-card.js")
    await hass.http.async_register_static_paths(
        [StaticPathConfig(KARTE_URL, pfad, True)]
    )
    add_extra_js_url(hass, f"{KARTE_URL}?v=1.0.3")
    hass.data[DOMAIN]["_karte"] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await _karte_bereitstellen(hass)
    session = async_get_clientsession(hass)
    api = OpenAirLogApi(session, entry.data[CONF_API_KEY])
    lh_id = entry.options.get(CONF_LH_ID)
    lh_secret = entry.options.get(CONF_LH_SECRET)
    lh = LufthansaApi(session, lh_id, lh_secret) if lh_id and lh_secret else None
    koordinator = OpenAirLogCoordinator(hass, api, dict(entry.options), lh)
    await koordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = koordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATTFORMEN)
    entry.async_on_unload(entry.add_update_listener(_optionen_geaendert))
    return True


async def _optionen_geaendert(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATTFORMEN)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok
