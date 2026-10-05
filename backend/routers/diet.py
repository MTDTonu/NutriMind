"""饮食路由：增删改查、当日汇总。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date

from database.db import get_db
from middleware.auth import get_current_user_id
from schemas.diet import DietAdd, DietUpdate, DietOut, DietToday
from services.diet_service import add_diet, list_diet, update_diet, delete_diet, today_diet
from services.user_service import mark_checkin
from utils.common import resp, parse_date, today

router = APIRouter(prefix="/api/v1/diet", tags=["饮食"])


@router.post("/add")
def add_diet_record(
    body: DietAdd,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """新增饮食记录。"""
    rec = add_diet(db, user_id, body)
    # 记录饮食即视为当日打卡
    mark_checkin(db, user_id, parse_date(body.record_date))
    return resp(200, "success", DietOut.model_validate(rec).model_dump())


@router.get("/list")
def list_diet_records(
    record_date: str = Query(..., description="YYYY-MM-DD"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """按日期列出饮食记录。"""
    d = parse_date(record_date)
    recs = list_diet(db, user_id, d)
    return resp(200, "success", {
        "records": [DietOut.model_validate(r).model_dump() for r in recs]
    })


@router.put("/{record_id}")
def update_diet_record(
    record_id: int,
    body: DietUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """更新指定饮食记录。"""
    rec = update_diet(db, user_id, record_id, body)
    return resp(200, "success", DietOut.model_validate(rec).model_dump())


@router.delete("/{record_id}")
def delete_diet_record(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """删除指定饮食记录。"""
    delete_diet(db, user_id, record_id)
    return resp(200, "success", {"success": True})


@router.get("/today")
def diet_today(
    date: str = Query(None, description="YYYY-MM-DD，缺省为今天"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """当日饮食汇总。"""
    # 注意：形参名为 date，会遮蔽 datetime.date，因此缺省值必须用 utils.common.today()
    d = parse_date(date) if date else today()
    summary = today_diet(db, user_id, d)
    summary["items"] = [DietOut.model_validate(r).model_dump() for r in summary["items"]]
    return resp(200, "success", DietToday(**summary).model_dump())
