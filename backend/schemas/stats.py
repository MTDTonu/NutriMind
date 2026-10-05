"""统计相关 Pydantic 模型。"""
from pydantic import BaseModel
from typing import List, Optional


class DailyStat(BaseModel):
    """每日统计。"""
    date: str
    intake_calorie: float
    burned_calorie: float
    net: float
    weight: Optional[float] = None
    recommend_calorie: float
    remain: float


class WeeklyStat(BaseModel):
    """每周统计。"""
    days: List[str]
    intake: List[float]
    burned: List[float]
    avg_weight: Optional[float] = None
    avg_deficit: float
    goal_rate: float


class WeightTrend(BaseModel):
    """体重趋势。"""
    dates: List[str]
    weights: List[float]
    target_weight: float


class NutrientTrend(BaseModel):
    """营养趋势。"""
    dates: List[str]
    calorie: List[float]
    protein: List[float]
    fat: List[float]
    carbohydrate: List[float]
