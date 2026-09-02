"""OpenAirLog - Flugbuch und Dienstplan in Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_integration

from .api import OpenAirLogApi
from .const import CONF_API_KEY, CONF_LH_ID, CONF_LH_SECRET, DOMAIN
from .coordinator import OpenAirLogCoordinator
from .lufthansa import LufthansaApi

_LOGGER = logging.getLogger(__name__)

PLATTFORMEN = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CALENDAR]

KARTE_URL = f"/{DOMAIN}/openairlog-card.js"


async def _als_ressource_eintragen(hass: HomeAssistant, url: str) -> bool:
    """Traegt die Karte in die Lovelace-Ressourcen ein - wie eine HACS-Karte.

    Wichtig fuer die Zuverlaessigkeit: Nur bei registrierten Ressourcen weiss das
    Frontend, dass es auf das Laden warten muss. Ueber add_extra_js_url allein
    kann das Dashboard rendern, bevor die Karte definiert ist - dann erscheint
    "Konfigurationsfehler", mal ja, mal nein, je nach Cache und Ladereihenfolge.
    """
    try:
        daten = hass.data.get(LOVELACE_DOMAIN)
        ressourcen = getattr(daten, "resources", None)
        # Nicht ueber ein "mode"-Attribut gehen - das gibt es je nach HA-Version
        # nicht mehr. Entscheidend ist, ob die Sammlung beschreibbar ist:
        # im YAML-Modus fehlt async_create_item, dann pflegt der Nutzer selbst.
        if ressourcen is None or not hasattr(ressourcen, "async_create_item"):
            _LOGGER.debug("Lovelace-Ressourcen nicht beschreibbar (%s)",
                          type(ressourcen).__name__)
            return False

        if hasattr(ressourcen, "async_get_info"):
            await ressourcen.async_get_info()

        eigene = [
            r for r in ressourcen.async_items()
            if str(r.get("url", "")).startswith(KARTE_URL)
        ]
        if not eigene:
            await ressourcen.async_create_item({"res_type": "module", "url": url})
            _LOGGER.debug("Karte als Lovelace-Ressource eingetragen: %s", url)
        elif eigene[0].get("url") != url:
            # Version im Query-Teil aktualisieren, damit Browser neu laden
            await ressourcen.async_update_item(eigene[0]["id"], {"url": url})
            _LOGGER.debug("Karten-Ressource aktualisiert: %s", url)
        return True
    except Exception:  # noqa: BLE001 - Karte darf das Setup nie verhindern
        _LOGGER.debug("Eintrag als Lovelace-Ressource nicht moeglich", exc_info=True)
        return False


async def _karte_bereitstellen(hass: HomeAssistant) -> None:
    """Liefert die Lovelace-Karte aus der Integration aus.

    So muss die Karte nicht getrennt ueber HACS installiert werden - sie kommt
    mit der Integration mit und meldet sich selbst beim Frontend an.
    """
    if hass.data.setdefault(DOMAIN, {}).get("_karte"):
        return
    hass.data[DOMAIN]["_karte"] = True

    pfad = hass.config.path(f"custom_components/{DOMAIN}/www/openairlog-card.js")
    await hass.http.async_register_static_paths(
        [StaticPathConfig(KARTE_URL, pfad, True)]
    )

    # Version aus dem Manifest - so muss sie nie von Hand nachgezogen werden
    integration = await async_get_integration(hass, DOMAIN)
    url = f"{KARTE_URL}?v={integration.version}"

    if not await _als_ressource_eintragen(hass, url):
        add_extra_js_url(hass, url)  # Rueckfallweg (YAML-Modus)


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
