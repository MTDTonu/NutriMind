"""数据导入导出与提醒设置的请求/响应结构。"""
from pydantic import BaseModel, field_validator
from typing import Optional
import re

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ReminderUpdate(BaseModel):
    """提醒设置更新：全部可选，未传字段保持原值。"""

    meal_enabled: Optional[int] = None
    breakfast_time: Optional[str] = None
    lunch_time: Optional[str] = None
    dinner_time: Optional[str] = None

    weigh_enabled: Optional[int] = None
    weigh_time: Optional[str] = None

    water_enabled: Optional[int] = None
    water_start: Optional[str] = None
    water_end: Optional[str] = None
    water_interval_hours: Optional[int] = None

    quiet_enabled: Optional[int] = None
    quiet_start: Optional[str] = None
    quiet_end: Optional[str] = None

    @field_validator(
        "breakfast_time",
        "lunch_time",
        "dinner_time",
        "weigh_time",
        "water_start",
        "water_end",
        "quiet_start",
        "quiet_end",
    )
    @classmethod
    def check_time(cls, v):
        if v is None:
            return v
        if not _TIME_RE.match(v):
            raise ValueError("时间格式须为 HH:MM，如 08:30")
        return v

    @field_validator("meal_enabled", "weigh_enabled", "water_enabled", "quiet_enabled")
    @classmethod
    def check_flag(cls, v):
        if v is None:
            return v
        return 1 if int(v) else 0

    @field_validator("water_interval_hours")
    @classmethod
    def check_interval(cls, v):
        if v is None:
            return v
        v = int(v)
        if not 1 <= v <= 6:
            raise ValueError("饮水提醒间隔须在 1~6 小时之间")
        return v
