"""AI 大模型配置相关的 Pydantic 模型。

三套能力（文字 / 视觉理解 / 语言转文字）各自独立配置：
- provider：国内厂商（zhipu / dashscope / volcengine / ernie / custom）
- api_key：密钥（写入时为空字符串表示「保持原值不修改」）
- model：模型名
- base_url：仅 custom 厂商需要
"""
from typing import Optional
from pydantic import BaseModel


# 支持的国内厂商及其默认模型（供前端下拉与默认值参考）
# 各厂商默认模型：
# 智谱默认全部选用【永久免费的 Flash 系列】——文本 glm-4-flash、视觉 glm-4v-flash
# （均实测可用且不计费），避免用户开箱即用就产生费用。
PROVIDER_DEFAULTS = {
    "zhipu": {"text": "glm-4-flash", "vision": "glm-4v-flash", "asr": "glm-4-flash"},
    "dashscope": {"text": "qwen-plus", "vision": "qwen-vl-max", "asr": "paraformer-v2"},
    "volcengine": {"text": "doubao-pro-32k", "vision": "doubao-vision-pro", "asr": "volcengine-asr"},
    "ernie": {"text": "ernie-4.5-8k-preview", "vision": "ernie-4.5-vl-8k-preview", "asr": "ernie-asr"},
    "custom": {"text": "", "vision": "", "asr": ""},
}

PROVIDER_LABELS = {
    "zhipu": "智谱 GLM",
    "dashscope": "阿里云百炼",
    "volcengine": "字节豆包",
    "ernie": "百度文心",
    "custom": "自定义(OpenAI兼容)",
}

# 已确认【永久免费】的模型名（用于前端打「免费」徽标）。
# 智谱 Flash 系列均免费，且已在本机实测可用。
PROVIDER_FREE_MODELS = {
    "zhipu": [
        "glm-4-flash",
        "glm-4-flash-250414",
        "glm-4.7-flash",
        "glm-4v-flash",
        "glm-4.6v-flash",
        "glm-4.1v-thinking-flash",
    ],
}


class CapabilityIn(BaseModel):
    """单套能力入参。所有字段均可选；api_key 为空字符串表示保持原值。"""
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None


class AISettingsUpdate(BaseModel):
    text: Optional[CapabilityIn] = None
    vision: Optional[CapabilityIn] = None
    asr: Optional[CapabilityIn] = None


class CapabilityOut(BaseModel):
    provider: Optional[str] = None
    has_key: bool = False
    masked_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None


class AISettingsOut(BaseModel):
    text: CapabilityOut = CapabilityOut()
    vision: CapabilityOut = CapabilityOut()
    asr: CapabilityOut = CapabilityOut()
