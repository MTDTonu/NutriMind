"""饮水路由：新增（同日期累加）、查询当日。

目标饮水量 = 体重(kg) * 35 ml。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from pydantic import BaseModel, Field, ConfigDict

from database.db import get_db
from database.models import WaterRecord, User
from middleware.auth import get_current_user_id
from services.user_service import mark_checkin
from utils.common import resp, parse_date, today

router = APIRouter(prefix="/api/v1/water", tags=["饮水"])


class WaterAdd(BaseModel):
    record_date: str = Field(..., description="YYYY-MM-DD")
    amount: int = Field(..., gt=0, description="本次饮水量（ml）")


class WaterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    record_date: date
    total_amount: int
    target_amount: int


@router.post("/add")
def add_water(
    body: WaterAdd,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """记录饮水：同日期累加，目标量按体重*35ml。"""
    d = parse_date(body.record_date)
    user = db.query(User).filter(User.id == user_id).first()
    target = int((user.current_weight if user else 60) * 35)

    exist = db.query(WaterRecord).filter(
        WaterRecord.user_id == user_id, WaterRecord.record_date == d
    ).first()
    if exist:
        exist.total_amount += body.amount
        db.commit()
        db.refresh(exist)
        rec = exist
    else:
        rec = WaterRecord(
            user_id=user_id,
            record_date=d,
            total_amount=body.amount,
            target_amount=target,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

    mark_checkin(db, user_id, d)
    return resp(200, "success", {
        "total_amount": rec.total_amount,
        "target_amount": rec.target_amount,
    })


@router.get("/today")
def water_today(
    date: str = Query(None, description="YYYY-MM-DD，缺省为今天"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """查询当日饮水总量与目标量。"""
    d = parse_date(date) if date else today()
    rec = db.query(WaterRecord).filter(
        WaterRecord.user_id == user_id, WaterRecord.record_date == d
    ).first()
    total = rec.total_amount if rec else 0
    target = rec.target_amount if rec else 0
    if not rec:
        user = db.query(User).filter(User.id == user_id).first()
        target = int((user.current_weight if user else 60) * 35)
    return resp(200, "success", {
        "total_amount": total,
        "target_amount": target,
        "date": d.strftime("%Y-%m-%d"),
    })
