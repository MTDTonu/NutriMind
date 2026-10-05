"""用户今日画像：把分散在各表的真实数据压成一份「AI 能读懂、人也能读」的快照。

用途有两个：
1. 前端 AI 页顶部展示「今日画像」，让提问前先看见自己的处境；
2. 注入对话系统提示词，让回答基于真实摄入 / 体重 / 运动，而不是泛泛而谈。

只读，不落库。任一段数据缺失就降级为 None，前端按「未记录」展示。
"""

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import (
    DietRecord,
    ExerciseRecord,
    UserCheckin,
    WaterRecord,
    WeightRecord,
)
from services import energy_service
from utils.common import today

# meal_type 是 1/2/3/4 的整数枚举，画像里统一转成中文
_MEAL_NAMES = {1: "早餐", 2: "午餐", 3: "晚餐", 4: "加餐"}


def _round(v, n=1):
    return None if v is None else round(float(v), n)


def build_brief(db: Session, user, target_date: date = None) -> dict:
    """构建用户当日画像。"""
    d = target_date or today()
    uid = user.id

    # ---- 目标热量（含自适应反推）----
    try:
        plan = energy_service.current_plan(db, user)
        target_kcal = plan["target"]["target_calorie"]
        base_tdee = plan["base_tdee"]
        using_adaptive = plan["using_adaptive"]
        weekly_loss = plan["target"].get("weekly_loss_kg")
    except Exception:  # noqa: BLE001 画像属增强信息，失败不应阻断对话
        target_kcal = float(getattr(user, "recommend_calorie", 0) or 0)
        base_tdee = float(getattr(user, "tdee", 0) or 0)
        using_adaptive = False
        weekly_loss = None

    # ---- 今日饮食 ----
    rows = (
        db.query(DietRecord)
        .filter(DietRecord.user_id == uid, DietRecord.record_date == d)
        .all()
    )
    intake = sum(r.calorie or 0 for r in rows)
    protein = sum(r.protein or 0 for r in rows)
    fat = sum(r.fat or 0 for r in rows)
    carb = sum(r.carbohydrate or 0 for r in rows)
    meals = []
    for code, name in _MEAL_NAMES.items():
        sub = [r for r in rows if r.meal_type == code]
        if sub:
            meals.append({"meal": name, "kcal": round(sum(r.calorie or 0 for r in sub))})

    # ---- 今日运动与饮水 ----
    burn = (
        db.query(func.coalesce(func.sum(ExerciseRecord.calorie_burn), 0.0))
        .filter(ExerciseRecord.user_id == uid, ExerciseRecord.record_date == d)
        .scalar()
        or 0
    )
    minutes = (
        db.query(func.coalesce(func.sum(ExerciseRecord.duration), 0))
        .filter(ExerciseRecord.user_id == uid, ExerciseRecord.record_date == d)
        .scalar()
        or 0
    )
    water_row = (
        db.query(WaterRecord)
        .filter(WaterRecord.user_id == uid, WaterRecord.record_date == d)
        .order_by(WaterRecord.id.desc())
        .first()
    )

    # ---- 体重：最新一次 + 近 7 天变化 ----
    w_rows = (
        db.query(WeightRecord)
        .filter(WeightRecord.user_id == uid)
        .order_by(WeightRecord.record_date.desc())
        .all()
    )
    latest_w = w_rows[0] if w_rows else None
    week_ago = d - timedelta(days=7)
    old_w = next((r for r in w_rows if r.record_date <= week_ago), None)
    w_delta = (
        _round(latest_w.weight - old_w.weight, 1)
        if (latest_w and old_w)
        else None
    )

    # ---- 连续打卡 ----
    streak = (
        db.query(func.max(UserCheckin.continuous_days))
        .filter(UserCheckin.user_id == uid)
        .scalar()
        or 0
    )

    remaining = None
    if target_kcal:
        remaining = round(float(target_kcal) - float(intake))

    return {
        "date": d.strftime("%Y-%m-%d"),
        "target_kcal": round(float(target_kcal)),
        "using_adaptive": bool(using_adaptive),
        "base_tdee": _round(base_tdee, 0),
        "weekly_loss_kg": weekly_loss,
        "intake_kcal": round(float(intake)),
        "remaining_kcal": remaining,
        "protein_g": _round(protein),
        "fat_g": _round(fat),
        "carb_g": _round(carb),
        "meal_count": len(rows),
        "meals": meals,
        "burn_kcal": round(float(burn)),
        "exercise_minutes": int(minutes),
        "water_ml": int(water_row.total_amount) if water_row else 0,
        "water_target_ml": int(water_row.target_amount) if water_row else 0,
        "weight_kg": _round(latest_w.weight) if latest_w else None,
        "weight_7d_delta": w_delta,
        "weight_days": (d - latest_w.record_date).days if latest_w else None,
        "streak_days": int(streak),
        "target_weight_kg": _round(getattr(user, "target_weight", None)),
    }


def brief_to_text(brief: dict) -> str:
    """把画像压成一段给大模型看的紧凑中文描述（控制在 ~200 字）。"""
    if not brief:
        return ""

    def g(k, suffix="", default="未记录"):
        v = brief.get(k)
        if v is None or v == "":
            return default
        return f"{v}{suffix}"

    gap = ""
    if brief.get("target_weight_kg") and brief.get("weight_kg"):
        diff = round(brief["weight_kg"] - brief["target_weight_kg"], 1)
        if diff > 0:
            gap = f"，距目标还差 {diff} kg"
        elif diff <= 0:
            gap = "，已达成目标体重"

    w_trend = ""
    if brief.get("weight_7d_delta") is not None:
        delta = brief["weight_7d_delta"]
        w_trend = f"，近 7 天{'下降' if delta < 0 else '上升'} {abs(delta)} kg"

    meals = "、".join(f"{m['meal']}{m['kcal']}kcal" for m in (brief.get("meals") or []))
    remaining = brief.get("remaining_kcal")
    remain_txt = (
        f"还剩余 {remaining} kcal 额度"
        if remaining is not None and remaining >= 0
        else f"已超出 {abs(remaining)} kcal"
        if remaining is not None
        else ""
    )

    return (
        f"今日（{brief.get('date')}）实况：目标摄入 {g('target_kcal', 'kcal')}，"
        f"已摄入 {g('intake_kcal', 'kcal')}（{remain_txt}），"
        f"蛋白质 {g('protein_g', 'g')} / 脂肪 {g('fat_g', 'g')} / 碳水 {g('carb_g', 'g')}。"
        f"已记录 {brief.get('meal_count', 0)} 餐"
        + (f"（{meals}）" if meals else "")
        + "。"
        f"运动消耗 {g('burn_kcal', 'kcal')} / {g('exercise_minutes', ' 分钟')}，"
        f"饮水 {g('water_ml', 'ml')}（目标 {g('water_target_ml', 'ml', '—')}）。"
        f"体重 {g('weight_kg', 'kg')}{gap}{w_trend}，连续打卡 {brief.get('streak_days', 0)} 天。"
    )
