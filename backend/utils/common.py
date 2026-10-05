"""通用工具：统一响应封装、日期处理。"""
from datetime import datetime, date
from typing import Any

from utils.exceptions import AppException


def resp(code: int = 200, message: str = "success", data: Any = None) -> dict:
    """统一响应结构：{"code":..., "message":..., "data":...}。"""
    return {"code": code, "message": message, "data": data}


def parse_date(value) -> date:
    """将字符串 'YYYY-MM-DD' 或 date 对象解析为 date；非法格式抛出 400。"""
    if value is None:
        raise AppException(400, "日期参数不能为空")
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        raise AppException(400, "日期格式应为 YYYY-MM-DD")
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        raise AppException(400, f"日期格式非法：{value!r}，应为 YYYY-MM-DD")


def today() -> date:
    """返回今天日期。"""
    return date.today()


def now() -> datetime:
    """返回当前时间。"""
    return datetime.now()


def date_to_str(d: date) -> str:
    """date -> 'YYYY-MM-DD'。"""
    return d.strftime("%Y-%m-%d")
