"""Config flow for Doubao Speech-to-Text integration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_CREDENTIAL_PATH,
    CONF_ENABLE_PUNCTUATION,
    DEFAULT_CREDENTIAL_PATH,
    DEFAULT_ENABLE_PUNCTUATION,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.
    
    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    from .doubaoime_asr import ASRConfig, DoubaoASR, ASRError
    
    credential_path = data.get(CONF_CREDENTIAL_PATH, DEFAULT_CREDENTIAL_PATH)
    enable_punctuation = data.get(CONF_ENABLE_PUNCTUATION, DEFAULT_ENABLE_PUNCTUATION)
    
    # 将相对路径转换为 Home Assistant 配置目录下的绝对路径
    if not Path(credential_path).is_absolute():
        credential_path = hass.config.path(credential_path)
    
    # 尝试初始化配置并验证凭据
    try:
        config = ASRConfig(
            credential_path=credential_path,
            enable_punctuation=enable_punctuation,
        )
        # 确保凭据已初始化（会自动注册设备如果需要）
        await config.async_ensure_credentials()
        
        # 简单验证：检查是否成功获取了 device_id 和 token
        if not config.device_id or not config.token:
            raise CannotConnect("无法获取设备凭据")
            
    except ASRError as err:
        _LOGGER.error("验证 Doubao STT 配置失败: %s", err)
        raise CannotConnect(str(err)) from err
    except Exception as err:
        _LOGGER.exception("验证 Doubao STT 配置时发生未知错误")
        raise CannotConnect(str(err)) from err
    
    # 返回用户可读的标题信息
    return {
        "title": "Doubao STT",
        "credential_path": credential_path,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Doubao Speech-to-Text."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        # 显示配置表单
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_CREDENTIAL_PATH,
                    default=DEFAULT_CREDENTIAL_PATH,
                ): str,
                vol.Optional(
                    CONF_ENABLE_PUNCTUATION,
                    default=DEFAULT_ENABLE_PUNCTUATION,
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Doubao STT."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # 验证新的配置
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        # 获取当前配置值
        current_credential_path = self.config_entry.data.get(
            CONF_CREDENTIAL_PATH, DEFAULT_CREDENTIAL_PATH
        )
        current_enable_punctuation = self.config_entry.data.get(
            CONF_ENABLE_PUNCTUATION, DEFAULT_ENABLE_PUNCTUATION
        )

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_CREDENTIAL_PATH,
                    default=current_credential_path,
                ): str,
                vol.Optional(
                    CONF_ENABLE_PUNCTUATION,
                    default=current_enable_punctuation,
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
