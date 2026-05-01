from __future__ import annotations

from enum import Enum, auto
from typing import List, Optional

from pydantic import BaseModel, Field
import uuid


AudioChunk = bytes


class ResponseType(Enum):
    TASK_STARTED = auto()
    SESSION_STARTED = auto()
    SESSION_FINISHED = auto()
    VAD_START = auto()
    INTERIM_RESULT = auto()
    FINAL_RESULT = auto()
    HEARTBEAT = auto()
    ERROR = auto()
    UNKNOWN = auto()


class ASRWord(BaseModel):
    word: str
    start_time: float
    end_time: float


class OIDecodingInfo(BaseModel):
    oi_former_word_num: int = 0
    oi_latter_word_num: int = 0
    oi_words: Optional[List] = None


class ASRAlternative(BaseModel):
    text: str
    start_time: float
    end_time: float
    words: List[ASRWord] = []
    semantic_related_to_prev: Optional[bool] = None
    oi_decoding_info: Optional[OIDecodingInfo] = None


class ASRResult(BaseModel):
    text: str
    start_time: float
    end_time: float
    confidence: float = 0.0
    alternatives: List[ASRAlternative] = []
    is_interim: bool = True
    is_vad_finished: bool = False
    index: int = 0


class ASRExtra(BaseModel):
    audio_duration: Optional[int] = None
    model_avg_rtf: Optional[float] = None
    model_send_first_response: Optional[int] = None
    speech_adaptation_version: Optional[str] = None
    model_total_process_time: Optional[int] = None
    packet_number: Optional[int] = None
    vad_start: Optional[bool] = None
    req_payload: Optional[dict] = None


class ASRResponse(BaseModel):
    type: ResponseType
    text: str = ""
    is_final: bool = False
    vad_start: bool = False
    vad_finished: bool = False
    packet_number: int = -1
    error_msg: str = ""
    raw_json: Optional[dict] = None
    results: List[ASRResult] = []
    extra: Optional[ASRExtra] = None


class ASRError(Exception):
    def __init__(self, message: str, response: Optional[ASRResponse] = None) -> None:
        super().__init__(message)
        self.response = response


class _SessionState(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    final_text: str = ""
    is_finished: bool = False
    error: Optional[ASRResponse] = None
