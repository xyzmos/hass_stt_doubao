from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from .device import DeviceCredentials, register_device, get_asr_token
from .sami import get_sami_token


def _jwt_is_expired(token: str, margin: int = 60) -> bool:
    import base64
    import time
    try:
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp")
        if exp is None:
            return False
        return time.time() >= exp - margin
    except (IndexError, ValueError, json.JSONDecodeError):
        return False


class CredentialManager:
    """Manages device credentials: loading, saving, registration, and token refresh."""

    def __init__(
        self,
        credential_path: Optional[str | Path] = None,
        device_id: Optional[str] = None,
        token: Optional[str] = None,
    ) -> None:
        self.credential_path = credential_path
        self.device_id = device_id
        self.token = token
        self._credentials: Optional[DeviceCredentials] = None
        self._initialized = False

    def _load_sync(self) -> Optional[DeviceCredentials]:
        if self.credential_path is None:
            return None
        path = Path(self.credential_path).expanduser()
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
                return DeviceCredentials(**data)
        except (json.JSONDecodeError, OSError):
            return None

    def _save_sync(self, creds: DeviceCredentials) -> None:
        if self.credential_path is None:
            return
        path = Path(self.credential_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(creds.model_dump(), f, indent=2, ensure_ascii=False)

    async def _load_async(self) -> Optional[DeviceCredentials]:
        return await asyncio.to_thread(self._load_sync)

    async def _save_async(self, creds: DeviceCredentials) -> None:
        await asyncio.to_thread(self._save_sync, creds)

    @property
    def credentials(self) -> Optional[DeviceCredentials]:
        return self._credentials

    def ensure(self, *, is_async: bool = False) -> None:
        """Core credential initialization logic.

        When *is_async* is True the caller is expected to have already
        arranged for I/O to happen off the event loop (the sync helper
        methods are called from ``asyncio.to_thread`` by the async
        wrappers).  For simplicity the sync/async split is handled by
        ``ensure_sync`` / ``ensure_async`` below.
        """
        raise NotImplementedError  # pragma: no cover – dispatched below

    def ensure_sync(self) -> None:
        if self._initialized:
            return

        user_device_id = self.device_id
        user_token = self.token

        file_creds = self._load_sync()
        if file_creds:
            self._credentials = file_creds
            if self.device_id is None:
                self.device_id = file_creds.device_id
            if self.token is None:
                self.token = file_creds.token

        need_save = False
        if self.device_id is None:
            self._credentials = register_device()
            self.device_id = self._credentials.device_id
            need_save = True

        if self.token is None:
            cdid = self._credentials.cdid if self._credentials else None
            self.token = get_asr_token(self.device_id, cdid)

        if self.credential_path and need_save and self._credentials:
            self._credentials.token = self.token
            self._save_sync(self._credentials)

        if user_device_id is not None:
            self.device_id = user_device_id
        if user_token is not None:
            self.token = user_token

        self._initialized = True

    async def ensure_async(self) -> None:
        if self._initialized:
            return

        user_device_id = self.device_id
        user_token = self.token

        file_creds = await self._load_async()
        if file_creds:
            self._credentials = file_creds
            if self.device_id is None:
                self.device_id = file_creds.device_id
            if self.token is None:
                self.token = file_creds.token

        need_save = False
        if self.device_id is None:
            self._credentials = await asyncio.to_thread(register_device)
            self.device_id = self._credentials.device_id
            need_save = True

        if self.token is None:
            cdid = self._credentials.cdid if self._credentials else None
            self.token = await asyncio.to_thread(get_asr_token, self.device_id, cdid)

        if self.credential_path and need_save and self._credentials:
            self._credentials.token = self.token
            await self._save_async(self._credentials)

        if user_device_id is not None:
            self.device_id = user_device_id
        if user_token is not None:
            self.token = user_token

        self._initialized = True

    def save_credentials_sync(self, creds: DeviceCredentials) -> None:
        self._credentials = creds
        self._save_sync(creds)

    async def save_credentials_async(self, creds: DeviceCredentials) -> None:
        self._credentials = creds
        await self._save_async(creds)

    def get_sami_token_sync(self) -> str:
        self.ensure_sync()
        if (self._credentials
                and self._credentials.sami_token
                and not _jwt_is_expired(self._credentials.sami_token)):
            return self._credentials.sami_token

        cdid = self._credentials.cdid if self._credentials else None
        sami_token = get_sami_token(cdid)

        if self._credentials:
            self._credentials.sami_token = sami_token
            self._save_sync(self._credentials)

        return sami_token

    async def get_sami_token_async(self) -> str:
        await self.ensure_async()
        if (self._credentials
                and self._credentials.sami_token
                and not _jwt_is_expired(self._credentials.sami_token)):
            return self._credentials.sami_token

        cdid = self._credentials.cdid if self._credentials else None
        sami_token = await asyncio.to_thread(get_sami_token, cdid)

        if self._credentials:
            self._credentials.sami_token = sami_token
            await self._save_async(self._credentials)

        return sami_token
