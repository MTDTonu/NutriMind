"""运动路由：新增、列表、删除。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from pydantic import BaseModel, Field, ConfigDict

from database.db import get_db
from database.models import ExerciseRecord
from middleware.auth import get_current_user_id
from services.user_service import mark_checkin
from utils.common import resp, parse_date
from utils.exceptions import AppException

router = APIRouter(prefix="/api/v1/exercise", tags=["运动"])


class ExerciseAdd(BaseModel):
    record_date: str = Field(..., description="YYYY-MM-DD")
    exercise_type: str = Field(..., description="运动类型，如 跑步/游泳")
    duration: int = Field(..., gt=0, description="时长（分钟）")
    calorie_burn: float = Field(..., ge=0, description="消耗热量")


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    record_date: date
    exercise_type: str
    duration: int
    calorie_burn: float


@router.post("/add")
def add_exercise(
    body: ExerciseAdd,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """新增运动记录。"""
    rec = ExerciseRecord(
        user_id=user_id,
        record_date=parse_date(body.record_date),
        exercise_type=body.exercise_type,
        duration=body.duration,
        calorie_burn=body.calorie_burn,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    mark_checkin(db, user_id, parse_date(body.record_date))
    return resp(200, "success", ExerciseOut.model_validate(rec).model_dump())


@router.get("/list")
def list_exercise(
    date: str = Query(None, description="YYYY-MM-DD，指定则只返回当天记录；缺省返回全部"),
    start: str = Query(None, description="YYYY-MM-DD，区间起点（含）"),
    end: str = Query(None, description="YYYY-MM-DD，区间终点（含）"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出运动记录（按日期倒序）。

    传入 date 时只返回当天，供「今日运动」使用；
    传入 start/end 时返回区间内记录（供周/月小结使用）；否则返回该用户全部记录。
    """
    q = db.query(ExerciseRecord).filter(ExerciseRecord.user_id == user_id)
    if date:
        q = q.filter(ExerciseRecord.record_date == parse_date(date))
    else:
        if start:
            q = q.filter(ExerciseRecord.record_date >= parse_date(start))
        if end:
            q = q.filter(ExerciseRecord.record_date <= parse_date(end))
    recs = q.order_by(
        ExerciseRecord.record_date.desc(), ExerciseRecord.id.desc()
    ).all()
    return resp(200, "success", {
        "records": [ExerciseOut.model_validate(r).model_dump() for r in recs]
    })


@router.get("/weekly")
def weekly_exercise(
    days: int = Query(7, ge=1, le=60, description="统计天数，默认 7"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """按天聚合运动消耗，供「本周小结」使用。

    返回按日期升序的每日汇总：total_calorie / total_minutes / count。
    没有记录的日期会补 0，保证前端图表横轴连续。
    """
    from datetime import timedelta

    today = date.today()
    start_day = today - timedelta(days=days - 1)

    recs = (
        db.query(ExerciseRecord)
        .filter(
            ExerciseRecord.user_id == user_id,
            ExerciseRecord.record_date >= start_day,
            ExerciseRecord.record_date <= today,
        )
        .all()
    )

    buckets = {}
    d = start_day
    while d <= today:
        buckets[d.isoformat()] = {"date": d.isoformat(), "calorie": 0.0, "minutes": 0, "count": 0}
        d += timedelta(days=1)

    for r in recs:
        key = r.record_date.isoformat() if isinstance(r.record_date, date) else str(r.record_date)
        b = buckets.get(key)
        if not b:
            continue
        b["calorie"] += float(r.calorie_burn or 0)
        b["minutes"] += int(r.duration or 0)
        b["count"] += 1

    days_out = []
    for b in buckets.values():
        days_out.append({
            "date": b["date"],
            "calorie": round(b["calorie"], 1),
            "minutes": b["minutes"],
            "count": b["count"],
        })

    total_calorie = round(sum(x["calorie"] for x in days_out), 1)
    total_minutes = sum(x["minutes"] for x in days_out)
    active_days = sum(1 for x in days_out if x["count"] > 0)

    return resp(200, "success", {
        "days": days_out,
        "total_calorie": total_calorie,
        "total_minutes": total_minutes,
        "active_days": active_days,
        "span_days": days,
    })


@router.delete("/{record_id}")
def delete_exercise(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """删除运动记录。"""
    rec = db.query(ExerciseRecord).filter(
        ExerciseRecord.id == record_id, ExerciseRecord.user_id == user_id
    ).first()
    if not rec:
        raise AppException(404, "运动记录不存在")
    db.delete(rec)
    db.commit()
    return resp(200, "success", {"success": True})
