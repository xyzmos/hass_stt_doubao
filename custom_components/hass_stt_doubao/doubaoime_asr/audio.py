from typing import Optional, List, Union, TYPE_CHECKING
from pathlib import Path
import asyncio

import miniaudio

from .config import ASRConfig

if TYPE_CHECKING:
    import opuslib


class AudioEncoder:
    """
    进行音频格式转换
    """
    def __init__(self, config: ASRConfig) -> None:
        self.config = config
        self._encoder: Optional["opuslib.Encoder"] = None
        self._opuslib_module = None
    
    async def _ensure_opuslib(self):
        """在 executor 中导入 opuslib，避免阻塞事件循环"""
        if self._opuslib_module is None:
            loop = asyncio.get_event_loop()
            self._opuslib_module = await loop.run_in_executor(None, self._import_opuslib)
    
    @staticmethod
    def _import_opuslib():
        """在独立线程中导入 opuslib"""
        import opuslib
        return opuslib
    
    async def get_encoder(self) -> "opuslib.Encoder":
        """异步获取编码器"""
        if self._encoder is None:
            await self._ensure_opuslib()
            self._encoder = self._opuslib_module.Encoder(
                self.config.sample_rate,
                self.config.channels,
                self._opuslib_module.APPLICATION_AUDIO,
            )
        return self._encoder
    
    async def pcm_to_opus_frames(self, pcm_data: bytes) -> List[bytes]:
        """将 PCM 数据转换为 Opus 帧（异步）"""
        encoder = await self.get_encoder()
        
        samples_per_frame = (
            self.config.sample_rate * self.config.frame_duration_ms // 1000
        )
        bytes_per_frame = samples_per_frame * 2 # 16-bit

        frames = []
        for i in range(0, len(pcm_data), bytes_per_frame):
            chunk = pcm_data[i : i + bytes_per_frame]
            if len(chunk) < bytes_per_frame:
                chunk = chunk + b"\x00" * (bytes_per_frame - len(chunk))
            
            opus_frame = encoder.encode(chunk, samples_per_frame)
            frames.append(opus_frame)
        
        return frames
    
    @staticmethod
    def convert_audio_to_pcm(
        audio_path: Union[Path, str],
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> bytes:
        decoded = miniaudio.decode_file(
            str(audio_path),
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=channels,
            sample_rate=sample_rate,
        )
        return decoded.samples.tobytes()
