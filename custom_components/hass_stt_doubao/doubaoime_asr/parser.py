from __future__ import annotations

import json
from typing import Optional

from .models import (
    ASRWord,
    OIDecodingInfo,
    ASRAlternative,
    ASRResult,
    ASRExtra,
    ASRResponse,
    ResponseType,
)
from .asr_pb2 import AsrResponse as AsrResponsePb


def parse_word(data: dict) -> ASRWord:
    return ASRWord(
        word=data.get("word", ""),
        start_time=data.get("start_time", 0.0),
        end_time=data.get("end_time", 0.0),
    )


def parse_oi_decoding_info(data: Optional[dict]) -> Optional[OIDecodingInfo]:
    if data is None:
        return None
    return OIDecodingInfo(
        oi_former_word_num=data.get("oi_former_word_num", 0),
        oi_latter_word_num=data.get("oi_latter_word_num", 0),
        oi_words=data.get("oi_words"),
    )


def parse_alternative(data: dict) -> ASRAlternative:
    words = [parse_word(w) for w in data.get("words", [])]
    return ASRAlternative(
        text=data.get("text", ""),
        start_time=data.get("start_time", 0.0),
        end_time=data.get("end_time", 0.0),
        words=words,
        semantic_related_to_prev=data.get("semantic_related_to_prev"),
        oi_decoding_info=parse_oi_decoding_info(data.get("oi_decoding_info")),
    )


def parse_result(data: dict) -> ASRResult:
    alternatives = [parse_alternative(a) for a in data.get("alternatives", [])]
    return ASRResult(
        text=data.get("text", ""),
        start_time=data.get("start_time", 0.0),
        end_time=data.get("end_time", 0.0),
        confidence=data.get("confidence", 0.0),
        alternatives=alternatives,
        is_interim=data.get("is_interim", True),
        is_vad_finished=data.get("is_vad_finished", False),
        index=data.get("index", 0),
    )


def parse_extra(data: dict) -> ASRExtra:
    return ASRExtra(
        audio_duration=data.get("audio_duration"),
        model_avg_rtf=data.get("model_avg_rtf"),
        model_send_first_response=data.get("model_send_first_response"),
        speech_adaptation_version=data.get("speech_adaptation_version"),
        model_total_process_time=data.get("model_total_process_time"),
        packet_number=data.get("packet_number"),
        vad_start=data.get("vad_start"),
        req_payload=data.get("req_payload"),
    )


def parse_response(data: bytes) -> ASRResponse:
    pb = AsrResponsePb()
    pb.ParseFromString(data)

    message_type = pb.message_type
    result_json = pb.result_json
    status_message = pb.status_message

    if message_type == "TaskStarted":
        return ASRResponse(type=ResponseType.TASK_STARTED)

    if message_type == "SessionStarted":
        return ASRResponse(type=ResponseType.SESSION_STARTED)

    if message_type == "SessionFinished":
        return ASRResponse(type=ResponseType.SESSION_FINISHED)

    if message_type in ("TaskFailed", "SessionFailed"):
        return ASRResponse(type=ResponseType.ERROR, error_msg=status_message)

    if not result_json:
        return ASRResponse(type=ResponseType.UNKNOWN)

    try:
        json_data = json.loads(result_json)
    except json.JSONDecodeError:
        return ASRResponse(type=ResponseType.UNKNOWN)

    results_raw = json_data.get("results")
    extra_raw = json_data.get("extra", {})

    parsed_extra = parse_extra(extra_raw)

    if results_raw is None:
        return ASRResponse(
            type=ResponseType.HEARTBEAT,
            packet_number=extra_raw.get("packet_number", -1),
            raw_json=json_data,
            extra=parsed_extra,
        )

    parsed_results = [parse_result(r) for r in results_raw]

    if extra_raw.get("vad_start"):
        return ASRResponse(
            type=ResponseType.VAD_START,
            vad_start=True,
            raw_json=json_data,
            results=parsed_results,
            extra=parsed_extra,
        )

    text = ""
    is_interim = True
    vad_finished = False

    for r in parsed_results:
        if r.text:
            text = r.text
        if not r.is_interim:
            is_interim = False
        if r.is_vad_finished:
            vad_finished = True

    nonstream_result = any(
        r.get("extra", {}).get("nonstream_result") for r in results_raw
    )

    if nonstream_result or (not is_interim and vad_finished):
        return ASRResponse(
            type=ResponseType.FINAL_RESULT,
            text=text,
            is_final=True,
            vad_finished=vad_finished,
            raw_json=json_data,
            results=parsed_results,
            extra=parsed_extra,
        )

    return ASRResponse(
        type=ResponseType.INTERIM_RESULT,
        text=text,
        is_final=False,
        raw_json=json_data,
        results=parsed_results,
        extra=parsed_extra,
    )
