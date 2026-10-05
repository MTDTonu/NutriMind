"""认证服务：注册、登录、获取当前用户。"""
from sqlalchemy.orm import Session

from database.models import User
from utils.security import hash_password, verify_password
from services.calc_service import calc_bmr, calc_tdee, calc_recommend
from utils.exceptions import AppException


def register_user(db: Session, body) -> User:
    """注册新用户，计算并保存代谢指标。"""
    # 用户名唯一校验
    exist = db.query(User).filter(User.username == body.username).first()
    if exist:
        raise AppException(400, "用户名已存在")

    # 计算代谢指标
    bmr = calc_bmr(body.gender, body.age, body.height, body.current_weight)
    tdee = calc_tdee(bmr, body.activity_level)
    recommend = calc_recommend(tdee, bmr)

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        gender=body.gender,
        age=body.age,
        height=body.height,
        current_weight=body.current_weight,
        target_weight=body.target_weight,
        activity_level=body.activity_level,
        bmr=round(bmr, 2),
        tdee=round(tdee, 2),
        recommend_calorie=round(recommend, 2),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, username: str, password: str) -> User:
    """校验用户名密码，返回用户对象。"""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise AppException(401, "用户名或密码错误")
    return user


def get_current_user(db: Session, user_id: int) -> User:
    """根据用户 ID 获取用户，不存在则抛 401。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(401, "用户不存在")
    return user
