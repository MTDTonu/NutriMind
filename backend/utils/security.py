"""安全工具：密码哈希（bcrypt）、JWT 生成与校验。

兼容性说明：
- 使用 passlib 的 CryptContext 封装 bcrypt。
- bcrypt >= 4.1 移除了 `bcrypt.__about__` 属性，会导致 passlib 1.7.4 在导入时
  抛出 AttributeError。这里在导入 passlib 之前动态补一个 `__about__` 兼容属性，
  保证在 bcrypt==4.2.0 下仍可正常工作。
- 密码绝不明文存储，统一使用 bcrypt 哈希。
"""
import os
import secrets
import warnings
import jwt
from datetime import datetime, timedelta

# ---------- 兼容 passlib 与 bcrypt>=4.1 的导入问题 ----------
import bcrypt  # noqa: E402
if not hasattr(bcrypt, "__about__"):
    import types  # noqa: E402
    _fake_about = types.ModuleType("bcrypt.__about__")
    _fake_about.__version__ = getattr(bcrypt, "__version__", "4.2.0")
    bcrypt.__about__ = _fake_about

from passlib.context import CryptContext  # noqa: E402

# bcrypt 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置。
# 安全约束：JWT_SECRET 绝不能保留默认值或可空，否则任何人都可用该已知字符串
# 伪造合法 Token、越权访问任意用户数据。因此：
#   1) 缺失或仍为默认值 -> 启动时生成强随机密钥并告警（仅用于让本地/演示可跑通，
#      重启后旧 Token 立即失效）；
#   2) 生产环境必须在 .env 显式配置固定的强随机字符串。
_JWT_DEFAULT = "change-me-secret"
_raw_secret = os.getenv("JWT_SECRET")
if not _raw_secret or _raw_secret == _JWT_DEFAULT:
    JWT_SECRET = secrets.token_hex(32)
    warnings.warn(
        "JWT_SECRET 未设置或仍为默认值，已自动生成随机密钥（重启后旧 Token 失效）。"
        "生产环境请在 .env 中配置固定的强随机字符串（如 openssl rand -hex 32）。",
        stacklevel=2,
    )
    print(
        "[SECURITY] JWT_SECRET 未显式配置，已自动生成随机密钥。"
        "生产环境请设置固定的 JWT_SECRET 以避免 Token 被伪造与跨重启失效。"
    )
else:
    JWT_SECRET = _raw_secret

# Token 有效期。默认 30 天，配合前端「记住凭据 + 失效自动静默重登」，
# 用户体验上等价于长期在线；后端仍随时可让 Token 自然到期，不签发永不过期凭证。
JWT_EXPIRE_DAYS = int(os.getenv("JWT_EXPIRE_DAYS", "30"))


def validate_jwt_secret() -> None:
    """在应用启动时被调用，二次确认密钥强度（保留扩展点，便于接入配置中心）。"""
    if not JWT_SECRET or len(JWT_SECRET) < 16:
        raise RuntimeError("JWT_SECRET 强度不足，请配置长度 >= 16 的随机字符串。")


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与存储的哈希是否匹配。"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    """生成 JWT，载荷包含 user_id 与过期时间（默认 7 天）。"""
    payload = {
        "user_id": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """解析 JWT，失败直接抛出异常（由调用方/中间件捕获返回 401）。"""
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
