"""
SAMI 服务相关
"""

import hashlib
import time
import uuid
from typing import Optional

import requests
from pydantic import BaseModel, ConfigDict, Field

from .constants import SAMI_CONFIG_URL, SAMI_APP_KEY, USER_AGENT, APP_CONFIG, DEFAULT_DEVICE_CONFIG


class _SamiConfigParams(BaseModel):
    """
    SAMI 配置接口的 URL Params
    """
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    device_platform: str = "android"
    os: str = "android"
    ssmix: str = "a"
    rticket: str = Field(default_factory=lambda: str(int(time.time() * 1000)), serialization_alias="_rticket")
    cdid: str
    channel: str
    aid: str
    app_name: str
    version_code: str
    version_name: str
    manifest_version_code: str
    update_version_code: str
    resolution: str
    dpi: str
    device_type: str
    device_brand: str
    language: str
    os_api: str
    os_version: str
    ac: str = "wifi"
    use_olympus_account: str = Field(default="1", serialization_alias="use-olympus-account")

    @classmethod
    def default(cls, cdid: str) -> "_SamiConfigParams":
        """
        使用默认配置构建 SAMI 配置 Params
        """
        app_config = {
            **{k: APP_CONFIG[k] for k in ("channel", "app_name", "version_name")},
            "aid": str(APP_CONFIG["aid"]),
            "version_code": str(APP_CONFIG["version_code"]),
            "manifest_version_code": str(APP_CONFIG["manifest_version_code"]),
            "update_version_code": str(APP_CONFIG["update_version_code"]),
        }

        device_keys = ("device_platform", "os", "resolution", "dpi", "device_type",
                       "device_brand", "language", "os_api", "os_version")
        device_config = {k: DEFAULT_DEVICE_CONFIG[k] for k in device_keys}

        return cls(cdid=cdid, **app_config, **device_config)


class _SamiConfigRequest(BaseModel):
    """
    SAMI 配置接口的请求体
    """
    sami_app_key: str = SAMI_APP_KEY


class _SamiConfigData(BaseModel):
    """SAMI 配置数据"""
    sami_token: str


class _SamiConfigResponse(BaseModel):
    """
    SAMI 配置接口的响应
    """
    code: int
    msg: str
    data: _SamiConfigData

    @property
    def sami_token(self) -> str:
        return self.data.sami_token


def get_sami_config(cdid: str) -> requests.Response:
    """
    获取 SAMI 配置 (包含 token)

    Args:
        cdid: 客户端设备 ID

    Returns:
        响应对象
    """
    params = _SamiConfigParams.default(cdid)
    body = _SamiConfigRequest()
    body_json = body.model_dump_json()
    x_ss_stub = hashlib.md5(body_json.encode()).hexdigest().upper()

    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "app_version": APP_CONFIG["version_name"],
        "app_id": str(APP_CONFIG["aid"]),
        "os_type": "Android",
        "x-ss-stub": x_ss_stub,
    }

    response = requests.post(
        SAMI_CONFIG_URL,
        params=params.model_dump(by_alias=True),
        data=body_json,
        headers=headers,
    )

    return response


def get_sami_token(cdid: Optional[str] = None) -> str:
    """
    获取 SAMI token

    :param cdid: 客户端设备 ID，如果为 None 则自动生成
    :return: SAMI token 字符串
    """
    if cdid is None:
        cdid = str(uuid.uuid4())

    response = get_sami_config(cdid)
    response.raise_for_status()

    data = _SamiConfigResponse(**response.json())
    return data.sami_token
