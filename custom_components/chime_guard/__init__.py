"""The Chime Guard integration: Silent Google Cast Playback."""
from __future__ import annotations

import logging
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    FRONTEND_SCRIPT_URL,
    VERSION,
)
from .websocket import async_setup_websocket
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Chime Guard integration from yaml (if any)."""
    hass.data.setdefault(DOMAIN, {})

    # Register static path for frontend JavaScript
    js_path = hass.config.path(f"custom_components/{DOMAIN}/frontend/chime_guard.js")
    
    try:
        from homeassistant.components.http import StaticPathConfig
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                FRONTEND_SCRIPT_URL,
                js_path,
                False,
            )
        ])
    except (ImportError, AttributeError):
        try:
            hass.http.register_static_path(FRONTEND_SCRIPT_URL, js_path, False)
        except Exception as err:
            _LOGGER.warning("Could not register static path: %s", err)

    # Automatically register script as extra_js_url so users don't need manual YAML resources
    script_url_versioned = f"{FRONTEND_SCRIPT_URL}?v={VERSION}"
    try:
        from homeassistant.components.frontend import add_extra_js_url
        add_extra_js_url(hass, script_url_versioned)
    except (ImportError, AttributeError):
        if "frontend_extra_module_url" not in hass.data:
            hass.data["frontend_extra_module_url"] = set()
        hass.data["frontend_extra_module_url"].add(script_url_versioned)

    _LOGGER.info("Chime Guard frontend module registered at %s", script_url_versioned)

    # Register WebSocket API and services globally
    async_setup_websocket(hass)
    async_setup_services(hass)

    # If chime_guard is in configuration.yaml, auto-import config entry if needed
    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=config[DOMAIN] or {},
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Chime Guard from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Setup WebSocket API and services
    async_setup_websocket(hass)
    async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(async_update_options))
    _LOGGER.info("Chime Guard integration loaded successfully (v%s)", VERSION)
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    hass.data[DOMAIN][entry.entry_id] = {**entry.data, **entry.options}
    _LOGGER.debug("Chime Guard options updated: %s", entry.options)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
