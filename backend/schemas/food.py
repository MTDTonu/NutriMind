"""食物库相关 Pydantic 模型。"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class PortionOut(BaseModel):
    """份量单位输出。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    grams: float
    is_default: int = 0


class FoodOut(BaseModel):
    """食物输出：统一携带来源与置信度，界面须据此标注。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    aliases: Optional[str] = None
    category: str
    category_label: Optional[str] = None
    source: str
    confidence: float
    brand: Optional[str] = None
    barcode: Optional[str] = None
    owner_user_id: Optional[int] = None

    calorie: float
    protein: float
    fat: float
    carbohydrate: float
    sugar: float
    fiber: float
    sodium: float
    gi: Optional[int] = None

    use_count: int = 0
    portions: List[PortionOut] = []
    # 非 ORM 字段：当前用户是否收藏
    favorited: int = 0


class FoodSearchItem(BaseModel):
    """搜索结果条目（轻量）。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    category_label: Optional[str] = None
    source: str
    confidence: float
    calorie: float
    protein: float
    fat: float
    carbohydrate: float
    default_portion_label: Optional[str] = None
    default_portion_grams: Optional[float] = None
    use_count: int = 0
    favorited: int = 0


class FoodCreate(BaseModel):
    """自定义食物：营养字段按每 100g 填写。"""
    name: str = Field(..., min_length=1, max_length=80)
    aliases: Optional[str] = Field(None, max_length=255)
    category: str = "user"
    brand: Optional[str] = Field(None, max_length=80)
    barcode: Optional[str] = Field(None, max_length=40)
    calorie: float = Field(0, ge=0)
    protein: float = Field(0, ge=0)
    fat: float = Field(0, ge=0)
    carbohydrate: float = Field(0, ge=0)
    sugar: float = Field(0, ge=0)
    fiber: float = Field(0, ge=0)
    sodium: float = Field(0, ge=0)
    gi: Optional[int] = Field(None, ge=0, le=110)
    portion_label: Optional[str] = Field(None, max_length=30)
    portion_grams: Optional[float] = Field(None, gt=0)


class QuickAddBody(BaseModel):
    """从食物库一键写入饮食记录。"""
    record_date: str = Field(..., description="YYYY-MM-DD")
    meal_type: int = Field(..., ge=1, le=4, description="1 早 / 2 午 / 3 晚 / 4 加餐")
    food_id: int = Field(..., description="目标食物 ID")
    # 二选一：给了 portion_id 用份量克重，否则直接用 grams（默认 100g）
    portion_id: Optional[int] = None
    grams: Optional[float] = Field(None, gt=0, le=5000)
    # 份数，默认 1（如「2 碗饭」）
    quantity: float = Field(1, gt=0, le=20)
    food_image_path: Optional[str] = None


class QuickAddOut(BaseModel):
    """快捷录入结果：把换算过程一并返回，便于界面给出「X 碗 ≈ XXXg」。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_date: str
    meal_type: int
    food_desc: str
    input_type: int
    calorie: float
    protein: float
    fat: float
    carbohydrate: float
    sugar: float
    fiber: float
    sodium: float
    food_image_path: Optional[str] = None
    create_time: Optional[datetime] = None

    # 换算证据
    food_id: int
    grams: float
    quantity: float
    portion_label: Optional[str] = None