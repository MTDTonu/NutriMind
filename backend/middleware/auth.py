"""JWT 鉴权中间件 + 当前用户依赖。

职责：
- AuthMiddleware：拦截需要登录的请求，从 Authorization: Bearer {token}
  解析出 user_id 存入 request.state.user_id；失败或缺失返回 401。
- get_current_user_id：FastAPI 依赖，从 request.state.user_id 读取当前用户，
  供各 router 使用。

鉴权范围：**仅业务接口 `/api/**`**。其余路径（SPA 静态资源与前端路由、/uploads
图片、/docs 文档、/health 探活）一律放行——否则浏览器刷新 `/diet` 这类前端路由
会被 401 拦住，且 `<img>` 无法携带 Authorization 头导致图片必然裂图。
"""
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

from utils.security import decode_access_token

# 无需鉴权的业务接口（注册、登录）
PUBLIC_PATHS = {
    "/api/v1/auth/register",
    "/api/v1/auth/login",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT 鉴权中间件。"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # CORS 预检（OPTIONS）不带鉴权头，必须直接放行交由 CORS 中间件响应，
        # 否则跨域生产环境会被此处拦截 401，导致浏览器阻断后续真实请求。
        if request.method == "OPTIONS":
            return await call_next(request)

        # 非 /api 路径（SPA 资源、前端路由、uploads、docs、health）直接放行
        if not path.startswith("/api/"):
            return await call_next(request)

        # 公开接口（注册 / 登录）放行
        if path in PUBLIC_PATHS:
            return await call_next(request)

        # 读取 Authorization 头
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"code": 401, "message": "未认证，缺少有效的 Authorization 头", "data": None},
            )

        token = auth_header[len("Bearer "):].strip()
        try:
            payload = decode_access_token(token)
            user_id = payload.get("user_id")
            if user_id is None:
                raise ValueError("token 中缺少 user_id")
            # 注入到 request.state，供下游依赖读取
            request.state.user_id = user_id
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "message": "未认证或令牌已失效", "data": None},
            )

        return await call_next(request)


def get_current_user_id(request: Request) -> int:
    """FastAPI 依赖：返回当前登录用户 ID（由 AuthMiddleware 注入）。"""
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        # 理论上中间件已拦截，这里作为兜底
        from utils.exceptions import AppException
        raise AppException(401, "未认证")
    return user_id
