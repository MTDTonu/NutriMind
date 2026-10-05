"""统计服务：每日/每周/体重趋势/营养趋势。"""
from datetime import date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import DietRecord, WeightRecord, ExerciseRecord, User


def _date_list(end: date, days: int) -> list:
    """返回从 (end - days + 1) 到 end 的日期列表（升序）。"""
    return [end - timedelta(days=i) for i in range(days - 1, -1, -1)]


def _sum_calorie(db: Session, user_id: int, d: date) -> float:
    val = db.query(func.coalesce(func.sum(DietRecord.calorie), 0.0)).filter(
        DietRecord.user_id == user_id, DietRecord.record_date == d
    ).scalar()
    return float(val or 0)


def _sum_burned(db: Session, user_id: int, d: date) -> float:
    val = db.query(func.coalesce(func.sum(ExerciseRecord.calorie_burn), 0.0)).filter(
        ExerciseRecord.user_id == user_id, ExerciseRecord.record_date == d
    ).scalar()
    return float(val or 0)


def daily_stat(db: Session, user_id: int, target_date: date) -> dict:
    """每日统计：摄入、消耗、净热量、体重、推荐摄入、剩余。"""
    intake = _sum_calorie(db, user_id, target_date)
    burned = _sum_burned(db, user_id, target_date)
    weight_rec = db.query(WeightRecord).filter(
        WeightRecord.user_id == user_id, WeightRecord.record_date == target_date
    ).first()
    user = db.query(User).filter(User.id == user_id).first()
    recommend = user.recommend_calorie if user else 0

    net = round(intake - burned, 2)
    remain = round(recommend - intake, 2)
    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "intake_calorie": round(intake, 2),
        "burned_calorie": round(burned, 2),
        "net": net,
        "weight": weight_rec.weight if weight_rec else None,
        "recommend_calorie": recommend,
        "remain": remain,
    }


def weekly_stat(db: Session, user_id: int) -> dict:
    """近 7 天统计。"""
    end = date.today()
    days = _date_list(end, 7)
    days_str = [d.strftime("%Y-%m-%d") for d in days]
    intake = [round(_sum_calorie(db, user_id, d), 2) for d in days]
    burned = [round(_sum_burned(db, user_id, d), 2) for d in days]

    # 平均体重（区间内存在的体重记录）
    weights = [
        w.weight for w in db.query(WeightRecord.weight).filter(
            WeightRecord.user_id == user_id, WeightRecord.record_date.in_(days)
        ).all()
    ]
    avg_weight = round(sum(weights) / len(weights), 2) if weights else None

    user = db.query(User).filter(User.id == user_id).first()
    recommend = user.recommend_calorie if user else 0
    deficits = [recommend - intake[i] + burned[i] for i in range(7)]
    avg_deficit = round(sum(deficits) / 7, 2)

    # 目标达成率：基于最早与最新体重相对目标体重的进度
    first_w = db.query(WeightRecord).filter(
        WeightRecord.user_id == user_id
    ).order_by(WeightRecord.record_date.asc()).first()
    last_w = db.query(WeightRecord).filter(
        WeightRecord.user_id == user_id
    ).order_by(WeightRecord.record_date.desc()).first()
    goal_rate = 0.0
    if first_w and last_w and user and user.target_weight != first_w.weight:
        denom = first_w.weight - user.target_weight
        if denom != 0:
            goal_rate = round((first_w.weight - last_w.weight) / denom * 100, 1)
            goal_rate = max(0.0, min(100.0, goal_rate))

    return {
        "days": days_str,
        "intake": intake,
        "burned": burned,
        "avg_weight": avg_weight,
        "avg_deficit": avg_deficit,
        "goal_rate": goal_rate,
    }


def weight_trend(db: Session, user_id: int, range_type: str) -> dict:
    """体重趋势：range=day(1) / week(7) / month(30)。"""
    end = date.today()
    days_map = {"day": 1, "week": 7, "month": 30}
    n = days_map.get(range_type, 7)
    start = end - timedelta(days=n - 1)
    recs = (
        db.query(WeightRecord)
        .filter(
            WeightRecord.user_id == user_id,
            WeightRecord.record_date >= start,
            WeightRecord.record_date <= end,
        )
        .order_by(WeightRecord.record_date)
        .all()
    )
    user = db.query(User).filter(User.id == user_id).first()
    target = user.target_weight if user else 0
    return {
        "dates": [r.record_date.strftime("%Y-%m-%d") for r in recs],
        "weights": [r.weight for r in recs],
        "target_weight": target,
    }


def nutrient_trend_stat(db: Session, user_id: int, days: int) -> dict:
    """营养趋势：近 N 天每日热量/蛋白/脂肪/碳水。"""
    end = date.today()
    dates = _date_list(end, max(1, days))
    calorie, protein, fat, carbohydrate = [], [], [], []
    for d in dates:
        row = db.query(
            func.coalesce(func.sum(DietRecord.calorie), 0.0),
            func.coalesce(func.sum(DietRecord.protein), 0.0),
            func.coalesce(func.sum(DietRecord.fat), 0.0),
            func.coalesce(func.sum(DietRecord.carbohydrate), 0.0),
        ).filter(DietRecord.user_id == user_id, DietRecord.record_date == d).first()
        calorie.append(round(float(row[0] or 0), 2))
        protein.append(round(float(row[1] or 0), 2))
        fat.append(round(float(row[2] or 0), 2))
        carbohydrate.append(round(float(row[3] or 0), 2))
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in dates],
        "calorie": calorie,
        "protein": protein,
        "fat": fat,
        "carbohydrate": carbohydrate,
    }
