"""用户相关 Pydantic 模型。"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime


class UserOut(BaseModel):
    """用户输出模型（不含密码哈希）。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    gender: int
    age: int
    height: float
    current_weight: float
    target_weight: float
    activity_level: int
    bmr: float
    tdee: float
    recommend_calorie: float
    diet_preference: Optional[str] = None
    diet_avoid: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None


class ProfileUpdate(BaseModel):
    """修改个人信息（可选字段，仅更新传入项）。"""
    gender: Optional[int] = Field(None, ge=0, le=1)
    age: Optional[int] = Field(None, ge=1, le=120)
    height: Optional[float] = Field(None, gt=0)
    current_weight: Optional[float] = Field(None, gt=0)
    target_weight: Optional[float] = Field(None, gt=0)
    activity_level: Optional[int] = Field(None, ge=1, le=4)


class PreferenceUpdate(BaseModel):
    """修改饮食偏好（JSON 字符串）与忌口。"""
    diet_preference: Optional[str] = Field(None, description="饮食偏好，逗号分隔")
    diet_avoid: Optional[str] = Field(None, description="忌口 / 过敏，纯文本")


class CheckinOut(BaseModel):
    """打卡统计输出（全部为数据库真实值）。"""
    continuous_days: int
    total_days: int
    checked_today: bool
    today: str
    month: str
    dates: list = Field(default_factory=list)


class MetricsOut(BaseModel):
    """代谢指标输出。"""
    bmr: float
    tdee: float
    recommend_calorie: float
    activity_level: int
    bmi: float
