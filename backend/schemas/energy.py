"""能量引擎相关 Pydantic 模型。"""
from pydantic import BaseModel, Field
from typing import Optional, List


class TargetSetBody(BaseModel):
    """设置目标模式。

    deficit：按每日热量缺口（更直观，适合大多数人）
    rate   ：按每周减重速率（更贴近用户真正的目标口径）
    """
    mode: str = Field(..., description="deficit=热量缺口 / rate=每周减重")
    target_rate: Optional[float] = Field(None, ge=0.1, le=1.5, description="kg/周，rate 模式必填")
    target_deficit: Optional[float] = Field(None, ge=0, le=1500, description="kcal/日")
