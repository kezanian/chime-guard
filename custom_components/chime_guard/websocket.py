"""WebSocket API for Chime Guard."""
from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    WS_TYPE_GET_CONFIG,
    CONF_SPEAKER_MAPPINGS,
    CONF_MIN_MUTE_WINDOW,
    CONF_MAX_TIMEOUT,
    CONF_EXTERNAL_TAKEOVER,
    CONF_INTERCEPT_JOIN,
    CONF_EXCLUDED_SPEAKERS,
    DEFAULT_MIN_MUTE_WINDOW,
    DEFAULT_MAX_TIMEOUT,
    DEFAULT_EXTERNAL_TAKEOVER,
    DEFAULT_INTERCEPT_JOIN,
    KNOWN_MA_APPS,
)

_LOGGER = logging.getLogger(__name__)


def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register Chime Guard WebSocket commands."""
    try:
        websocket_api.async_register_command(hass, ws_get_config)
    except Exception:
        pass


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_GET_CONFIG,
    }
)
@websocket_api.async_response
async def ws_get_config(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the active Chime Guard configuration to frontend clients."""
    config_entry = None
    entries = hass.config_entries.async_entries(DOMAIN)
    if entries:
        config_entry = entries[0]

    options = config_entry.options if config_entry else {}
    data = config_entry.data if config_entry else {}

    # Merge data and options (options override data)
    merged = {**data, **options}

    mappings = merged.get(CONF_SPEAKER_MAPPINGS, {})
    min_mute = merged.get(CONF_MIN_MUTE_WINDOW, DEFAULT_MIN_MUTE_WINDOW)
    max_timeout = merged.get(CONF_MAX_TIMEOUT, DEFAULT_MAX_TIMEOUT)
    external_takeover = merged.get(CONF_EXTERNAL_TAKEOVER, DEFAULT_EXTERNAL_TAKEOVER)
    intercept_join = merged.get(CONF_INTERCEPT_JOIN, DEFAULT_INTERCEPT_JOIN)
    excluded = merged.get(CONF_EXCLUDED_SPEAKERS, [])

    connection.send_result(
        msg["id"],
        {
            "mappings": mappings,
            "min_mute_window": min_mute,
            "max_timeout": max_timeout,
            "external_takeover": external_takeover,
            "intercept_join": intercept_join,
            "excluded_speakers": excluded,
            "known_ma_apps": KNOWN_MA_APPS,
        },
    )
