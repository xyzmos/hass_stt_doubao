"""The Doubao Speech-to-Text integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CREDENTIAL_PATH,
    CONF_ENABLE_PUNCTUATION,
    DEFAULT_CREDENTIAL_PATH,
    DEFAULT_ENABLE_PUNCTUATION,
)
from .doubaoime_asr import ASRConfig

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.STT]

@dataclass
class DoubaoRuntimeData:
    """Runtime data resolved from config entry data and options."""

    credential_path: str
    enable_punctuation: bool
    asr_config: ASRConfig


type DoubaoConfigEntry = ConfigEntry[DoubaoRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: DoubaoConfigEntry) -> bool:
    """Set up Doubao Speech-to-Text from a config entry."""
    merged = {**entry.data, **entry.options}

    credential_path = merged.get(CONF_CREDENTIAL_PATH, DEFAULT_CREDENTIAL_PATH)
    if not Path(credential_path).is_absolute():
        credential_path = hass.config.path(credential_path)

    entry.runtime_data = DoubaoRuntimeData(
        credential_path=credential_path,
        enable_punctuation=merged.get(
            CONF_ENABLE_PUNCTUATION, DEFAULT_ENABLE_PUNCTUATION
        ),
        asr_config=ASRConfig(
            credential_path=credential_path,
            enable_punctuation=merged.get(
                CONF_ENABLE_PUNCTUATION, DEFAULT_ENABLE_PUNCTUATION
            ),
        ),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("Doubao STT 集成加载完成")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DoubaoConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
