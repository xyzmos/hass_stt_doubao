"""
ByteDance Wave 加密协议客户端
"""

import base64
import hashlib
import secrets
import time
from typing import Callable, Optional, Union

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pydantic import BaseModel

from .constants import HANDSHAKE_URL, HKDF_INFO, USER_AGENT


class _KeyShare(BaseModel):
    """
    密钥交换信息
    """
    curve: str
    pubkey: str


class _HandshakeRequest(BaseModel):
    """
    握手请求
    """
    version: int = 2
    random: str
    app_id: str
    did: str
    key_shares: list[_KeyShare]
    cipher_suites: list[int] = [4097]  # ChaCha20


class _HandshakeResponse(BaseModel):
    """
    握手响应
    """
    version: int
    random: str
    key_share: _KeyShare
    cipher_suite: int
    cert: str
    ticket: str
    ticket_exp: int
    ticket_long: str
    ticket_long_exp: int


class WaveSession(BaseModel):
    """
    Wave 加密会话
    """
    ticket: str
    ticket_long: str
    encryption_key: bytes
    client_random: bytes
    server_random: bytes
    shared_key: bytes
    ticket_exp: int
    ticket_long_exp: int
    expires_at: float

    class Config:
        arbitrary_types_allowed = True

    def is_expired(self) -> bool:
        """检查会话是否已过期"""
        return time.time() >= self.expires_at

    def to_dict(self) -> dict:
        """序列化为可 JSON 存储的 dict（bytes 字段用 base64 编码）"""
        return {
            "ticket": self.ticket,
            "ticket_long": self.ticket_long,
            "encryption_key": base64.b64encode(self.encryption_key).decode(),
            "client_random": base64.b64encode(self.client_random).decode(),
            "server_random": base64.b64encode(self.server_random).decode(),
            "shared_key": base64.b64encode(self.shared_key).decode(),
            "ticket_exp": self.ticket_exp,
            "ticket_long_exp": self.ticket_long_exp,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WaveSession":
        """从 dict 反序列化（base64 解码 bytes 字段）"""
        return cls(
            ticket=data["ticket"],
            ticket_long=data["ticket_long"],
            encryption_key=base64.b64decode(data["encryption_key"]),
            client_random=base64.b64decode(data["client_random"]),
            server_random=base64.b64decode(data["server_random"]),
            shared_key=base64.b64decode(data["shared_key"]),
            ticket_exp=data["ticket_exp"],
            ticket_long_exp=data["ticket_long_exp"],
            expires_at=data["expires_at"],
        )


class WaveClient:
    """
    Wave 协议客户端
    """

    def __init__(
        self,
        device_id: str,
        app_id: Union[str, int],
        session: Optional[WaveSession] = None,
        on_session_update: Optional[Callable[[WaveSession], None]] = None,
    ):
        self.device_id = device_id
        self.app_id = str(app_id)
        self.session = session
        self._on_session_update = on_session_update

    @staticmethod
    def _chacha20_crypt(key: bytes, nonce: bytes, data: bytes) -> bytes:
        """ChaCha20 加密/解密"""
        if len(nonce) == 12:
            nonce_16 = b'\x00\x00\x00\x00' + nonce
        else:
            nonce_16 = nonce
        cipher = Cipher(algorithms.ChaCha20(key, nonce_16), mode=None, backend=default_backend())
        encryptor = cipher.encryptor()
        return encryptor.update(data) + encryptor.finalize()

    @staticmethod
    def _derive_key(shared_key: bytes, salt: bytes, info: bytes) -> bytes:
        """HKDF 密钥派生"""
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=info,
            backend=default_backend()
        ).derive(shared_key)

    def handshake(self) -> bool:
        """
        执行 Wave 握手，建立加密会话

        :return: 握手是否成功
        """
        # 生成 ECDH 密钥对
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        client_random = secrets.token_bytes(32)

        pubkey_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )

        request = _HandshakeRequest(
            random=base64.b64encode(client_random).decode(),
            app_id=self.app_id,
            did=self.device_id,
            key_shares=[_KeyShare(curve="secp256r1", pubkey=base64.b64encode(pubkey_bytes).decode())],
        )

        request_json = request.model_dump_json(by_alias=True)

        # ECDSA 签名
        signature = private_key.sign(request_json.encode(), ec.ECDSA(hashes.SHA256()))

        headers = {
            "Content-Type": "application/json",
            "x-tt-s-sign": base64.b64encode(signature).decode(),
            "User-Agent": USER_AGENT,
        }

        response = requests.post(HANDSHAKE_URL, data=request_json, headers=headers)

        if response.status_code != 200:
            return False

        resp = _HandshakeResponse(**response.json())

        # 计算共享密钥
        server_pubkey = base64.b64decode(resp.key_share.pubkey)
        server_public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), server_pubkey)
        shared_key = private_key.exchange(ec.ECDH(), server_public_key)
        server_random = base64.b64decode(resp.random)

        # 派生加密密钥
        salt = client_random + server_random
        encryption_key = self._derive_key(shared_key, salt, HKDF_INFO)

        # 保存会话，计算绝对过期时间（提前 60 秒刷新）
        self.session = WaveSession(
            ticket=resp.ticket,
            ticket_long=resp.ticket_long,
            encryption_key=encryption_key,
            client_random=client_random,
            server_random=server_random,
            shared_key=shared_key,
            ticket_exp=resp.ticket_exp,
            ticket_long_exp=resp.ticket_long_exp,
            expires_at=time.time() + resp.ticket_exp - 60,
        )

        if self._on_session_update:
            self._on_session_update(self.session)

        return True

    def _ensure_session(self) -> None:
        """确保会话有效，如果过期则自动刷新"""
        if self.session is None or self.session.is_expired():
            if not self.handshake():
                raise RuntimeError("Failed to establish/refresh session")

    def prepare_request(self, plaintext: bytes, extra_headers: Optional[dict] = None) -> tuple[bytes, dict]:
        """
        准备加密请求

        :param plaintext: 明文数据
        :param extra_headers: 额外的请求头
        :return: (密文, headers) 元组
        """
        self._ensure_session()

        nonce = secrets.token_bytes(12)
        ciphertext = self._chacha20_crypt(self.session.encryption_key, nonce, plaintext)
        stub = hashlib.md5(ciphertext).hexdigest().upper()

        headers = {
            "Content-Type": "application/json",
            "x-tt-e-b": "1",
            "x-tt-e-t": self.session.ticket,
            "x-tt-e-p": base64.b64encode(nonce).decode(),
            "x-ss-stub": stub,
        }

        if extra_headers:
            headers.update(extra_headers)

        return ciphertext, headers

    def decrypt(self, ciphertext: bytes, nonce: bytes) -> bytes:
        """
        解密数据

        :param ciphertext: 密文数据
        :param nonce: 12 字节 nonce
        :return: 明文数据
        """
        if not self.session:
            raise RuntimeError("No active session. Call handshake() first.")

        return self._chacha20_crypt(self.session.encryption_key, nonce, ciphertext)
