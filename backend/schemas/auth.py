"""认证相关 Pydantic 模型。"""
from pydantic import BaseModel, Field
from schemas.user import UserOut


class RegisterRequest(BaseModel):
    """注册请求。"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    gender: int = Field(..., ge=0, le=1, description="0 女 / 1 男")
    age: int = Field(..., ge=1, le=120)
    height: float = Field(..., gt=0, description="cm")
    current_weight: float = Field(..., gt=0, description="kg")
    target_weight: float = Field(..., gt=0, description="kg")
    activity_level: int = Field(..., ge=1, le=4, description="1 久坐 / 2 轻度 / 3 中度 / 4 重度")


class LoginRequest(BaseModel):
    """登录请求。"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class AuthResponse(BaseModel):
    """登录/注册返回：token + 用户信息。"""
    token: str
    user: UserOut
