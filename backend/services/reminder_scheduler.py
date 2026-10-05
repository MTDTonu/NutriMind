"""服务端提醒调度器：让提醒在「页面关着」的时候也能到。

与前端那份前台调度器（`frontend/src/utils/reminder.js`）的关系：
- 计划算法刻意保持一致（同样的时间源、同样的免打扰规则、同样的槽位 key），
  所以无论哪一边触发，用户对「几点会响」的预期是一致的。
- 去重放在数据库（`reminder_log` 唯一约束），不放内存：服务重启、多实例都不重复发。
- 触发窗口是「时间点后 15 分钟内」，调度心跳 60 秒，因此最坏延迟约 1 分钟；
  超过窗口则不补发——迟到半小时的午餐提醒没有意义，只会惹人烦。

时区：用固定偏移（默认 UTC+8）而非 zoneinfo。Windows 上不带 tzdata 时
`ZoneInfo('Asia/Shanghai')` 会直接抛错，而这是本项目的主要运行环境之一。
"""
import asyncio
import os
from datetime import date, datetime, timedelta, timezone

from services import push_service

# 提醒所属时区（小时偏移），可用 REMINDER_UTC_OFFSET 覆盖
_TZ = timezone(timedelta(hours=float(os.getenv("REMINDER_UTC_OFFSET", "8"))))
# 调度心跳（秒）
_TICK_SECONDS = max(int(os.getenv("REMINDER_TICK_SECONDS", "60")), 15)
# 触发窗口（分钟）：到点后这段时间内才算有效，超时不补发
_GRACE_MINUTES = max(int(os.getenv("REMINDER_GRACE_MINUTES", "15")), 1)

_MEALS = [
    ("breakfast_time", "breakfast", "早餐", "/diet", "吃完顺手记一笔，比晚上回忆准得多。"),
    ("lunch_time", "lunch", "午餐", "/diet", "记录花 10 秒，热量曲线才有参考价值。"),
    ("dinner_time", "dinner", "晚餐", "/diet", "晚餐记得吃够蛋白，别只吃水果。"),
]

_task = None
_stats = {
    "running": False,
    "started_at": None,
    "last_tick_at": None,
    "last_error": None,
    "ticks": 0,
    "sent": 0,
    "last_sent": [],
}


# ---------- 计划计算（与前端保持一致） ----------
def _to_minutes(hhmm):
    if not isinstance(hhmm, str):
        return None
    parts = hhmm.split(":")
    if len(parts) != 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if h > 23 or m > 59 or h < 0 or m < 0:
        return None
    return h * 60 + m


def _in_quiet(cfg, minute):
    if not cfg.quiet_enabled:
        return False
    start = _to_minutes(cfg.quiet_start)
    end = _to_minutes(cfg.quiet_end)
    if start is None or end is None or start == end:
        return False
    if start < end:
        return start <= minute < end
    return minute >= start or minute < end  # 跨零点


def _water_minutes(cfg):
    if not cfg.water_enabled:
        return []
    start = _to_minutes(cfg.water_start)
    end = _to_minutes(cfg.water_end)
    if start is None or end is None or end <= start:
        return []
    step = min(max(int(cfg.water_interval_hours or 2), 1), 6) * 60
    return list(range(start, end + 1, step))


def build_slots(cfg):
    """把提醒设置展开成当天的槽位列表：[{key, minute, title, body, url}]。"""
    slots = []

    if cfg.meal_enabled:
        for field, key, label, url, body in _MEALS:
            minute = _to_minutes(getattr(cfg, field))
            if minute is None:
                continue
            slots.append(
                {
                    "key": key,
                    "minute": minute,
                    "title": f"该记{label}了",
                    "body": body,
                    "url": url,
                }
            )

    if cfg.weigh_enabled:
        minute = _to_minutes(cfg.weigh_time)
        if minute is not None:
            slots.append(
                {
                    "key": "weigh",
                    "minute": minute,
                    "title": "该称体重了",
                    "body": "晨起空腹最稳定，称完体重曲线才有意义。",
                    "url": "/weight",
                }
            )

    for minute in _water_minutes(cfg):
        hh = f"{minute // 60:02d}{minute % 60:02d}"
        slots.append(
            {
                "key": f"water-{hh}",
                "minute": minute,
                "title": "喝杯水吧",
                "body": "补水能明显降低「假饥饿」带来的加餐。",
                "url": "/water",
            }
        )

    return slots


def _due(slots, now_minute):
    """挑出「正在触发窗口内」的槽位，支持跨零点的宽限期。"""
    out = []
    for slot in slots:
        start = slot["minute"]
        end = start + _GRACE_MINUTES
        if end <= 1440:
            hit = start <= now_minute < end
        else:
            hit = now_minute >= start or now_minute < end - 1440
        if hit:
            out.append(slot)
    return out


# ---------- 单轮扫描（同步，跑在独立线程里） ----------
def _tick_sync():
    from database.db import SessionLocal
    from database.models import PushSubscription, ReminderSetting, ReminderLog

    db = SessionLocal()
    sent_now = []
    try:
        now = datetime.now(_TZ)
        now_minute = now.hour * 60 + now.minute
        fire_date = now.date()

        # 只处理「有有效订阅」的用户：没有落地的通道就没有发送的意义
        rows = (
            db.query(PushSubscription)
            .filter(PushSubscription.enabled == 1)
            .all()
        )
        user_ids = sorted({r.user_id for r in rows})

        for uid in user_ids:
            cfg = db.query(ReminderSetting).filter(ReminderSetting.user_id == uid).first()
            if not cfg:
                continue
            if _in_quiet(cfg, now_minute):
                continue

            already = {
                r.slot_key
                for r in db.query(ReminderLog).filter(
                    ReminderLog.user_id == uid,
                    ReminderLog.fire_date == fire_date,
                    ReminderLog.channel == "push",
                ).all()
            }

            for slot in _due(build_slots(cfg), now_minute):
                if slot["key"] in already:
                    continue

                result = push_service.send_push(
                    db, uid, slot["title"], slot["body"], url=slot["url"], tag=slot["key"]
                )
                # 无论推送服务是否成功都记账：目的是「不重复打扰」，
                # 而不是「保证送达」——送达率由推送服务商决定。
                try:
                    db.add(
                        ReminderLog(
                            user_id=uid,
                            fire_date=fire_date,
                            slot_key=slot["key"],
                            channel="push",
                        )
                    )
                    db.commit()
                except Exception:  # noqa: BLE001
                    db.rollback()

                _stats["sent"] += result.get("sent", 0)
                sent_now.append(
                    {"user_id": uid, "slot": slot["key"], "at": now.strftime("%H:%M"), **result}
                )
    finally:
        db.close()

    return sent_now


def _cleanup_old_logs():
    """保留 30 天触发记录，避免日志表无上限增长。"""
    from database.db import SessionLocal
    from database.models import ReminderLog

    cutoff = datetime.now(_TZ).date() - timedelta(days=30)
    db = SessionLocal()
    try:
        db.query(ReminderLog).filter(ReminderLog.fire_date < cutoff).delete(
            synchronize_session=False
        )
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    finally:
        db.close()


# ---------- 调度循环 ----------
async def _loop():
    _stats["running"] = True
    _stats["started_at"] = datetime.now(_TZ).isoformat(timespec="seconds")
    print(f"[reminder] 服务端提醒调度器已启动：每 {_TICK_SECONDS}s 扫描一次（UTC{_TZ}）")

    ticks = 0
    while True:
        try:
            sent = await asyncio.to_thread(_tick_sync)
            _stats["last_tick_at"] = datetime.now(_TZ).isoformat(timespec="seconds")
            _stats["ticks"] += 1
            _stats["last_error"] = None
            if sent:
                _stats["last_sent"] = sent[-5:]
                print(f"[reminder] 已推送 {len(sent)} 条：{sent}")

            ticks += 1
            if ticks >= 240:  # 约每 4 小时清理一次历史记录
                ticks = 0
                await asyncio.to_thread(_cleanup_old_logs)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            # 心跳里的异常绝不能让整个调度器死掉
            _stats["last_error"] = str(exc)[:200]
            print(f"[reminder] 调度异常：{exc}")

        await asyncio.sleep(_TICK_SECONDS)


def start_scheduler():
    """由 FastAPI 启动事件调用；重复调用不会起多个循环。"""
    global _task
    if _task and not _task.done():
        return _task
    if os.getenv("REMINDER_SCHEDULER", "1") not in ("1", "true", "True"):
        print("[reminder] 调度器已按配置禁用（REMINDER_SCHEDULER=0）")
        return None

    try:
        # 提前拿到 VAPID 密钥，缺失时在此生成并落盘，后续发送无需再付费这一步
        push_service.get_vapid()
        _task = asyncio.ensure_future(_loop())
    except Exception as exc:  # noqa: BLE001
        print(f"[reminder] 调度器启动失败：{exc}")
    return _task


def stop_scheduler():
    global _task
    if _task and not _task.done():
        _task.cancel()
        _stats["running"] = False
    _task = None


def scheduler_status() -> dict:
    cfg_ready = False
    try:
        cfg_ready = bool(push_service.get_vapid().get("public_key"))
    except Exception:  # noqa: BLE001
        cfg_ready = False

    return {
        "running": bool(_stats["running"] and _task and not _task.done()),
        "started_at": _stats["started_at"],
        "last_tick_at": _stats["last_tick_at"],
        "last_error": _stats["last_error"],
        "ticks": _stats["ticks"],
        "sent_total": _stats["sent"],
        "last_sent": _stats["last_sent"],
        "tick_seconds": _TICK_SECONDS,
        "grace_minutes": _GRACE_MINUTES,
        "utc_offset": int(_TZ.utcoffset(None).total_seconds() // 3600),
        "vapid_ready": cfg_ready,
    }


def debug_plan(user_id: int) -> list:
    """给排查用：返回某用户当天计划好的槽位（不发通知）。"""
    from database.db import SessionLocal
    from database.models import ReminderSetting

    db = SessionLocal()
    try:
        cfg = db.query(ReminderSetting).filter(ReminderSetting.user_id == user_id).first()
        if not cfg:
            return []
        return [
            {"key": s["key"], "time": f"{s['minute'] // 60:02d}:{s['minute'] % 60:02d}", "title": s["title"]}
            for s in build_slots(cfg)
        ]
    finally:
        db.close()
