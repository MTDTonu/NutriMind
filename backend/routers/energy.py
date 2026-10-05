"""能量引擎路由：自适应 TDEE 反推、周校准、目标双模式。

接入口径遵循「先给结论，再给证据」：
- /target 返回可直接渲染的目标方案；
- /adaptive 返回反推过程与数据充分性；
- /calibrate 执行写入。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database.db import get_db
from database.models import User
from middleware.auth import get_current_user_id
from schemas.energy import TargetSetBody
from services.energy_service import current_plan, calibrate, set_target, adaptive_tdee
from utils.common import resp
from utils.exceptions import AppException

router = APIRouter(prefix="/api/v1/energy", tags=["能量引擎"])


def _load_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(404, "用户不存在")
    return user


@router.get("/target")
def get_target(
    window: int = Query(14, ge=7, le=60),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """当前目标方案（优先使用已校准的自适应 TDEE）。"""
    user = _load_user(db, user_id)
    return resp(200, "success", current_plan(db, user, window))


@router.get("/adaptive")
def get_adaptive(
    window: int = Query(14, ge=7, le=60),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """反推真实 TDEE：返回数据充分性、计算过程与安全夹逼情况。"""
    user = _load_user(db, user_id)
    return resp(200, "success", adaptive_tdee(db, user, window))


@router.post("/calibrate")
def do_calibrate(
    window: int = Query(14, ge=7, le=60),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """执行一次校准：可信则写入 tdee_adaptive 并重算推荐摄入。"""
    user = _load_user(db, user_id)
    return resp(200, "success", calibrate(db, user, window, persist=True))


@router.post("/target")
def post_target(
    body: TargetSetBody,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """切换目标模式（热量缺口 / 每周速率）并重算推荐摄入。"""
    user = _load_user(db, user_id)
    return resp(200, "success", set_target(db, user, body.mode, body.target_rate, body.target_deficit))
