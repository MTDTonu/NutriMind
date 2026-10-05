"""智能能量引擎：静态估算 → 真实反推 → 周校准 → 目标重算。

三层口径必须分清，界面与文案都要如实标注，不能混着说：
1. 静态 TDEE（static_tdee）：按 Mifflin-St Jeor 公式 + 活动系数算出，是「人群均值推测」。
2. 自适应 TDEE（adaptive_tdee）：按本人「摄入 - 体重变化」反推，是「个人实测」。
   只有当数据充分时才给，绝不用少量数据硬算一个漂亮数字。
3. 目标摄入（target_calorie）：在 2 的基础上减去缺口，并叠加安全下限。

核心换算：1 kg 体脂 ≈ 7700 kcal。
"""
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import date, timedelta

from database.models import User, DietRecord, WeightRecord
from utils.exceptions import AppException

KCAL_PER_KG = 7700.0

# 校验门槛：达不到就不给结果，宁可说「数据不足」也不给错误结论
MIN_DIET_DAYS = 7       # 至少 7 天有饮食记录
MIN_WEIGHT_POINTS = 4   # 至少 4 次称重
MIN_SPAN_DAYS = 10      # 称重至少跨 10 天


# ---------------------------------------------------------------- 数据采集

def daily_intake(db: Session, user_id: int, start: date, end: date) -> dict:
    """区间内每日摄入热量（kcal）。"""
    rows = (
        db.query(DietRecord.record_date, func.sum(DietRecord.calorie))
        .filter(
            DietRecord.user_id == user_id,
            DietRecord.record_date >= start,
            DietRecord.record_date <= end,
        )
        .group_by(DietRecord.record_date)
        .all()
    )
    return {r[0]: float(r[1] or 0) for r in rows}


def weight_points(db: Session, user_id: int, start: date, end: date) -> list:
    """区间内体重记录 [(date, weight)]，按日期升序。"""
    rows = (
        db.query(WeightRecord.record_date, WeightRecord.weight)
        .filter(
            WeightRecord.user_id == user_id,
            WeightRecord.record_date >= start,
            WeightRecord.record_date <= end,
        )
        .order_by(WeightRecord.record_date)
        .all()
    )
    return [(r[0], float(r[1])) for r in rows]


def _slope_per_day(points: list) -> float:
    """最小二乘拟合体重的日变化斜率（kg/日）。

    用回归而非「末值 - 初值」，是因为单点波动（饮水、排便、称重时间）会主导差值，
    回归能把每天的噪声摊平。
    """
    n = len(points)
    if n < 2:
        return 0.0
    x0 = points[0][0].toordinal()
    xs = [(p[0].toordinal() - x0) for p in points]
    ys = [p[1] for p in points]
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom


# ---------------------------------------------------------------- 反推 TDEE

def adaptive_tdee(db: Session, user: User, window: int = 14) -> dict:
    """反推用户真实 TDEE。

    Returns:
        dict: valid / adaptive_tdee / static_tdee / delta / mean_intake /
              slope_kg_per_day / diet_days / weight_points / confidence / reason
    """
    end = date.today()
    start = end - timedelta(days=window - 1)

    intakes = daily_intake(db, user.id, start, end)
    points = weight_points(db, user.id, start, end)

    diet_days = len(intakes)
    mean_intake = sum(intakes.values()) / diet_days if diet_days else 0.0
    static = float(user.tdee or 0)

    span = (points[-1][0] - points[0][0]).days if len(points) >= 2 else 0
    reasons = []
    if diet_days < MIN_DIET_DAYS:
        reasons.append(f"饮食记录仅 {diet_days} 天（需 ≥{MIN_DIET_DAYS} 天）")
    if len(points) < MIN_WEIGHT_POINTS:
        reasons.append(f"体重记录仅 {len(points)} 次（需 ≥{MIN_WEIGHT_POINTS} 次）")
    if span < MIN_SPAN_DAYS:
        reasons.append(f"称重仅跨 {span} 天（需 ≥{MIN_SPAN_DAYS} 天）")

    if reasons:
        return {
            "valid": False,
            "reason": "；".join(reasons) + "，暂不可校准",
            "static_tdee": round(static, 1),
            "adaptive_tdee": None,
            "mean_intake": round(mean_intake, 1),
            "diet_days": diet_days,
            "weight_points": len(points),
            "span_days": span,
            "confidence": 0.0,
        }

    slope = _slope_per_day(points)  # kg/日，减重时为负
    # 体重每减少 1kg 代表额外动用 7700kcal，折算到每天即为「除摄入外还消耗的部分」
    adaptive = mean_intake - slope * KCAL_PER_KG

    # 安全夹逼：反推值不应偏离生理常识，防止单点噪声得出荒谬数字
    bmr = float(user.bmr or 0)
    lo, hi = bmr * 1.1, bmr * 2.5
    clamped = None
    if bmr > 0:
        if adaptive < lo:
            adaptive, clamped = lo, "low"
        elif adaptive > hi:
            adaptive, clamped = hi, "high"

    # 数据越密，置信度越高（14 天满载 ≈ 0.9）
    coverage = min(diet_days / window, 1.0)
    confidence = round(0.5 + 0.4 * coverage, 2)
    if clamped:
        confidence = round(confidence * 0.7, 2)

    return {
        "valid": True,
        "reason": (
            "数据充分，已按近 %d 天摄入与体重变化反推" % window
            if not clamped
            else "反推值超出合理区间，已夹逼到安全边界"
        ),
        "static_tdee": round(static, 1),
        "adaptive_tdee": round(adaptive, 1),
        "delta": round(adaptive - static, 1),
        "mean_intake": round(mean_intake, 1),
        "slope_kg_per_day": round(slope, 4),
        "slope_kg_per_week": round(slope * 7, 2),
        "diet_days": diet_days,
        "weight_points": len(points),
        "span_days": span,
        "confidence": confidence,
        "clamped": clamped,
    }


# ---------------------------------------------------------------- 目标计算

def compute_target(user: User, base_tdee: float) -> dict:
    """按目标模式计算推荐摄入与预期减重速率。

    安全规则（不可绕过）：
    - 摄入不得低于 BMR（避免代谢适应与营养不良风险）；
    - 缺口不得超过 TDEE 的 25%（避免过快掉重与肌肉流失）；
    - 周减重速率上限 1.0kg，下限 0.2kg。
    """
    bmr = float(user.bmr or 0)
    mode = getattr(user, "target_mode", "deficit") or "deficit"
    base = float(base_tdee or user.tdee or 0)

    if mode == "rate":
        rate = float(getattr(user, "target_rate", None) or 0.5)
        rate = max(0.2, min(1.0, rate))  # kg/周
        deficit = rate * KCAL_PER_KG / 7.0
    else:
        deficit = float(getattr(user, "target_deficit", None) or 400)

    warnings = []
    # 上限：缺口不超过 TDEE 的 25%
    cap = base * 0.25
    if deficit > cap > 0:
        warnings.append(f"缺口 {deficit:.0f} kcal 超过消耗量的 25%，已下调至 {cap:.0f} kcal")
        deficit = cap

    target = max(base - deficit, bmr)
    actual_deficit = base - target

    if actual_deficit < 1:
        warnings.append("当前目标摄入已不低于基础代谢，无法再制造缺口")
        actual_deficit = 0.0

    weekly_loss = actual_deficit * 7 / KCAL_PER_KG

    # 预计达成日
    gap = float(user.current_weight or 0) - float(user.target_weight or 0)
    eta_days = None
    if weekly_loss > 0 and gap > 0:
        eta_days = int((gap / weekly_loss) * 7)

    return {
        "mode": mode,
        "target_calorie": round(target, 1),
        "deficit": round(actual_deficit, 1),
        "weekly_loss_kg": round(weekly_loss, 2),
        "estimated_days": eta_days,
        "gap_kg": round(gap, 1),
        "warnings": warnings,
    }


def current_plan(db: Session, user: User, window: int = 14) -> dict:
    """组合「反推 TDEE + 目标计算」得到当前完整方案。"""
    fit = adaptive_tdee(db, user, window)
    base = fit.get("adaptive_tdee") or float(user.tdee or 0)
    target = compute_target(user, base)
    return {
        "using_adaptive": bool(fit.get("adaptive_tdee")),
        "fit": fit,
        "base_tdee": round(base, 1),
        "target": target,
        "last_calibrate_at": (
            user.last_calibrate_at.strftime("%Y-%m-%d") if getattr(user, "last_calibrate_at", None) else None
        ),
    }


# ---------------------------------------------------------------- 写入

def calibrate(db: Session, user: User, window: int = 14, persist: bool = True) -> dict:
    """执行一次周校准：把可信的反推结果落到 user.tdee_adaptive 并重算推荐摄入。"""
    result = current_plan(db, user, window)
    if not result["fit"]["valid"]:
        return result

    if persist:
        user.tdee_adaptive = result["base_tdee"]
        user.last_calibrate_at = date.today()
        user.recommend_calorie = result["target"]["target_calorie"]
        db.commit()
        db.refresh(user)
    result["calibrated"] = True
    return result


def set_target(db: Session, user: User, mode: str, rate=None, deficit=None) -> dict:
    """切换目标模式并立即重算推荐摄入。"""
    if mode not in ("deficit", "rate"):
        raise AppException(400, "目标模式应为 deficit 或 rate")
    if mode == "rate":
        if rate is None:
            raise AppException(400, "速率模式需提供每周减重目标 target_rate")
        if not (0.1 <= float(rate) <= 1.5):
            raise AppException(400, "每周减重目标应在 0.1~1.5 kg 之间")
    if deficit is not None and not (0 <= float(deficit) <= 1500):
        raise AppException(400, "每日热量缺口应在 0~1500 kcal 之间")

    user.target_mode = mode
    if mode == "rate":
        user.target_rate = float(rate)
    if deficit is not None:
        user.target_deficit = float(deficit)

    base = float(getattr(user, "tdee_adaptive", None) or user.tdee or 0)
    plan = compute_target(user, base)
    user.recommend_calorie = plan["target_calorie"]
    db.commit()
    db.refresh(user)

    return {
        "mode": mode,
        "target_calorie": plan["target_calorie"],
        "deficit": plan["deficit"],
        "weekly_loss_kg": plan["weekly_loss_kg"],
        "estimated_days": plan["estimated_days"],
        "warnings": plan["warnings"],
    }
