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
DEFAULT_SAMPLE_RATE: Final = 16000
DEFAULT_CHANNELS: Final = 1
DEFAULT_APP_NAME: Final = "com.android.chrome"

# Supported languages
SUPPORTED_LANGUAGES: Final = ["zh-CN", "zh"]

# Service names (if needed)
SERVICE_TRANSCRIBE: Final = "transcribe"

# Event types
EVENT_DOUBAO_STT_RESULT: Final = f"{DOMAIN}_result"
