"""知食 NutriMind - AI 智能减脂管理系统 后端入口。

开发模式启动（前端走 vite dev server，双进程）：
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

生产/部署模式（后端单端口同时托管前端构建产物，单进程）：
    先在 frontend 执行 npm run build，再启动本服务；
    检测到 ../frontend/dist/index.html 后会自动托管 SPA，访问 http://<host>:8000 即可。

应用启动流程：
1. 加载 .env 环境变量。
2. 注册 CORS 中间件（最外层）。
3. 注册 JWT 鉴权中间件（内层，仅拦截 /api/**）。
4. 注册全局异常处理器。
5. 挂载所有 router（统一前缀 /api/v1）。
6. 挂载 /uploads 静态目录；若存在前端构建产物则一并托管 SPA。
7. 启动时校验密钥、创建上传目录、自动建表。
"""
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from database.db import create_tables
from middleware.cors import add_cors
from middleware.auth import AuthMiddleware
from utils.exceptions import register_exception_handlers
from utils.common import resp
from utils.security import validate_jwt_secret

from routers import auth, user, diet, weight, ai, exercise, water, stats, food, energy, data, push

# 加载环境变量（若存在 .env）
load_dotenv()

# 创建 FastAPI 应用
app = FastAPI(
    title="知食 NutriMind - AI 智能减脂管理系统",
    description="基于 FastAPI + 智谱 AI 的智能减脂管理后端",
    version="1.0.0",
)

# 1. CORS 中间件（最外层，处理跨域与预检）
add_cors(app)

# 2. JWT 鉴权中间件（内层，解析 token 注入 request.state.user_id）
app.add_middleware(AuthMiddleware)

# 2.5 写入幂等中间件（在鉴权之后，仅对带 X-Idempotency-Key 的 JSON 写请求去重）
from middleware.idempotency import IdempotencyMiddleware
app.add_middleware(IdempotencyMiddleware)

# 3. 全局异常处理
register_exception_handlers(app)

# 4. 挂载路由
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(diet.router)
app.include_router(weight.router)
app.include_router(ai.router)
app.include_router(exercise.router)
app.include_router(water.router)
app.include_router(stats.router)
app.include_router(food.router)
app.include_router(data.router)
app.include_router(push.router)
app.include_router(energy.router)


# 前端构建产物目录：存在 index.html 即视为「部署模式」，由后端统一托管。
# 开发模式下该目录不存在，前端仍由 vite dev server 提供。
_FRONTEND_DIST = os.getenv("FRONTEND_DIST") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
)
_HAS_DIST = os.path.isfile(os.path.join(_FRONTEND_DIST, "index.html"))

# 上传目录：在导入期创建并挂载，确保顺序早于 SPA 的兜底路由
_UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(_UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=os.path.abspath(_UPLOAD_DIR)), name="uploads")


@app.get("/health")
def health():
    """健康检查（始终可用，供部署探活）。"""
    return resp(200, "ok", {"name": "知食 NutriMind"})


if _HAS_DIST:
    # ---- 部署模式：托管前端 SPA（history 路由回退到 index.html） ----
    _ASSETS_DIR = os.path.join(_FRONTEND_DIST, "assets")
    if os.path.isdir(_ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")

    @app.get("/", include_in_schema=False)
    async def spa_index():
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """真实存在的静态文件直接返回，其余交给前端路由。"""
        candidate = os.path.join(_FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))

else:
    # ---- 开发模式：根路径返回服务信息，前端由 5173 提供 ----
    @app.get("/")
    def index():
        return resp(200, "ok", {"name": "知食 NutriMind", "docs": "/docs"})


@app.on_event("startup")
def on_startup():
    """启动时：校验密钥强度 + 确保上传目录存在 + 自动建表 + 补齐内置食物库。"""
    validate_jwt_secret()
    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    create_tables()
    _init_food_base()
    _start_reminder_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    """停机时取消提醒调度协程：否则 uvicorn 退出时会抛 Task was destroyed。"""
    try:
        from services import reminder_scheduler

        reminder_scheduler.stop_scheduler()
    except Exception:  # noqa: BLE001
        pass


def _start_reminder_scheduler():
    """拉起服务端提醒调度器。

    单独包一层并吞掉异常：提醒是增强能力，它的失败不应该让整个服务起不来。
    """
    try:
        from services import reminder_scheduler

        reminder_scheduler.start_scheduler()
    except Exception as exc:  # noqa: BLE001
        print(f"[reminder] 提醒调度器未启动：{exc}")


def _init_food_base():
    """幂等导入内置食物库。

    失败只告警不阻断启动：食物库缺失不应让整个服务起不来，
    否则一次数据问题会直接演变成线上不可用。
    """
    try:
        from database.db import SessionLocal
        from services.food_service import ensure_base_foods

        db = SessionLocal()
        try:
            added = ensure_base_foods(db)
            if added:
                print(f"[food] 内置食物库已补齐，新增 {added} 条")
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        print(f"[food] 内置食物库初始化失败（可稍后手动调用 /api/v1/foods/ensure-base 重试）：{exc}")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
