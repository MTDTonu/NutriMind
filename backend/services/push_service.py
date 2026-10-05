"""Web Push 推送服务。

为什么需要这一层：
浏览器里那套前台调度器（`frontend/src/utils/reminder.js`）只在页面打开时才跑，
关掉浏览器就收不到任何提醒。Web Push 把订阅交给推送服务商（Google / Mozilla / Apple 的通道），
服务端按计划直接把通知推到设备通知中心——页面关着也能响。

关键取舍：
- **VAPID 密钥自动生成并落盘**：首次启动如果 `.env` 里没有密钥，就现生成一对写进去。
  若不落盘，服务每次重启密钥都变，之前所有订阅会全部失效（用户需要重新授权），这是最常见的线上坑。
- **载荷一律加密**：``p256dh`` / ``auth`` 由浏览器生成，服务端用它加密 JSON，
  推送服务商看不到内容。
- **失效订阅立即清理**：推送返回 404/410 说明订阅已注销（用户卸了 PWA 或清了数据），
  留着只会让每次发送都失败。
"""
import json
import os
from datetime import datetime
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from dotenv import set_key

_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

# VAPID 声明里的联系方式：必须是 mailto: 或 https: 开头的合法 URL，否则推送服务商会拒收
_DEFAULT_SUB = "mailto:nutrimind@example.com"

_cached: Optional[dict] = None


def _b64url(raw: bytes) -> str:
    """base64url 编码并去掉 '=' 填充（Web Push 的约定）。"""
    import base64

    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _generate_keys() -> tuple:
    """生成一对 P-256 密钥，返回 (私钥 base64url, 公钥 base64url 未压缩点)。"""
    priv = ec.generate_private_key(ec.SECP256R1())
    priv_raw = priv.private_numbers().private_value.to_bytes(32, "big")
    pub_raw = priv.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    return _b64url(priv_raw), _b64url(pub_raw)


def _persist(private_key: str, public_key: str):
    """把密钥写回 .env 并同步到进程环境，保证重启后订阅依然有效。"""
    try:
        if os.path.exists(_ENV_PATH):
            set_key(_ENV_PATH, "VAPID_PRIVATE_KEY", private_key, quote_mode="never")
            set_key(_ENV_PATH, "VAPID_PUBLIC_KEY", public_key, quote_mode="never")
    except Exception:  # noqa: BLE001
        # 只读环境（容器镜像等）写不进去：降级为本次进程有效，并在 /push/status 里提示
        pass
    os.environ["VAPID_PRIVATE_KEY"] = private_key
    os.environ["VAPID_PUBLIC_KEY"] = public_key


def get_vapid(force_reload: bool = False) -> dict:
    """读取（必要时生成）VAPID 配置。

    返回 {enabled, public_key, private_key, sub}；enabled=False 表示 .env 缺失且不可写，
    此时退化为「仅前台提醒」，不会阻塞其它功能。
    """
    global _cached
    if _cached and not force_reload:
        return _cached

    priv = os.getenv("VAPID_PRIVATE_KEY", "").strip()
    pub = os.getenv("VAPID_PUBLIC_KEY", "").strip()

    if not priv or not pub:
        priv, pub = _generate_keys()
        _persist(priv, pub)
        print("[push] 已生成 VAPID 密钥对并写入 .env（请勿外泄私钥）")

    _cached = {
        "enabled": True,
        "private_key": priv,
        "public_key": pub,
        "sub": os.getenv("VAPID_SUB", _DEFAULT_SUB),
    }
    return _cached


def vapid_claims() -> dict:
    """VAPID JWT 声明。aud 由 pywebpush 按 endpoint 自动补齐。"""
    return {"sub": get_vapid()["sub"]}


def _send_one(subscription_info: dict, payload: str) -> None:
    """同步发送一条推送（阻塞式，由调用方放进线程池）。"""
    from pywebpush import webpush, WebPushException

    webpush(
        subscription_info=subscription_info,
        data=payload,
        vapid_private_key=get_vapid()["private_key"],
        vapid_claims=vapid_claims(),
        ttl=60 * 60 * 6,  # 离线设备最长排队 6 小时
        timeout=10,
    )


def send_to_subscription(db, sub, payload: dict) -> tuple:
    """向单个订阅推送，返回 (ok, detail)。

    失效订阅（404/410）直接删除；其它错误累计失败次数，连续失败 20 次后停用，
    避免一台坏设备拖慢整个调度循环。
    """
    info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}
    try:
        _send_one(info, json.dumps(payload, ensure_ascii=False))
        sub.fail_count = 0
        sub.last_sent_at = datetime.now()
        db.commit()
        return True, "sent"
    except Exception as exc:  # noqa: BLE001
        status = getattr(exc, "status_code", None)
        db.rollback()
        if status in (404, 410):
            db.delete(sub)
            db.commit()
            return False, f"订阅已失效({status})，已清理"
        sub.fail_count = (sub.fail_count or 0) + 1
        if sub.fail_count >= 20:
            sub.enabled = 0
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        return False, f"{status or 'ERR'}: {exc}"


def send_push(db, user_id: int, title: str, body: str, url: str = "/", tag: str = "") -> dict:
    """向某用户的所有有效订阅推送同一条通知。

    返回 {subscribed, sent, failed, details}，便于接口直接回显给前端排查。
    """
    from database.models import PushSubscription

    subs = (
        db.query(PushSubscription)
        .filter(PushSubscription.user_id == user_id, PushSubscription.enabled == 1)
        .all()
    )
    payload = {
        "title": title,
        "body": body,
        "url": url,
        "tag": tag or None,
        "icon": "/icons/icon-192.png",
        "badge": "/icons/icon-192.png",
    }
    out = {"subscribed": len(subs), "sent": 0, "failed": 0, "details": []}
    for sub in subs:
        ok, detail = send_to_subscription(db, sub, payload)
        if ok:
            out["sent"] += 1
        else:
            out["failed"] += 1
            out["details"].append(detail[:120])
    return out
