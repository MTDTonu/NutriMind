"""静态密钥加密（A2）：对落库与 .env 同步的 api_key 做对称加密。

设计：
- 密钥由 `JWT_SECRET` 经 SHA-256 派生（32 字节）→ urlsafe-base64，作为 Fernet key。
  复用已有的强随机 JWT_SECRET，不额外引入密钥文件。
- 密文以 `enc:` 前缀标识；`decrypt_secret` 对无前缀的值**原样返回**，
  以兼容「手工写入 .env 的明文 Key」以及历史明文数据（平滑迁移，无需数据迁移脚本）。
- JWT_SECRET 变更会导致旧密文无法解开 → 解密失败返回空串（视为未配置），
  用户重新在「我的」页填写即可。
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

_PREFIX = "enc:"


def _fernet() -> Fernet:
    # 延迟导入，避免 utils.security 与本模块的潜在导入顺序问题
    from utils.security import JWT_SECRET

    seed = (JWT_SECRET or "jianfei-local-fallback").encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
    return Fernet(key)


def is_encrypted(value) -> bool:
    """判断是否为加密串（带 enc: 前缀）。"""
    return isinstance(value, str) and value.startswith(_PREFIX)


def encrypt_secret(plain) -> str:
    """加密明文。空值原样返回；已是密文则不重复封装。"""
    if not plain:
        return plain or ""
    if is_encrypted(plain):
        return plain
    token = _fernet().encrypt(plain.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt_secret(value) -> str:
    """解密。无 `enc:` 前缀视为明文原样返回；解不开返回空串（视为未配置）。"""
    if not value:
        return ""
    if not is_encrypted(value):
        return value
    try:
        return _fernet().decrypt(value[len(_PREFIX):].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""
