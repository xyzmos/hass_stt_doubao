from __future__ import annotations

import base64
import json
import uuid
from typing import TYPE_CHECKING, List

import requests
from pydantic import BaseModel, Field

from .wave_client import WaveClient
from .constants import AID, APP_CONFIG, NER_URL, SAMI_APP_KEY

if TYPE_CHECKING:
    from .config import ASRConfig


class NerUserInfo(BaseModel):
    uid: str = "0"
    did: str
    app_name: str
    app_version: str
    sdk_version: str = ""
    platform: str = "android"
    experience_improve: bool = False

    @classmethod
    def new(cls, did: str, app_name: str):
        app_version = APP_CONFIG.get("version_name", "")
        return cls(did=did, app_name=app_name, app_version=app_version)


class NerRequest(BaseModel):
    """
    ner 接口请求体
    """
    user: NerUserInfo
    text: str
    additions: dict = Field(default_factory=dict)

    @classmethod
    def new(cls, text: str, did: str, app_name: str = "", addiction: dict = None):
        return cls(user=NerUserInfo.new(did, app_name), text=text, additions=addiction or {})


class NerWord(BaseModel):
    freq: int
    word: str


class NerResult(BaseModel):
    text: str
    words: List[NerWord]


class NerResponse(BaseModel):
    """
    ner 接口响应体
    """
    results: List[NerResult]


def get_ner_results(wave_client: WaveClient, sami_token: str, text: str, did: str, app_name: str = "") -> NerResponse:
    """
    调用 ner 接口获取结果
    """
    request = NerRequest.new(text, did, app_name)

    headers = {
        'app_version': APP_CONFIG.get('version_name', ''),
        'app_id': str(AID),
        'os_type': 'android',
        'x-api-resource-id': 'asr.user.context',
        'x-api-app-key': SAMI_APP_KEY,
        'x-api-token': sami_token,
        'x-api-request-id': str(uuid.uuid4()),
    }
    req_data = request.model_dump_json().encode()

    payload, headers = wave_client.prepare_request(req_data, headers)

    response = requests.post(NER_URL, data=payload, headers=headers)

    resp_headers = response.headers
    nonce = base64.b64decode(resp_headers.get('x-tt-e-p'))

    decoded = wave_client.decrypt(response.content, nonce=nonce)

    return NerResponse(**json.loads(decoded.decode()))


def ner(config: ASRConfig, text: str, app_name: str = "") -> NerResponse:
    """
    通过 ASRConfig 调用 NER 接口（同步便捷函数）

    自动管理 WaveClient、sami_token 和 device_id。

    :param config: ASR 配置（会自动初始化凭据）
    :param text: 需要进行 NER 的文本
    :param app_name: 应用名称（可选），可能会根据不同应用的使用场景适配不同的识别策略？"
    :return: NER 响应
    """
    config.ensure_credentials()
    wave_client = config.get_wave_client()
    sami_token = config.get_sami_token()
    return get_ner_results(wave_client, sami_token, text, config.device_id, app_name)


async def async_ner(config: ASRConfig, text: str, app_name: str = "") -> NerResponse:
    """
    通过 ASRConfig 调用 NER 接口（异步便捷函数，不阻塞事件循环）

    自动管理 WaveClient、sami_token 和 device_id。

    :param config: ASR 配置（会自动初始化凭据）
    :param text: 需要进行 NER 的文本
    :param app_name: 应用名称（可选）
    :return: NER 响应
    """
    import asyncio
    await config.async_ensure_credentials()
    wave_client = await config.async_get_wave_client()
    sami_token = await config.async_get_sami_token()
    return await asyncio.to_thread(
        get_ner_results, wave_client, sami_token, text, config.device_id, app_name
    )
