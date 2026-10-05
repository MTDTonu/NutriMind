"""用户路由：资料修改、偏好设置、指标查询。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db import get_db
from middleware.auth import get_current_user_id
from schemas.user import ProfileUpdate, PreferenceUpdate, MetricsOut, UserOut, CheckinOut
from schemas.ai_settings import (
    AISettingsUpdate,
    AISettingsOut,
    CapabilityOut,
    PROVIDER_LABELS,
    PROVIDER_DEFAULTS,
    PROVIDER_FREE_MODELS,
)
from services.user_service import (
    update_profile,
    update_preference,
    get_metrics,
    get_checkin_stats,
    get_user_ai_settings,
    upsert_user_ai_settings,
)
from utils.env_sync import sync_ai_settings_to_env
from utils.crypto import decrypt_secret
from utils.common import resp, today

router = APIRouter(prefix="/api/v1/user", tags=["用户"])


@router.put("/profile")
def update_user_profile(
    body: ProfileUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """修改个人信息并自动重算代谢指标。"""
    user = update_profile(db, user_id, body)
    return resp(200, "success", UserOut.model_validate(user).model_dump())


@router.put("/preference")
def update_user_preference(
    body: PreferenceUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """修改饮食偏好与忌口。"""
    user = update_preference(
        db, user_id, body.diet_preference, getattr(body, "diet_avoid", None)
    )
    return resp(200, "success", UserOut.model_validate(user).model_dump())


@router.get("/metrics")
def user_metrics(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """查询当前用户的代谢指标与 BMI。"""
    metrics = get_metrics(db, user_id)
    return resp(200, "success", MetricsOut(**metrics).model_dump())


@router.get("/checkin")
def user_checkin(
    month: str = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """查询真实打卡数据：连续天数 / 累计天数 / 当月打卡日期。

    month 形如 '2026-09'，缺省为当月。所有字段均来自 user_checkin 表，无模拟值。
    """
    stats = get_checkin_stats(db, user_id, month=month, on=today())
    return resp(200, "success", CheckinOut(**stats).model_dump())


def _cap_out(row, cap: str) -> CapabilityOut:
    """由配置行构造单套能力的脱敏输出（先解密再脱敏，展示真实 Key 末 4 位）。"""
    key = decrypt_secret(getattr(row, f"{cap}_api_key") or "") if row else ""
    has = bool(key)
    # 仅展示末 4 位，避免泄露；位数不足则统一用 **** 占位
    masked = ("****" + key[-4:]) if has and len(key) >= 4 else ("****" if has else None)
    return CapabilityOut(
        provider=(getattr(row, f"{cap}_provider") or None) if row else None,
        has_key=has,
        masked_key=masked,
        model=(getattr(row, f"{cap}_model") or None) if row else None,
        base_url=(getattr(row, f"{cap}_base_url") or None) if row else None,
    )


@router.get("/ai-settings/providers")
def ai_settings_providers():
    """返回可选厂商及其默认模型，供前端下拉与厂商切换自动填值。"""
    return resp(200, "success", {
        "labels": PROVIDER_LABELS,
        "defaults": PROVIDER_DEFAULTS,
        "free_models": PROVIDER_FREE_MODELS,
    })


@router.get("/ai-settings")
def get_ai_settings(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """读取当前用户的三套大模型配置（api_key 脱敏）。"""
    row = get_user_ai_settings(db, user_id)
    out = AISettingsOut(
        text=_cap_out(row, "text"),
        vision=_cap_out(row, "vision"),
        asr=_cap_out(row, "asr"),
    )
    return resp(200, "success", out.model_dump())


@router.put("/ai-settings")
def put_ai_settings(
    body: AISettingsUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """更新三套大模型配置，并同步写回 .env（保持环境变量与数据库一致）。

    api_key 为空字符串表示「保持原值不修改」，避免误清空。
    """
    data = body.model_dump(exclude_none=True)
    row = upsert_user_ai_settings(db, user_id, data)
    sync_ai_settings_to_env(row)
    out = AISettingsOut(
        text=_cap_out(row, "text"),
        vision=_cap_out(row, "vision"),
        asr=_cap_out(row, "asr"),
    )
    return resp(200, "success", out.model_dump())
