"""体重路由：新增、列表、删除。

规则：同一天多条只保留最新；新增/更新时计算与上一记录的体重差值（weight_diff）。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

from database.db import get_db
from database.models import WeightRecord
from middleware.auth import get_current_user_id
from services.user_service import mark_checkin
from utils.common import resp, parse_date
from utils.exceptions import AppException

router = APIRouter(prefix="/api/v1/weight", tags=["体重"])


class WeightAdd(BaseModel):
    record_date: str = Field(..., description="YYYY-MM-DD")
    weight: float = Field(..., gt=0)
    body_fat: Optional[float] = None
    waist: Optional[float] = None
    remark: Optional[str] = None


class WeightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    record_date: date
    weight: float
    body_fat: Optional[float] = None
    waist: Optional[float] = None
    weight_diff: float
    remark: Optional[str] = None


def _prev_weight(db: Session, user_id: int, before: date) -> Optional[WeightRecord]:
    """取早于 before 的最近一条体重记录。"""
    return (
        db.query(WeightRecord)
        .filter(WeightRecord.user_id == user_id, WeightRecord.record_date < before)
        .order_by(WeightRecord.record_date.desc(), WeightRecord.create_time.desc())
        .first()
    )


def _recompute_weight_diff(db: Session, user_id: int) -> None:
    """按日期升序重算该用户全部体重记录的差值（weight_diff）。

    旧实现只在新增/覆盖时按「上一条记录」推算当前记录的差值并落库，导致：
    - 补录历史日期（在两条现有记录中间插入）→ 其后所有记录的 weight_diff 全部偏移；
    - 删除某条记录 → 其后记录的 weight_diff 仍指向已删除的基线，脏值；
    - 改某条记录的重量 → 其后记录的差值不联动。
    现改为：任一增删改后，对全量记录按 (日期, 创建时间) 升序重算，首条 diff=0。
    """
    rows = (
        db.query(WeightRecord)
        .filter(WeightRecord.user_id == user_id)
        .order_by(WeightRecord.record_date.asc(), WeightRecord.create_time.asc())
        .all()
    )
    prev = None
    for r in rows:
        r.weight_diff = round(r.weight - prev.weight, 2) if prev else 0.0
        prev = r
    db.commit()


@router.post("/add")
def add_weight(
    body: WeightAdd,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """新增/覆盖当日体重，并计算差值。"""
    d = parse_date(body.record_date)
    exist = db.query(WeightRecord).filter(
        WeightRecord.user_id == user_id, WeightRecord.record_date == d
    ).first()

    prev = _prev_weight(db, user_id, d)
    diff = round(body.weight - prev.weight, 2) if prev else 0.0

    if exist:
        # 同一天覆盖最新值
        exist.weight = body.weight
        exist.body_fat = body.body_fat
        exist.waist = body.waist
        exist.remark = body.remark
        exist.weight_diff = diff
        db.commit()
        db.refresh(exist)
        rec = exist
    else:
        rec = WeightRecord(
            user_id=user_id,
            record_date=d,
            weight=body.weight,
            body_fat=body.body_fat,
            waist=body.waist,
            weight_diff=diff,
            remark=body.remark,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

    mark_checkin(db, user_id, d)
    # 重算全链，修正插入/覆盖历史日期导致的后续 weight_diff 偏移
    _recompute_weight_diff(db, user_id)
    rec = db.query(WeightRecord).filter(WeightRecord.id == rec.id).first()
    return resp(200, "success", {
        "record": WeightOut.model_validate(rec).model_dump(),
        "weight_diff": rec.weight_diff,
    })


@router.get("/list")
def list_weight(
    type: str = Query("day", description="day | week | month"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出体重记录：day(今日) / week(近7天) / month(近30天)。"""
    end = date.today()
    days_map = {"day": 1, "week": 7, "month": 30}
    n = days_map.get(type, 1)
    start = end - timedelta(days=n - 1)
    recs = (
        db.query(WeightRecord)
        .filter(
            WeightRecord.user_id == user_id,
            WeightRecord.record_date >= start,
            WeightRecord.record_date <= end,
        )
        .order_by(WeightRecord.record_date.desc())
        .all()
    )
    return resp(200, "success", {
        "records": [WeightOut.model_validate(r).model_dump() for r in recs]
    })


@router.delete("/{record_id}")
def delete_weight(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """删除体重记录。"""
    rec = db.query(WeightRecord).filter(
        WeightRecord.id == record_id, WeightRecord.user_id == user_id
    ).first()
    if not rec:
        raise AppException(404, "体重记录不存在")
    db.delete(rec)
    db.commit()
    # 删除后重算全链，修正其后记录的 weight_diff 基线
    _recompute_weight_diff(db, user_id)
    return resp(200, "success", {"success": True})
