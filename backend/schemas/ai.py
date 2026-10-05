"""AI 相关 Pydantic 模型。"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any


class FoodItem(BaseModel):
    """识别出的单个食物营养信息。

    数值字段均给默认值：模型偶发漏字段时降级为 0，而非直接 500。
    """
    model_config = ConfigDict(extra="ignore")

    name: str
    # 数量（个 / 份）。同一张图里可能有多个相同食物，用它区分，默认 1。
    quantity: float = 1
    weight: float = 0
    calorie: float = 0
    protein: float = 0
    fat: float = 0
    carbohydrate: float = 0
    sugar: float = 0
    fiber: float = 0
    sodium: float = 0


class RecognizeResponse(BaseModel):
    """图片识别返回。"""
    food_list: List[FoodItem]
    total_calorie: float
    image_url: Optional[str] = None


class PlanFood(BaseModel):
    """食谱中的单个菜品。"""
    model_config = ConfigDict(extra="ignore")

    name: str
    weight: str
    calorie: float
    practice: str


class PlanResponse(BaseModel):
    """一日食谱返回。"""
    breakfast: List[PlanFood]
    lunch: List[PlanFood]
    dinner: List[PlanFood]
    total_calorie: float
    adapt_desc: str


class PlanRequest(BaseModel):
    """生成食谱请求（date 可选，默认今天）。"""
    date: Optional[str] = None


class ChatRequest(BaseModel):
    """AI 对话请求。"""
    message: str
    history: Optional[List[Any]] = None
    # 用户长期记忆（前端维护，随请求注入 system prompt）
    memories: Optional[List[str]] = None


class ChatResponse(BaseModel):
    """AI 对话返回。"""
    reply: str


class DailyReviewResponse(BaseModel):
    """每日复盘返回。"""
    review: str


class SessionCreate(BaseModel):
    """新建会话（title 可选，缺省为「新对话」）。"""
    title: Optional[str] = None


class RenameRequest(BaseModel):
    """会话改名。"""
    title: str = Field(..., min_length=1, max_length=100)


class SessionOut(BaseModel):
    """会话概要（列表项 / 详情）。"""
    model_config = ConfigDict(from_attributes=True)

    sid: str
    title: str
    updated_at: str
    message_count: int = 0
    preview: str = ""


class MessageOut(BaseModel):
    """会话内的单条消息。"""
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    image: Optional[str] = None
    created_at: str


class SessionDetail(BaseModel):
    """会话详情：元数据 + 消息列表。"""
    sid: str
    title: str
    updated_at: str
    messages: List[MessageOut] = []


class MemoryRequest(BaseModel):
    """新增 / 删除长期记忆。"""
    text: str = Field(..., min_length=1, max_length=200)


class TurnRequest(BaseModel):
    """一次完整对话回合：用户消息 + 助手回复，由前端在流式结束后统一落库。"""
    user_content: str = Field(..., min_length=1)
    assistant_content: str = ""
    image: Optional[str] = None
