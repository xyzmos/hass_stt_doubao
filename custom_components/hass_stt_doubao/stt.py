"""Support for Doubao Speech-to-Text service."""
from __future__ import annotations

import asyncio
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
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_CREDENTIAL_PATH,
    CONF_ENABLE_PUNCTUATION,
    SUPPORTED_LANGUAGES,
)
from .doubaoime_asr import ASRConfig, ASRError, DoubaoASR, ResponseType

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Doubao STT from a config entry."""
    config_data = hass.data[DOMAIN][config_entry.entry_id]
    
    async_add_entities(
        [DoubaoSTTEntity(config_entry, config_data)],
        True,
    )


class DoubaoSTTEntity(SpeechToTextEntity):
    """Doubao Speech-to-Text entity."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        config_data: dict,
    ) -> None:
        """Initialize Doubao STT entity."""
        self._config_entry = config_entry
        self._credential_path = config_data[CONF_CREDENTIAL_PATH]
        self._enable_punctuation = config_data[CONF_ENABLE_PUNCTUATION]
        self._attr_name = "Doubao STT"
        self._attr_unique_id = f"{config_entry.entry_id}_stt"

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
        
        # 创建 ASR 配置
        config = ASRConfig(
            credential_path=self._credential_path,
            enable_punctuation=self._enable_punctuation,
            sample_rate=16000,  # HA 固定使用 16kHz
            channels=1,  # HA 固定使用单声道
        )
        
        try:
            # 使用 DoubaoASR 进行实时识别
            final_text = ""
            async with DoubaoASR(config) as asr:
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
            
            _LOGGER.info("语音识别成功: %s", final_text)
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
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("处理音频流时发生未知错误")
            return SpeechResult(
                text=None,
                result=SpeechResultState.ERROR,
            )
