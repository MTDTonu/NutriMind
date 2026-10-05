"""认证路由：注册、登录、获取当前用户信息。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db import get_db
from middleware.auth import get_current_user_id
from schemas.auth import RegisterRequest, LoginRequest
from schemas.user import UserOut
from services.auth_service import register_user, login_user, get_current_user
from services.user_service import mark_checkin
from utils.security import create_access_token
from utils.common import resp
from datetime import date

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册：计算代谢指标并存库，返回 token 与用户信息。"""
    user = register_user(db, body)
    # 注册当天自动打卡
    mark_checkin(db, user.id, date.today())
    token = create_access_token(user.id)
    return resp(200, "success", {
        "token": token,
        "user": UserOut.model_validate(user).model_dump(),
    })


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """用户登录：校验密码，返回 token 与用户信息。"""
    user = login_user(db, body.username, body.password)
    token = create_access_token(user.id)
    return resp(200, "success", {
        "token": token,
        "user": UserOut.model_validate(user).model_dump(),
    })


@router.get("/info")
def info(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """获取当前登录用户信息。"""
    user = get_current_user(db, user_id)
    return resp(200, "success", UserOut.model_validate(user).model_dump())
