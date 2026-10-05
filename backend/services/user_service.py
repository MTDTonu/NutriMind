"""用户服务：资料修改、偏好设置、指标查询、打卡。"""
from datetime import timedelta, date

from sqlalchemy.orm import Session

from database.models import User, UserCheckin, UserAISettings
from services.calc_service import calc_bmr, calc_tdee, calc_recommend, calc_bmi
from utils.common import date_to_str
from utils.crypto import encrypt_secret, decrypt_secret
from utils.exceptions import AppException


# ---------- 大模型配置（文字 / 视觉 / 语音 三套）----------

def get_user_ai_settings(db: Session, user_id: int):
    """读取用户大模型配置行（无则返回 None）。"""
    return db.query(UserAISettings).filter(UserAISettings.user_id == user_id).first()


def upsert_user_ai_settings(db: Session, user_id: int, data: dict) -> UserAISettings:
    """写入/更新三套能力配置。

    data 形如 {'text': {...}, 'vision': {...}, 'asr': {...}}，每项字段可选。
    api_key 为空字符串或 None 时保持原值（不覆盖、不清除），避免误清空。
    """
    row = get_user_ai_settings(db, user_id)
    if row is None:
        row = UserAISettings(user_id=user_id)
        db.add(row)

    for cap in ("text", "vision", "asr"):
        inc = data.get(cap) or {}
        prov = inc.get("provider")
        key = inc.get("api_key")
        model = inc.get("model")
        base = inc.get("base_url")
        if prov is not None:
            setattr(row, f"{cap}_provider", prov)
        if model is not None:
            setattr(row, f"{cap}_model", model)
        if base is not None:
            setattr(row, f"{cap}_base_url", base)
        # 仅当 api_key 为非空字符串时才更新（空/None 保持原值）
        if key not in (None, ""):
            # 静态加密后落库（明文仅存在于内存；读取时由 build_cfg 解密）
            setattr(row, f"{cap}_api_key", encrypt_secret(key))

    db.commit()
    db.refresh(row)
    return row


def build_cfg(row, cap: str, default_model: str) -> dict:
    """由配置行构造一套能力的调用参数（provider/api_key/model/base_url）。

    无配置行时退回环境变量 ZHIPU_API_KEY（兼容老用法）。
    """
    if row is None:
        import os
        return {
            "provider": "zhipu",
            # 环境变量兜底：可能是明文（手工写入）或密文（由 UI 同步），统一解密（明文原样返回）
            "api_key": decrypt_secret(os.getenv("ZHIPU_API_KEY") or ""),
            "model": default_model,
            "base_url": None,
        }
    return {
        "provider": getattr(row, f"{cap}_provider") or "zhipu",
        "api_key": decrypt_secret(getattr(row, f"{cap}_api_key") or ""),
        "model": getattr(row, f"{cap}_model") or default_model,
        "base_url": getattr(row, f"{cap}_base_url") or None,
    }


def update_profile(db: Session, user_id: int, body) -> User:
    """修改个人信息，并重算代谢指标。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(401, "用户不存在")

    # 仅更新传入字段
    if body.gender is not None:
        user.gender = body.gender
    if body.age is not None:
        user.age = body.age
    if body.height is not None:
        user.height = body.height
    if body.current_weight is not None:
        user.current_weight = body.current_weight
    if body.target_weight is not None:
        user.target_weight = body.target_weight
    if body.activity_level is not None:
        user.activity_level = body.activity_level

    # 重算代谢指标
    bmr = calc_bmr(user.gender, user.age, user.height, user.current_weight)
    tdee = calc_tdee(bmr, user.activity_level)
    recommend = calc_recommend(tdee, bmr)
    user.bmr = round(bmr, 2)
    user.tdee = round(tdee, 2)
    user.recommend_calorie = round(recommend, 2)

    db.commit()
    db.refresh(user)
    return user


def update_preference(db: Session, user_id: int, diet_preference: str, diet_avoid: str = None) -> User:
    """更新饮食偏好与忌口（未传入的字段保持不变）。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(401, "用户不存在")
    if diet_preference is not None:
        user.diet_preference = diet_preference
    if diet_avoid is not None:
        user.diet_avoid = diet_avoid
    db.commit()
    db.refresh(user)
    return user


def get_metrics(db: Session, user_id: int) -> dict:
    """返回用户代谢指标 + BMI。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(401, "用户不存在")
    return {
        "bmr": user.bmr,
        "tdee": user.tdee,
        "recommend_calorie": user.recommend_calorie,
        "activity_level": user.activity_level,
        "bmi": calc_bmi(user.current_weight, user.height),
    }


def mark_checkin(db: Session, user_id: int, check_date) -> UserCheckin:
    """用户打卡：幂等 upsert；插入后重算整条连续链，确保乱序/补录也正确。

    旧实现只在「插入新记录」时依据「昨日记录」推算连续天数，并把结果 denormalize
    落库。一旦用户补录历史日期（例如先记了 5 号，回头再补 4 号），已存在的 5 号
    记录 continuous_days 会变成脏值（应为 2 却仍为 1），且后续所有记录全部偏移。
    现改为：保证当日记录存在后，对全量打卡按日期排序重算连续链，断档即归 1。
    """
    exist = db.query(UserCheckin).filter(
        UserCheckin.user_id == user_id,
        UserCheckin.checkin_date == check_date,
    ).first()
    if not exist:
        rec = UserCheckin(
            user_id=user_id,
            checkin_date=check_date,
            continuous_days=1,
            status=1,
        )
        db.add(rec)
        db.commit()

    # 无论当日记录是否已存在，都重算整条连续链（覆盖乱序补录 / 历史回填场景）
    _recompute_continuous(db, user_id)

    return db.query(UserCheckin).filter(
        UserCheckin.user_id == user_id,
        UserCheckin.checkin_date == check_date,
    ).first()


def _recompute_continuous(db: Session, user_id: int) -> None:
    """按日期升序重算该用户所有打卡的连续天数。

    - 与前一天连续（相差恰好 1 天）→ continuous = 前一天 + 1
    - 否则（首条 / 断档）→ continuous = 1
    仅统计 status==1 的正常记录。
    """
    rows = (
        db.query(UserCheckin)
        .filter(UserCheckin.user_id == user_id, UserCheckin.status == 1)
        .order_by(UserCheckin.checkin_date.asc())
        .all()
    )
    prev = None
    for r in rows:
        if prev is not None and (r.checkin_date - prev.checkin_date).days == 1:
            r.continuous_days = prev.continuous_days + 1
        else:
            r.continuous_days = 1
        prev = r
    db.commit()


def get_checkin_stats(db: Session, user_id: int, month: str = None, on: date = None):
    """读取真实打卡数据（不做任何伪造）。

    - continuous_days: 连续天数。今日已打卡取今日值；否则若昨日已打卡取昨日值
      （当天尚未结束，连续未中断）；都没有则为 0。
    - total_days: 累计打卡总天数（真实计数）。
    - checked_today: 今日是否已打卡。
    - dates: 指定月份（默认当月）内已打卡的日期列表 'YYYY-MM-DD'。

    优化：不再把所有历史打卡行一次性加载进内存，改为
    - total_days 用 COUNT 聚合；
    - 今日 / 昨日各按索引取单行（用于连续天数）；
    - dates 只查目标月份区间。
    打卡行数增长后内存与耗时仍近似常量级。
    """
    from sqlalchemy import func as _func

    on = on or date.today()

    # 累计打卡天数：SQL 聚合，不加载行
    total_days = int(
        db.query(_func.count(UserCheckin.id))
        .filter(UserCheckin.user_id == user_id, UserCheckin.status == 1)
        .scalar()
        or 0
    )

    def _one(d):
        return (
            db.query(UserCheckin)
            .filter(
                UserCheckin.user_id == user_id,
                UserCheckin.status == 1,
                UserCheckin.checkin_date == d,
            )
            .first()
        )

    today_rec = _one(on)
    yest_rec = _one(on - timedelta(days=1))

    if today_rec:
        continuous = today_rec.continuous_days
    elif yest_rec:
        continuous = yest_rec.continuous_days
    else:
        continuous = 0

    # 目标月份区间（默认当月），仅查询该月的打卡日期
    m = month or on.strftime("%Y-%m")
    try:
        y, mo = int(m[:4]), int(m[5:7])
        if not (1 <= mo <= 12):
            raise ValueError
    except Exception:  # noqa: BLE001
        y, mo = on.year, on.month
        m = on.strftime("%Y-%m")
    month_start = date(y, mo, 1)
    month_end = date(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1) - timedelta(days=1)
    date_rows = (
        db.query(UserCheckin.checkin_date)
        .filter(
            UserCheckin.user_id == user_id,
            UserCheckin.status == 1,
            UserCheckin.checkin_date >= month_start,
            UserCheckin.checkin_date <= month_end,
        )
        .order_by(UserCheckin.checkin_date.asc())
        .all()
    )
    dates = [date_to_str(r[0]) for r in date_rows]

    return {
        "continuous_days": int(continuous),
        "total_days": total_days,
        "checked_today": bool(today_rec),
        "today": date_to_str(on),
        "month": m,
        "dates": dates,
    }
