from __future__ import annotations

import json

from .config import SessionConfig
from .asr_pb2 import AsrRequest, FrameState


def build_start_task(request_id: str, token: str) -> bytes:
    request = AsrRequest()
    request.token = token
    request.service_name = "ASR"
    request.method_name = "StartTask"
    request.request_id = request_id
    return request.SerializeToString()


def build_start_session(request_id: str, token: str, config: SessionConfig) -> bytes:
    request = AsrRequest()
    request.token = token
    request.service_name = "ASR"
    request.method_name = "StartSession"
    request.request_id = request_id
    request.payload = config.model_dump_json()
    return request.SerializeToString()


def build_finish_session(request_id: str, token: str) -> bytes:
    request = AsrRequest()
    request.token = token
    request.service_name = "ASR"
    request.method_name = "FinishSession"
    request.request_id = request_id
    return request.SerializeToString()


def build_asr_request(
    audio_data: bytes,
    request_id: str,
    frame_state: FrameState,
    timestamp_ms: int,
) -> bytes:
    request = AsrRequest()
    metadata = json.dumps({"extra": {}, "timestamp_ms": timestamp_ms})

    request.service_name = "ASR"
    request.method_name = "TaskRequest"
    request.payload = metadata
    request.audio_data = audio_data
    request.request_id = request_id
    request.frame_state = frame_state
    return request.SerializeToString()
