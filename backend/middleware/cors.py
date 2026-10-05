"""CORS 中间件配置。

安全约束：
- 不能 `allow_origins=["*"]` 与 `allow_credentials=True` 同时生效（星号通配会让
  任意第三方站点都能发起携带凭证的请求）。
- 因此改为读取白名单环境变量 CORS_ORIGINS（逗号分隔）；未配置时回退到
  前端开发/常用源，而不是开放给所有来源。
"""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

import os


def _default_origins() -> list:
    """默认允许的源：本地开发 + 可经环境变量追加生产域名。"""
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ]
    extra = (os.getenv("CORS_ORIGINS") or "").strip()
    if extra:
        origins.extend([o.strip() for o in extra.split(",") if o.strip()])
    # 去重保序
    seen, out = set(), []
    for o in origins:
        if o not in seen:
            seen.add(o)
            out.append(o)
    return out


def add_cors(app: FastAPI):
    """为应用添加 CORS 中间件（显式白名单，绝不开放 *）。"""
    origins = _default_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
