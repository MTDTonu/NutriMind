"""Web Push 路由：订阅 / 退订 / 测试 / 状态。

这套接口把「页面关着也能收到提醒」补齐：前端订阅后把三件套上报，
服务端调度器（`services/reminder_scheduler.py`）到点直接推。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from database.db import get_db
from database.models import PushSubscription
from middleware.auth import get_current_user_id
from schemas.push import PushSubscribeIn, PushUnsubscribeIn, PushTestIn
from services import push_service, reminder_scheduler
from utils.common import resp

router = APIRouter(prefix="/api/v1/push", tags=["推送"])

_MAX_ENDPOINT = 512
_MAX_ENDPOINTS_PER_USER = 10


@router.get("/public-key")
def public_key():
    """返回 VAPID 公钥：前端 `applicationServerKey` 需要它。"""
    vapid = push_service.get_vapid()
    return resp(
        200,
        "success",
        {"public_key": vapid["public_key"], "enabled": vapid["enabled"]},
    )


@router.get("/status")
def status(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """订阅与调度器状态：前端据此显示「后台提醒已开启 / 未开启」。"""
    subs = (
        db.query(PushSubscription)
        .filter(PushSubscription.user_id == user_id, PushSubscription.enabled == 1)
        .all()
    )
    data = reminder_scheduler.scheduler_status()
    data["subscriptions"] = [
        {
            "id": s.id,
            "device": (s.user_agent or "")[:60],
            "last_sent_at": s.last_sent_at.isoformat(timespec="seconds") if s.last_sent_at else None,
            "created_at": s.create_time.isoformat(timespec="seconds") if s.create_time else None,
        }
        for s in subs
    ]
    data["plan_today"] = reminder_scheduler.debug_plan(user_id)
    return resp(200, "success", data)


@router.post("/subscribe")
def subscribe(
    body: PushSubscribeIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """上报订阅（幂等：同一 endpoint 重复上报只做更新）。

    限制每台用户最多 10 个订阅，防止恶意刷 endpoint 撑爆推送额度。
    """
    endpoint = (body.endpoint or "").strip()
    if not endpoint.startswith("https://"):
        return resp(400, "推送地址必须以 https:// 开头", None)
    if len(endpoint) > _MAX_ENDPOINT or not body.p256dh or not body.auth:
        return resp(400, "订阅信息不完整", None)

    row = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    if row:
        row.user_id = user_id
        row.p256dh = body.p256dh
        row.auth = body.auth
        row.user_agent = (body.user_agent or "")[:255] or row.user_agent
        row.enabled = 1
        row.fail_count = 0
    else:
        total = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).count()
        if total >= _MAX_ENDPOINTS_PER_USER:
            return resp(400, f"订阅设备数量已达上限（{_MAX_ENDPOINTS_PER_USER} 台）", None)
        db.add(
            PushSubscription(
                user_id=user_id,
                endpoint=endpoint,
                p256dh=body.p256dh,
                auth=body.auth,
                user_agent=(body.user_agent or "")[:255],
            )
        )
    db.commit()

    count = (
        db.query(PushSubscription)
        .filter(PushSubscription.user_id == user_id, PushSubscription.enabled == 1)
        .count()
    )
    return resp(200, "已开启后台提醒", {"subscription_count": count})


@router.delete("/unsubscribe")
def unsubscribe(
    body: PushUnsubscribeIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """退订：传 endpoint 退指定设备，不传则退订全部（换设备/清缓存时用）。"""
    q = db.query(PushSubscription).filter(PushSubscription.user_id == user_id)
    if body.endpoint:
        q = q.filter(PushSubscription.endpoint == body.endpoint)
    removed = q.delete(synchronize_session=False)
    db.commit()
    return resp(200, "已关闭后台提醒", {"removed": removed})


@router.post("/test")
def send_test(
    body: PushTestIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """立刻发一条测试推送：让用户在不等待到点的情况下确认链路可用。"""
    result = _send(user_id, body.title, body.body)
    if result["subscribed"] == 0:
        return resp(400, "当前还没有可用订阅，请先在提醒设置里开启后台提醒", result)
    if result["sent"] == 0:
        return resp(502, "推送服务未接受本次请求，请稍后重试", result)
    return resp(200, "测试推送已发出", result)


def _send(user_id: int, title: str = None, body: str = None):
    """同步发送一条推送。

    路由本身是同步 `def`，FastAPI 会放进线程池执行，因此这里阻塞等待推送服务
    返回不会拖累事件循环。
    """
    from database.db import SessionLocal

    db = SessionLocal()
    try:
        return push_service.send_push(
            db,
            user_id,
            title or "知食 · 测试提醒",
            body or "这就是到点后的样子：页面关着也会响。",
            "/",
            f"test-{int(datetime.now().timestamp())}",
        )
    finally:
        db.close()
