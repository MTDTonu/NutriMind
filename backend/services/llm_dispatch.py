"""多厂商大模型分发：文字 / 视觉理解 调用统一收口。

- 智谱（zhipu）：走官方 zhipuai SDK（依赖已装）。
- 其它国内厂商（dashscope / volcengine / ernie）及 custom：
  走 OpenAI 兼容的 /v1/chat/completions，用 httpx 发起（含流式）。
  视觉理解只需在 messages 中带 image_url，与文字共用同一通道。

语言转文字（ASR）当前由前端浏览器 Web Speech API 完成，
后端不在此实现；配置仍存入 user_ai_settings 作为服务端 ASR 预留。
"""
import json

import httpx
from utils.exceptions import AppException


# 各厂商 OpenAI 兼容 base_url（custom 由用户在 base_url 字段自填）
PROVIDER_BASE_URL = {
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "volcengine": "https://ark.cn-beijing.volces.com/api/v1",
    "ernie": "https://qianfan.baidubce.com/v2",
}

# 模块级复用的 HTTP 连接池：避免每次调用都新建 TCP/TLS 连接。
# 多轮对话 + 流式场景下连接复用收益明显；httpx.Client 线程安全，可跨请求共享。
# 注意：这是长生命周期对象，绝不能放进 `with`（会被关闭）。
_HTTP_CLIENT = httpx.Client(
    timeout=httpx.Timeout(90.0, connect=15.0),
    limits=httpx.Limits(
        max_connections=32,
        max_keepalive_connections=16,
        keepalive_expiry=30.0,
    ),
    headers={"User-Agent": "JianFeiWeb/1.0"},
    follow_redirects=True,
)


def _zhipu_client(api_key: str):
    from zhipuai import ZhipuAI

    try:
        client_kwargs = {"max_retries": 1, "timeout": httpx.Timeout(90.0, connect=15.0)}
    except Exception:  # noqa: BLE001
        client_kwargs = {"max_retries": 1, "timeout": 90}
    try:
        return ZhipuAI(api_key=api_key, **client_kwargs)
    except TypeError:
        return ZhipuAI(api_key=api_key)


def _openai_url(provider: str, base_url: str = None) -> str:
    base = (base_url or PROVIDER_BASE_URL.get(provider) or "https://api.openai.com/v1")
    return base.rstrip("/") + "/chat/completions"


def _require_cfg(cfg: dict, cap: str):
    provider = (cfg or {}).get("provider")
    api_key = (cfg or {}).get("api_key")
    model = (cfg or {}).get("model")
    # 配置缺失属于客户端（用户）问题，应返回 400 而非 500
    if not provider or not api_key:
        raise AppException(
            400,
            f"未配置「{cap}」模型的 Key，请到「我的」页配置（国内大模型均可）。",
        )
    if not model:
        raise AppException(400, f"未配置「{cap}」模型的模型名，请到「我的」页填写。")
    return provider, api_key, model, (cfg or {}).get("base_url")


def complete(cfg: dict, messages: list, cap: str = "文字", timeout: float = 90) -> str:
    """一次性补全，返回文本。"""
    provider, api_key, model, base_url = _require_cfg(cfg, cap)

    if provider == "zhipu":
        client = _zhipu_client(api_key)
        resp = client.chat.completions.create(model=model, messages=messages)
        return (resp.choices[0].message.content or "").strip()

    url = _openai_url(provider, base_url)
    r = _HTTP_CLIENT.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages},
        timeout=timeout,
    )
    if r.status_code != 200:
        raise AppException(500, f"大模型调用失败[{provider} {r.status_code}]: {r.text[:200]}")
    data = r.json()
    return (data["choices"][0]["message"]["content"] or "").strip()


def stream_complete(cfg: dict, messages: list, cap: str = "文字", timeout: float = 90):
    """流式补全，逐段 yield 文本片段。"""
    provider, api_key, model, base_url = _require_cfg(cfg, cap)

    if provider == "zhipu":
        client = _zhipu_client(api_key)
        resp = client.chat.completions.create(model=model, messages=messages, stream=True)
        for chunk in resp:
            try:
                piece = chunk.choices[0].delta.content
            except Exception:  # noqa: BLE001
                continue
            if piece:
                yield piece
        return

    url = _openai_url(provider, base_url)
    # 复用共享连接池；`client.stream` 上下文只关闭本次响应，不关闭共享 client
    with _HTTP_CLIENT.stream(
        "POST",
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "stream": True},
        timeout=timeout,
    ) as r:
        if r.status_code != 200:
            body = r.read().decode("utf-8", "ignore")
            raise AppException(500, f"大模型调用失败[{provider} {r.status_code}]: {body[:200]}")
        for line in r.iter_lines():
            if not line:
                continue
            if not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                piece = data["choices"][0]["delta"].get("content")
            except Exception:  # noqa: BLE001
                continue
            if piece:
                yield piece
