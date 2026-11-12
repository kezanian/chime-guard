"""Services for Chime Guard."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_SPEAKER_MAPPINGS,
    CONF_MIN_MUTE_WINDOW,
    CONF_MAX_TIMEOUT,
    DEFAULT_MIN_MUTE_WINDOW,
    DEFAULT_MAX_TIMEOUT,
    KNOWN_MA_APPS,
)

_LOGGER = logging.getLogger(__name__)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register Chime Guard services."""
    if hass.services.has_service(DOMAIN, "silent_play"):
        return

    async def handle_silent_play(call: ServiceCall) -> None:
        """Play media on a target speaker while suppressing the connect chime."""
        target_entity = call.data.get(ATTR_ENTITY_ID)
        media_id = call.data.get("media_content_id")
        media_type = call.data.get("media_content_type", "music")
        extra = call.data.get("extra", {})

        if not target_entity:
            raise HomeAssistantError("Missing entity_id for silent_play")

        # Resolve target to underlying physical Cast device
        entries = hass.config_entries.async_entries(DOMAIN)
        entry = entries[0] if entries else None
        merged = {**(entry.data if entry else {}), **(entry.options if entry else {})}
        mappings = merged.get(CONF_SPEAKER_MAPPINGS, {})
        min_mute_ms = merged.get(CONF_MIN_MUTE_WINDOW, DEFAULT_MIN_MUTE_WINDOW)
        max_timeout_s = merged.get(CONF_MAX_TIMEOUT, DEFAULT_MAX_TIMEOUT)

        cast_entity = mappings.get(target_entity, target_entity)

        # Check if cold start or external app takeover
        cast_state = hass.states.get(cast_entity)
        cast_st_val = cast_state.state if cast_state else ""
        cast_app = (cast_state.attributes.get("app_name") or "") if cast_state else ""
        cast_app_lower = cast_app.lower()

        is_ma = any(k in cast_app_lower for k in KNOWN_MA_APPS)
        needs_mute = (cast_st_val not in ["playing", "paused"]) or (not is_ma)

        if needs_mute:
            _LOGGER.debug("Muting %s for silent_play (connect chime absorption)", cast_entity)
            await hass.services.async_call(
                "media_player",
                "volume_mute",
                {"entity_id": cast_entity, "is_volume_muted": True},
                blocking=True,
            )

        # Fire media_player.play_media on the original target (e.g. MASS or Cast)
        play_data = {
            "entity_id": target_entity,
            "media_content_id": media_id,
            "media_content_type": media_type,
            **extra,
        }
        await hass.services.async_call("media_player", "play_media", play_data, blocking=False)

        if needs_mute:
            async def _unmute_task():
                start_time = time.time()
                min_mute_sec = min_mute_ms / 1000.0
                deadline = start_time + max_timeout_s

                # Initial delay matching min mute window
                await asyncio.sleep(min_mute_sec)

                while time.time() < deadline:
                    cur_st = hass.states.get(cast_entity)
                    if cur_st and cur_st.state == "playing":
                        break
                    await asyncio.sleep(0.25)

                _LOGGER.debug("Unmuting %s after chime window", cast_entity)
                await hass.services.async_call(
                    "media_player",
                    "volume_mute",
                    {"entity_id": cast_entity, "is_volume_muted": False},
                    blocking=True,
                )

            hass.async_create_task(_unmute_task())

    hass.services.async_register(DOMAIN, "silent_play", handle_silent_play)
    hass.services.async_register(DOMAIN, "play_media", handle_silent_play)
