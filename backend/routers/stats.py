"""统计路由：每日、每周、体重趋势、营养趋势。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.db import get_db
from middleware.auth import get_current_user_id
from schemas.stats import DailyStat, WeeklyStat, WeightTrend, NutrientTrend
from services.stats_service import daily_stat, weekly_stat, weight_trend, nutrient_trend_stat
from utils.common import resp, parse_date

router = APIRouter(prefix="/api/v1/stats", tags=["统计"])


@router.get("/daily")
def stats_daily(
    date: str = Query(None, description="YYYY-MM-DD，缺省为今天"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """每日统计：摄入、消耗、净热量、体重、推荐摄入、剩余。"""
    from datetime import date as _date
    d = parse_date(date) if date else _date.today()
    data = daily_stat(db, user_id, d)
    return resp(200, "success", DailyStat(**data).model_dump())


@router.get("/weekly")
def stats_weekly(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """近 7 天统计。"""
    data = weekly_stat(db, user_id)
    return resp(200, "success", WeeklyStat(**data).model_dump())


@router.get("/weight-trend")
def stats_weight_trend(
    range: str = Query("week", description="day | week | month"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """体重趋势。"""
    data = weight_trend(db, user_id, range)
    return resp(200, "success", WeightTrend(**data).model_dump())


@router.get("/nutrient-trend")
def stats_nutrient_trend(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """营养趋势：近 N 天每日热量/蛋白/脂肪/碳水。"""
    data = nutrient_trend_stat(db, user_id, days)
    return resp(200, "success", NutrientTrend(**data).model_dump())
