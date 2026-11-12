"""Config flow for Chime Guard."""
from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_SPEAKER_MAPPINGS,
    CONF_MIN_MUTE_WINDOW,
    CONF_MAX_TIMEOUT,
    CONF_EXTERNAL_TAKEOVER,
    CONF_MUTE_METHOD,
    CONF_INTERCEPT_JOIN,
    DEFAULT_MIN_MUTE_WINDOW,
    DEFAULT_MAX_TIMEOUT,
    DEFAULT_EXTERNAL_TAKEOVER,
    DEFAULT_MUTE_METHOD,
    DEFAULT_INTERCEPT_JOIN,
)

_LOGGER = logging.getLogger(__name__)


def _auto_discover_speakers(hass) -> dict[str, str]:
    """Scan entity registry for Google Cast and Music Assistant entities and pair them."""
    registry = er.async_get(hass)
    cast_entities = {}
    mass_entities = {}

    for entity in registry.entities.values():
        if entity.domain != "media_player":
            continue
        platform = entity.platform or ""
        if platform == "cast":
            cast_entities[entity.entity_id] = entity.name or entity.original_name or entity.entity_id
        elif platform in ("mass", "music_assistant"):
            mass_entities[entity.entity_id] = entity.name or entity.original_name or entity.entity_id

    # Fallback to states inspect if registry is sparse
    if not cast_entities:
        for eid in hass.states.async_entity_ids("media_player"):
            st = hass.states.get(eid)
            if not st:
                continue
            attrs = st.attributes or {}
            # Cast indicators
            if "cast_info" in attrs or "app_name" in attrs or "is_volume_muted" in attrs:
                cast_entities[eid] = attrs.get("friendly_name", eid)

    mappings: dict[str, str] = {}

    # Pair MASS with Cast by comparing names
    for mass_id, mass_name in mass_entities.items():
        mass_clean = mass_name.lower().replace("speaker", "").replace("display", "").strip()
        matched_cast = None
        for cast_id, cast_name in cast_entities.items():
            cast_clean = cast_name.lower().replace("speaker", "").replace("display", "").strip()
            if mass_clean and mass_clean in cast_clean or cast_clean in mass_clean:
                matched_cast = cast_id
                break
            if mass_id.replace("_2", "") == cast_id:
                matched_cast = cast_id
                break

        if matched_cast:
            mappings[mass_id] = matched_cast
        elif mass_id.replace("_2", "") in cast_entities:
            mappings[mass_id] = mass_id.replace("_2", "")

    # Add standalone Cast entities
    for cast_id in cast_entities:
        if cast_id not in mappings.values():
            mappings[cast_id] = cast_id

    return mappings


class ChimeGuardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Chime Guard."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            discovered = _auto_discover_speakers(self.hass)
            user_input[CONF_SPEAKER_MAPPINGS] = discovered
            return self.async_create_entry(title="Chime Guard", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_MIN_MUTE_WINDOW, default=DEFAULT_MIN_MUTE_WINDOW): vol.All(
                    cv.positive_int, vol.Range(min=800, max=4000)
                ),
                vol.Required(CONF_MAX_TIMEOUT, default=DEFAULT_MAX_TIMEOUT): vol.All(
                    cv.positive_int, vol.Range(min=5, max=30)
                ),
                vol.Required(CONF_EXTERNAL_TAKEOVER, default=DEFAULT_EXTERNAL_TAKEOVER): cv.boolean,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ChimeGuardOptionsFlow:
        """Get the options flow for this handler."""
        return ChimeGuardOptionsFlow(config_entry)


class ChimeGuardOptionsFlow(config_entries.OptionsFlow):
    """Handle Chime Guard options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # Preserve existing speaker mappings
            current_mappings = self.config_entry.data.get(CONF_SPEAKER_MAPPINGS, {})
            user_input[CONF_SPEAKER_MAPPINGS] = current_mappings
            return self.async_create_entry(title="", data=user_input)

        data = self.config_entry.data
        options = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MIN_MUTE_WINDOW,
                    default=options.get(CONF_MIN_MUTE_WINDOW, data.get(CONF_MIN_MUTE_WINDOW, DEFAULT_MIN_MUTE_WINDOW)),
                ): vol.All(cv.positive_int, vol.Range(min=800, max=4000)),
                vol.Required(
                    CONF_MAX_TIMEOUT,
                    default=options.get(CONF_MAX_TIMEOUT, data.get(CONF_MAX_TIMEOUT, DEFAULT_MAX_TIMEOUT)),
                ): vol.All(cv.positive_int, vol.Range(min=5, max=30)),
                vol.Required(
                    CONF_EXTERNAL_TAKEOVER,
                    default=options.get(CONF_EXTERNAL_TAKEOVER, data.get(CONF_EXTERNAL_TAKEOVER, DEFAULT_EXTERNAL_TAKEOVER)),
                ): cv.boolean,
                vol.Required(
                    CONF_INTERCEPT_JOIN,
                    default=options.get(CONF_INTERCEPT_JOIN, data.get(CONF_INTERCEPT_JOIN, DEFAULT_INTERCEPT_JOIN)),
                ): cv.boolean,
                vol.Required(
                    CONF_MUTE_METHOD,
                    default=options.get(CONF_MUTE_METHOD, data.get(CONF_MUTE_METHOD, DEFAULT_MUTE_METHOD)),
                ): vol.In(["volume_mute", "volume_zero"]),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
