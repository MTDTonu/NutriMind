"""饮食相关 Pydantic 模型。"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date


class DietAdd(BaseModel):
    """新增饮食记录。"""
    record_date: str = Field(..., description="YYYY-MM-DD")
    meal_type: int = Field(..., ge=1, le=4, description="1 早 / 2 午 / 3 晚 / 4 加餐")
    food_desc: str = Field(..., description="食物描述")
    input_type: int = Field(..., ge=1, le=2, description="1 文字 / 2 图片")
    calorie: float = 0
    protein: float = 0
    fat: float = 0
    carbohydrate: float = 0
    sugar: float = 0
    fiber: float = 0
    sodium: float = 0
    food_image_path: Optional[str] = None


class DietUpdate(BaseModel):
    """更新饮食记录（均可选）。"""
    record_date: Optional[str] = None
    meal_type: Optional[int] = Field(None, ge=1, le=4)
    food_desc: Optional[str] = None
    input_type: Optional[int] = Field(None, ge=1, le=2)
    calorie: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbohydrate: Optional[float] = None
    sugar: Optional[float] = None
    fiber: Optional[float] = None
    sodium: Optional[float] = None
    food_image_path: Optional[str] = None


class DietOut(BaseModel):
    """饮食记录输出。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    record_date: date
    meal_type: int
    food_desc: str
    food_image_path: Optional[str] = None
    input_type: int
    calorie: float
    protein: float
    fat: float
    carbohydrate: float
    sugar: float
    fiber: float
    sodium: float
    create_time: Optional[datetime] = None


class DietToday(BaseModel):
    """当日饮食汇总。"""
    date: str
    total_calorie: float
    total_protein: float
    total_fat: float
    total_carbohydrate: float
    total_sugar: float
    total_fiber: float
    total_sodium: float
    items: List[DietOut]
