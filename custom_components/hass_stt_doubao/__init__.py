"""The Doubao Speech-to-Text integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_CREDENTIAL_PATH,
    CONF_ENABLE_PUNCTUATION,
    DEFAULT_CREDENTIAL_PATH,
    DEFAULT_ENABLE_PUNCTUATION,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.STT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Doubao Speech-to-Text from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    _update_entry_data(hass, entry)
    
    entry.async_on_unload(
        entry.add_update_listener(_async_update_entry_listener)
    )
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("Doubao STT 集成已设置完成")
    
    return True


def _update_entry_data(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Store config from entry.options (falling back to entry.data)."""
    merged = {**entry.data, **entry.options}
    
    credential_path = merged.get(CONF_CREDENTIAL_PATH, DEFAULT_CREDENTIAL_PATH)
    enable_punctuation = merged.get(CONF_ENABLE_PUNCTUATION, DEFAULT_ENABLE_PUNCTUATION)
    
    if not Path(credential_path).is_absolute():
        credential_path = hass.config.path(credential_path)
    
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_CREDENTIAL_PATH: credential_path,
        CONF_ENABLE_PUNCTUATION: enable_punctuation,
    }


async def _async_update_entry_listener(
    hass: HomeAssistant, entry: ConfigEntry,
) -> None:
    """Handle options update."""
    _update_entry_data(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok
