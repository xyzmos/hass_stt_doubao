"""Constants for the Doubao Speech-to-Text integration."""

from typing import Final

# Integration domain
DOMAIN: Final = "hass_stt_doubao"

# Configuration keys
CONF_CREDENTIAL_PATH: Final = "credential_path"
CONF_ENABLE_PUNCTUATION: Final = "enable_punctuation"

# Default values
DEFAULT_CREDENTIAL_PATH: Final = "doubao_credentials.json"
DEFAULT_ENABLE_PUNCTUATION: Final = True

# Supported languages
SUPPORTED_LANGUAGES: Final = ["zh-CN", "zh"]
