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
    
    # 获取配置
    credential_path = entry.data.get(CONF_CREDENTIAL_PATH, DEFAULT_CREDENTIAL_PATH)
    enable_punctuation = entry.data.get(CONF_ENABLE_PUNCTUATION, DEFAULT_ENABLE_PUNCTUATION)
    
    # 将相对路径转换为绝对路径
    if not Path(credential_path).is_absolute():
        credential_path = hass.config.path(credential_path)
    
    # 存储配置供 STT 实体使用
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_CREDENTIAL_PATH: credential_path,
        CONF_ENABLE_PUNCTUATION: enable_punctuation,
    }
    
    # 加载 STT 平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("Doubao STT 集成已设置完成")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok
