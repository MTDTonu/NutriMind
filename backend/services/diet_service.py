"""饮食服务：增删改查、当日汇总。"""
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import date

from database.models import DietRecord
from utils.common import parse_date
from utils.exceptions import AppException


def add_diet(db: Session, user_id: int, body) -> DietRecord:
    """新增一条饮食记录。"""
    d = parse_date(body.record_date)
    rec = DietRecord(
        user_id=user_id,
        record_date=d,
        meal_type=body.meal_type,
        food_desc=body.food_desc,
        food_image_path=body.food_image_path,
        input_type=body.input_type,
        calorie=body.calorie,
        protein=body.protein,
        fat=body.fat,
        carbohydrate=body.carbohydrate,
        sugar=body.sugar,
        fiber=body.fiber,
        sodium=body.sodium,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def list_diet(db: Session, user_id: int, d: date) -> list:
    """按日期列出饮食记录，按餐型排序。"""
    return (
        db.query(DietRecord)
        .filter(DietRecord.user_id == user_id, DietRecord.record_date == d)
        .order_by(DietRecord.meal_type, DietRecord.id)
        .all()
    )


def update_diet(db: Session, user_id: int, rid: int, body) -> DietRecord:
    """更新饮食记录（仅更新传入字段）。"""
    rec = db.query(DietRecord).filter(
        DietRecord.id == rid, DietRecord.user_id == user_id
    ).first()
    if not rec:
        raise AppException(404, "饮食记录不存在")

    data = body.model_dump(exclude_unset=True)
    if "record_date" in data and data["record_date"]:
        data["record_date"] = parse_date(data["record_date"])
    for key, value in data.items():
        setattr(rec, key, value)

    db.commit()
    db.refresh(rec)
    return rec


def delete_diet(db: Session, user_id: int, rid: int) -> bool:
    """删除饮食记录。"""
    rec = db.query(DietRecord).filter(
        DietRecord.id == rid, DietRecord.user_id == user_id
    ).first()
    if not rec:
        raise AppException(404, "饮食记录不存在")
    db.delete(rec)
    db.commit()
    return True


def today_diet(db: Session, user_id: int, d: date) -> dict:
    """当日饮食汇总。"""
    recs = list_diet(db, user_id, d)
    total_calorie = sum(r.calorie for r in recs)
    total_protein = sum(r.protein for r in recs)
    total_fat = sum(r.fat for r in recs)
    total_carbohydrate = sum(r.carbohydrate for r in recs)
    total_sugar = sum(r.sugar for r in recs)
    total_fiber = sum(r.fiber for r in recs)
    total_sodium = sum(r.sodium for r in recs)
    return {
        "date": d.strftime("%Y-%m-%d"),
        "total_calorie": round(total_calorie, 2),
        "total_protein": round(total_protein, 2),
        "total_fat": round(total_fat, 2),
        "total_carbohydrate": round(total_carbohydrate, 2),
        "total_sugar": round(total_sugar, 2),
        "total_fiber": round(total_fiber, 2),
        "total_sodium": round(total_sodium, 2),
        "items": recs,
    }
