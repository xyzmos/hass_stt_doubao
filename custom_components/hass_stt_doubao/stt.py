"""Support for Doubao Speech-to-Text service."""
from __future__ import annotations

import logging
from typing import AsyncIterable

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
    SpeechToTextEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DoubaoConfigEntry
from .const import DOMAIN, SUPPORTED_LANGUAGES
from .doubaoime_asr import ASRError, DoubaoASR, ResponseType

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DoubaoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Doubao STT from a config entry."""
    async_add_entities([DoubaoSTTEntity(config_entry)])


class DoubaoSTTEntity(SpeechToTextEntity):
    """Doubao Speech-to-Text entity."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, config_entry: DoubaoConfigEntry) -> None:
        """Initialize Doubao STT entity."""
        self._asr_config = config_entry.runtime_data.asr_config
        self._attr_unique_id = config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        return SUPPORTED_LANGUAGES

    @property
    def supported_formats(self) -> list[AudioFormats]:
        """Return a list of supported formats."""
        return [AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        """Return a list of supported codecs."""
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        """Return a list of supported bit rates."""
        return [AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        """Return a list of supported sample rates."""
        return [AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        """Return a list of supported channels."""
        return [AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> SpeechResult:
        """Process an audio stream to STT service.

        Args:
            metadata: Metadata about the audio stream
            stream: Async iterable of audio chunks (PCM 16-bit, 16kHz, mono)

        Returns:
            SpeechResult with the transcribed text
        """
        _LOGGER.debug(
            "开始处理音频流: language=%s, format=%s, codec=%s, sample_rate=%s",
            metadata.language,
            metadata.format,
            metadata.codec,
            metadata.sample_rate,
        )

        try:
            final_text = ""
            async with DoubaoASR(self._asr_config) as asr:
                async for response in asr.transcribe_realtime(stream):
                    if response.type == ResponseType.FINAL_RESULT:
                        final_text = response.text
                        _LOGGER.debug("收到最终识别结果: %s", final_text)
                    elif response.type == ResponseType.INTERIM_RESULT:
                        _LOGGER.debug("收到中间识别结果: %s", response.text)
                    elif response.type == ResponseType.ERROR:
                        _LOGGER.error("识别过程出错: %s", response.error_msg)
                        return SpeechResult(
                            text=None,
                            result=SpeechResultState.ERROR,
                        )

            if not final_text:
                _LOGGER.warning("识别完成但未获得最终结果")
                return SpeechResult(
                    text=None,
                    result=SpeechResultState.ERROR,
                )

            _LOGGER.debug("语音识别成功: %s", final_text)
            return SpeechResult(
                text=final_text,
                result=SpeechResultState.SUCCESS,
            )

        except ASRError as err:
            _LOGGER.error("Doubao ASR 识别失败: %s", err)
            return SpeechResult(
                text=None,
                result=SpeechResultState.ERROR,
            )
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("处理音频流时发生未知错误")
            return SpeechResult(
                text=None,
                result=SpeechResultState.ERROR,
            )
