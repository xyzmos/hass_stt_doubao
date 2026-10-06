"""Config flow for Doubao Speech-to-Text integration."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_CREDENTIAL_PATH,
    CONF_ENABLE_PUNCTUATION,
    DEFAULT_CREDENTIAL_PATH,
    DEFAULT_ENABLE_PUNCTUATION,
)

_LOGGER = logging.getLogger(__name__)


def _validate_credential_file(credential_path: str) -> None:
    """Check that the credential file, if present, is a valid JSON object."""
    cred_path = Path(credential_path)
    if not cred_path.exists():
        return
    try:
        if not isinstance(json.loads(cred_path.read_text(encoding="utf-8")), dict):
            raise InvalidCredentialFile("凭据文件必须是 JSON 对象")
    except json.JSONDecodeError as err:
        raise InvalidCredentialFile(f"凭据文件不是有效的 JSON: {err}") from err
    except OSError as err:
        raise InvalidCredentialFile(f"凭据文件读取失败: {err}") from err


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input.

    Only checks that the credential file exists and is valid JSON if provided.
    Does NOT register a device or perform network I/O; actual credential
    initialization is deferred to the first transcribe call.
    """
    credential_path = data.get(CONF_CREDENTIAL_PATH, DEFAULT_CREDENTIAL_PATH)
    if not Path(credential_path).is_absolute():
        credential_path = hass.config.path(credential_path)

    await hass.async_add_executor_job(_validate_credential_file, credential_path)


def _options_schema() -> vol.Schema:
    return vol.Schema(
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


class DoubaoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Doubao Speech-to-Text."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except InvalidCredentialFile:
                errors["base"] = "invalid_credential_file"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="豆包语音识别",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _options_schema(), user_input
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DoubaoOptionsFlowHandler()


class DoubaoOptionsFlowHandler(OptionsFlowWithReload):
    """Handle options flow for Doubao STT.

    OptionsFlowWithReload automatically reloads the config entry after the
    options change so the STT entity picks up the new settings.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except InvalidCredentialFile:
                errors["base"] = "invalid_credential_file"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _options_schema(),
                {**self.config_entry.data, **self.config_entry.options},
            ),
            errors=errors,
        )


class InvalidCredentialFile(HomeAssistantError):
    """Error to indicate the credential file is invalid."""
