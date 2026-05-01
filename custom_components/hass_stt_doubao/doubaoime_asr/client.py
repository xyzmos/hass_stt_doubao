from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import ssl
import time
from typing import AsyncIterator, Callable, List, Optional, Union

import websockets
from websockets import ClientConnection

from .config import ASRConfig
from .audio import AudioEncoder
from .models import (
    ASRResponse,
    ASRError,
    AudioChunk,
    ResponseType,
    _SessionState,
)
from .parser import parse_response as _parse_response
from .protocol import (
    build_start_task as _build_start_task,
    build_start_session as _build_start_session,
    build_finish_session as _build_finish_session,
    build_asr_request as _build_asr_request,
)
from .asr_pb2 import FrameState

_LOGGER = logging.getLogger(__name__)


class DoubaoASR:
    def __init__(self, config: Optional[ASRConfig] = None):
        self.config = config
        self._encoder = AudioEncoder(self.config)
        self._ssl_context: Optional[ssl.SSLContext] = None

    async def __aenter__(self) -> DoubaoASR:
        self._ssl_context = await asyncio.to_thread(ssl.create_default_context)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    async def _run_ws_session(
        self,
        send_coroutine,
        recv_timeout: Optional[float] = None,
    ) -> AsyncIterator[ASRResponse]:
        state = _SessionState()
        ws_url = await self.config.async_ws_url()

        try:
            async with websockets.connect(
                ws_url,
                additional_headers=self.config.headers,
                open_timeout=self.config.connect_timeout,
                ssl=self._ssl_context,
            ) as ws:
                async for resp in self._initialize_session(ws, state):
                    yield resp

                response_queue: asyncio.Queue[Optional[ASRResponse]] = asyncio.Queue()

                async def _send():
                    await send_coroutine(ws, state)

                async def _recv():
                    await self._receive_responses(ws, state, response_queue)

                send_task = asyncio.create_task(_send())
                recv_task = asyncio.create_task(_recv())

                try:
                    while True:
                        try:
                            if recv_timeout is not None:
                                resp = await asyncio.wait_for(
                                    response_queue.get(), timeout=recv_timeout,
                                )
                            else:
                                resp = await response_queue.get()

                            if resp is None:
                                break

                            if resp.type == ResponseType.HEARTBEAT:
                                continue

                            yield resp
                            if resp.type == ResponseType.ERROR:
                                break

                        except asyncio.TimeoutError:
                            break
                finally:
                    results = await asyncio.gather(
                        send_task, recv_task, return_exceptions=True,
                    )
                    for r in results:
                        if isinstance(r, BaseException) and not isinstance(r, asyncio.CancelledError):
                            _LOGGER.debug("WS task exception: %s", r)

        except websockets.exceptions.WebSocketException as e:
            raise ASRError(f"WebSocket 错误: {e}") from e

    async def transcribe(self, audio: Union[str, Path, bytes], *, realtime=False, on_interim: Callable[[str], None] = None) -> str:
        final_text = ""
        async for response in self.transcribe_stream(audio, realtime=realtime):
            if response.type == ResponseType.INTERIM_RESULT and on_interim:
                on_interim(response.text)
            elif response.type == ResponseType.FINAL_RESULT:
                final_text = response.text
            elif response.type == ResponseType.ERROR:
                raise ASRError(response.error_msg, response)
        return final_text

    async def transcribe_stream(self, audio: Union[str, Path, bytes], *, realtime: bool = False) -> AsyncIterator[ASRResponse]:
        if isinstance(audio, (str, Path)):
            pcm_data = self._encoder.convert_audio_to_pcm(
                audio, self.config.sample_rate, self.config.channels,
            )
        else:
            pcm_data = audio

        opus_frames = self._encoder.pcm_to_opus_frames(pcm_data)

        async def _send(ws, state):
            await self._send_audio(ws, opus_frames, state, realtime)

        async for resp in self._run_ws_session(
            _send, recv_timeout=self.config.recv_timeout,
        ):
            yield resp

    async def transcribe_realtime(
        self,
        audio_source: AsyncIterator[AudioChunk],
    ) -> AsyncIterator[ASRResponse]:
        async def _send(ws, state):
            await self._send_audio_realtime(ws, audio_source, state)

        async for resp in self._run_ws_session(_send, recv_timeout=None):
            yield resp

    async def _send_audio_realtime(
        self,
        ws: ClientConnection,
        audio_source: AsyncIterator[AudioChunk],
        state: _SessionState,
    ):
        timestamp_ms = int(time.time() * 1000)
        frame_index = 0
        pcm_buffer = b""

        samples_per_frame = (
            self.config.sample_rate * self.config.frame_duration_ms // 1000
        )
        bytes_per_frame = samples_per_frame * 2

        async for chunk in audio_source:
            if state.is_finished:
                break

            pcm_buffer += chunk

            while len(pcm_buffer) >= bytes_per_frame:
                pcm_frame = pcm_buffer[:bytes_per_frame]
                pcm_buffer = pcm_buffer[bytes_per_frame:]

                opus_frame = self._encoder.encoder.encode(pcm_frame, samples_per_frame)

                if frame_index == 0:
                    frame_state = FrameState.FRAME_STATE_FIRST
                else:
                    frame_state = FrameState.FRAME_STATE_MIDDLE

                msg = _build_asr_request(
                    opus_frame,
                    state.request_id,
                    frame_state,
                    timestamp_ms + frame_index * self.config.frame_duration_ms,
                )
                await ws.send(msg)
                frame_index += 1

        if pcm_buffer and not state.is_finished:
            if len(pcm_buffer) < bytes_per_frame:
                pcm_buffer += b"\x00" * (bytes_per_frame - len(pcm_buffer))

            opus_frame = self._encoder.encoder.encode(pcm_buffer, samples_per_frame)

            msg = _build_asr_request(
                opus_frame,
                state.request_id,
                FrameState.FRAME_STATE_LAST,
                timestamp_ms + frame_index * self.config.frame_duration_ms,
            )
            await ws.send(msg)
        elif frame_index > 0 and not state.is_finished:
            silent_frame = b"\x00" * bytes_per_frame
            opus_frame = self._encoder.encoder.encode(silent_frame, samples_per_frame)

            msg = _build_asr_request(
                opus_frame,
                state.request_id,
                FrameState.FRAME_STATE_LAST,
                timestamp_ms + frame_index * self.config.frame_duration_ms,
            )
            await ws.send(msg)

        if not state.is_finished:
            token = await self.config.async_get_token()
            await ws.send(_build_finish_session(state.request_id, token))

    async def _initialize_session(self, ws: ClientConnection, state: _SessionState) -> AsyncIterator[ASRResponse]:
        token = await self.config.async_get_token()

        await ws.send(_build_start_task(state.request_id, token))
        resp = await ws.recv()
        parsed = _parse_response(resp)
        if parsed.type == ResponseType.ERROR:
            raise ASRError(f'StartTask 失败：{parsed.error_msg}', parsed)
        yield parsed

        session_cfg = await self.config.async_session_config()
        await ws.send(
            _build_start_session(state.request_id, token, session_cfg)
        )
        resp = await ws.recv()
        parsed = _parse_response(resp)
        if parsed.type == ResponseType.ERROR:
            raise ASRError(f'StartSession 失败：{parsed.error_msg}', parsed)
        yield parsed

    async def _send_audio(
        self,
        ws: ClientConnection,
        opus_frames: List[bytes],
        state: _SessionState,
        realtime: bool,
    ):
        timestamp_ms = int(time.time() * 1000)
        frame_interval = self.config.frame_duration_ms / 1000.0

        for i, opus_frame in enumerate(opus_frames):
            if state.is_finished:
                break

            if i == 0:
                frame_state = FrameState.FRAME_STATE_FIRST
            elif i == len(opus_frames) - 1:
                frame_state = FrameState.FRAME_STATE_LAST
            else:
                frame_state = FrameState.FRAME_STATE_MIDDLE

            msg = _build_asr_request(
                opus_frame,
                state.request_id,
                frame_state,
                timestamp_ms + i * self.config.frame_duration_ms,
            )
            await ws.send(msg)

            if realtime:
                await asyncio.sleep(frame_interval)

        token = await self.config.async_get_token()
        await ws.send(_build_finish_session(state.request_id, token))

    async def _receive_responses(
        self,
        ws: ClientConnection,
        state: _SessionState,
        queue: asyncio.Queue[Optional[ASRResponse]],
    ):
        try:
            while not state.is_finished:
                response = await ws.recv()
                resp = _parse_response(response)

                if resp.type == ResponseType.ERROR:
                    state.error = resp
                    state.is_finished = True
                    await queue.put(resp)
                    break
                elif resp.type == ResponseType.HEARTBEAT:
                    await queue.put(resp)
                elif resp.type == ResponseType.SESSION_FINISHED:
                    state.is_finished = True
                    await queue.put(resp)
                    break
                elif resp.type == ResponseType.FINAL_RESULT:
                    state.final_text = resp.text
                    await queue.put(resp)
                else:
                    await queue.put(resp)

        except websockets.exceptions.ConnectionClosed as exc:
            state.is_finished = True
            await queue.put(ASRResponse(
                type=ResponseType.ERROR,
                error_msg=f"WebSocket 连接已关闭: {exc}",
            ))
        finally:
            await queue.put(None)


async def transcribe(
    audio: str | Path | bytes,
    *,
    config: ASRConfig | None = None,
    on_interim: Callable[[str], None] | None = None,
    realtime: bool = False,
) -> str:
    async with DoubaoASR(config) as asr:
        return await asr.transcribe(audio, on_interim=on_interim, realtime=realtime)


async def transcribe_stream(
    audio: str | Path | bytes,
    *,
    config: ASRConfig | None = None,
    realtime: bool = False,
) -> AsyncIterator[ASRResponse]:
    async with DoubaoASR(config) as asr:
        async for resp in asr.transcribe_stream(audio, realtime=realtime):
            yield resp


async def transcribe_realtime(
    audio_source: AsyncIterator[AudioChunk],
    *,
    config: ASRConfig | None = None,
) -> AsyncIterator[ASRResponse]:
    async with DoubaoASR(config) as asr:
        async for resp in asr.transcribe_realtime(audio_source):
            yield resp
