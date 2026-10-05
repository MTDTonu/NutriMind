"""将用户的大模型配置同步写回 .env。

「我的」页保存配置后调用，使 .env 与数据库保持一致：
- 写 TEXT_/VISION_/ASR_ 三组 PROVIDER/API_KEY/MODEL/BASE_URL
- 若文字能力使用智谱，则同步 ZHIPU_API_KEY（兼容老代码与环境变量读取）

使用 python-dotenv 的 set_key，保留 .env 中其它键值。
"""
import os
from pathlib import Path

from dotenv import set_key

# backend/.env（本文件位于 backend/utils/，故上级目录即 backend）
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _set(key: str, value: str):
    try:
        set_key(str(ENV_PATH), key, value or "", quote_mode="never")
    except Exception:  # noqa: BLE001
        # .env 不存在或写入失败时静默忽略，不影响主流程（数据库仍是真实来源）
        pass


def sync_ai_settings_to_env(row):
    """把一行 UserAISettings 同步到 .env。"""
    for cap in ("text", "vision", "asr"):
        prov = getattr(row, f"{cap}_provider") or ""
        key = getattr(row, f"{cap}_api_key") or ""
        model = getattr(row, f"{cap}_model") or ""
        base = getattr(row, f"{cap}_base_url") or ""
        up = cap.upper()
        _set(f"{up}_PROVIDER", prov)
        _set(f"{up}_API_KEY", key)
        _set(f"{up}_MODEL", model)
        if base:
            _set(f"{up}_BASE_URL", base)

    # 兼容：文字用智谱时同步 ZHIPU_API_KEY
    if row.text_provider == "zhipu" and row.text_api_key:
        _set("ZHIPU_API_KEY", row.text_api_key)
