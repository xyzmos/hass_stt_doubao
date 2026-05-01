import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel

from .constants import WEBSOCKET_URL, USER_AGENT, AID
from .credential import CredentialManager
from .device import DeviceCredentials


class _AudioInfo(BaseModel):
    channel: int
    format: str
    sample_rate: int


class _SessionExtraConfig(BaseModel):
    app_name: str
    cell_compress_rate: int
    did: str
    enable_asr_threepass: bool
    enable_asr_twopass: bool
    input_mode: str


class SessionConfig(BaseModel):
    audio_info: _AudioInfo
    enable_punctuation: bool
    enable_speech_rejection: bool
    extra: _SessionExtraConfig


@dataclass
class ASRConfig:
    url: str = WEBSOCKET_URL
    aid: str = AID
    user_agent: str = USER_AGENT

    device_id: Optional[str] = None
    token: Optional[str] = None
    credential_path: Union[str, Path, None] = None

    sample_rate: int = 16000
    channels: int = 1
    frame_duration_ms: int = 20

    enable_punctuation: bool = True
    enable_speech_rejection: bool = False
    enable_asr_twopass: bool = True
    enable_asr_threepass: bool = True
    app_name: str = "com.android.chrome"

    connect_timeout: float = 10.0
    recv_timeout: float = 10.0

    _credential_manager: Optional[CredentialManager] = field(default=None, repr=False)
    _wave_client: Optional[object] = field(default=None, repr=False)

    @property
    def _cred_mgr(self) -> CredentialManager:
        if self._credential_manager is None:
            self._credential_manager = CredentialManager(
                credential_path=self.credential_path,
                device_id=self.device_id,
                token=self.token,
            )
        return self._credential_manager

    def _sync_from_mgr(self) -> None:
        self.device_id = self._cred_mgr.device_id
        self.token = self._cred_mgr.token

    def ensure_credentials(self):
        self._cred_mgr.ensure_sync()
        self._sync_from_mgr()

    async def async_ensure_credentials(self):
        await self._cred_mgr.ensure_async()
        self._sync_from_mgr()

    @property
    def ws_url(self) -> str:
        self.ensure_credentials()
        return f'{self.url}?aid={self.aid}&device_id={self.device_id}'

    async def async_ws_url(self) -> str:
        await self.async_ensure_credentials()
        return f'{self.url}?aid={self.aid}&device_id={self.device_id}'

    @property
    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "proto-version": "v2",
            "x-custom-keepalive": "true"
        }

    def session_config(self) -> SessionConfig:
        self.ensure_credentials()
        return self._build_session_config()

    async def async_session_config(self) -> SessionConfig:
        await self.async_ensure_credentials()
        return self._build_session_config()

    def _build_session_config(self) -> SessionConfig:
        audio_info = _AudioInfo(
            channel=self.channels,
            format="speech_opus",
            sample_rate=self.sample_rate,
        )
        extra = _SessionExtraConfig(
            app_name=self.app_name,
            cell_compress_rate=8,
            did=self.device_id,
            enable_asr_threepass=self.enable_asr_threepass,
            enable_asr_twopass=self.enable_asr_twopass,
            input_mode="tool",
        )

        return SessionConfig(
            audio_info=audio_info,
            enable_punctuation=self.enable_punctuation,
            enable_speech_rejection=self.enable_speech_rejection,
            extra=extra,
        )

    def get_token(self) -> str:
        self.ensure_credentials()
        return self.token

    async def async_get_token(self) -> str:
        await self.async_ensure_credentials()
        return self.token

    def _on_wave_session_update(self, session) -> None:
        mgr = self._cred_mgr
        if mgr.credentials:
            mgr.credentials.wave_session = session.to_dict()
            mgr.save_credentials_sync(mgr.credentials)

    def get_wave_client(self):
        from .wave_client import WaveClient, WaveSession

        self.ensure_credentials()
        if self._wave_client is None:
            cached_session = None
            creds = self._cred_mgr.credentials
            if creds and creds.wave_session:
                try:
                    session = WaveSession.from_dict(creds.wave_session)
                    if not session.is_expired():
                        cached_session = session
                except (KeyError, ValueError):
                    pass

            self._wave_client = WaveClient(
                self.device_id,
                self.aid,
                session=cached_session,
                on_session_update=self._on_wave_session_update,
            )
        return self._wave_client

    async def async_get_wave_client(self):
        from .wave_client import WaveClient, WaveSession

        await self.async_ensure_credentials()
        if self._wave_client is None:
            cached_session = None
            creds = self._cred_mgr.credentials
            if creds and creds.wave_session:
                try:
                    session = WaveSession.from_dict(creds.wave_session)
                    if not session.is_expired():
                        cached_session = session
                except (KeyError, ValueError):
                    pass

            self._wave_client = WaveClient(
                self.device_id,
                self.aid,
                session=cached_session,
                on_session_update=self._on_wave_session_update,
            )
        return self._wave_client

    def get_sami_token(self) -> str:
        self.ensure_credentials()
        return self._cred_mgr.get_sami_token_sync()

    async def async_get_sami_token(self) -> str:
        await self.async_ensure_credentials()
        return await self._cred_mgr.get_sami_token_async()
