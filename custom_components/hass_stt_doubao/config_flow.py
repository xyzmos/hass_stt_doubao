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
    
    Only checks that the credential file exists and is valid JSON if provided.
    Does NOT register a device or perform network I/O.
    Actual credential initialization is deferred to the first transcribe call.
    """
    import json as json_module
    
    credential_path = data.get(CONF_CREDENTIAL_PATH, DEFAULT_CREDENTIAL_PATH)
    enable_punctuation = data.get(CONF_ENABLE_PUNCTUATION, DEFAULT_ENABLE_PUNCTUATION)
    
    if not Path(credential_path).is_absolute():
        credential_path = hass.config.path(credential_path)
    
    cred_path = Path(credential_path)
    if cred_path.exists():
        try:
            cred_data = json_module.loads(cred_path.read_text(encoding="utf-8"))
            if not isinstance(cred_data, dict):
                raise CannotConnect("凭据文件格式不正确")
        except (json_module.JSONDecodeError, OSError) as err:
            raise CannotConnect(f"凭据文件读取失败: {err}") from err
    
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
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data={**self.config_entry.data, **user_input}
                )
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
