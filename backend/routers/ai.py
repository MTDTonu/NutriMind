"""AI 路由：食物识别、食谱生成、对话、每日复盘。"""
import os
import uuid
import asyncio
import logging
from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from database.db import get_db
from middleware.auth import get_current_user_id
from schemas.ai import (
    RecognizeResponse, FoodItem, PlanRequest, PlanResponse, ChatRequest,
    ChatResponse, DailyReviewResponse, SessionCreate, RenameRequest,
    SessionOut, MessageOut, SessionDetail, MemoryRequest, TurnRequest,
)
from services.ai_service import ai_service
from services.auth_service import get_current_user
from services.brief_service import build_brief, brief_to_text
from services.chat_history_service import (
    create_session, list_sessions, get_session, delete_session, rename_session,
    add_message, get_messages, list_memories, add_memory, remove_memory,
    touch_title, MAX_MEMORIES,
)
from services.user_service import get_user_ai_settings, build_cfg
from utils.common import resp, parse_date, today
from utils.exceptions import AppException
from sqlalchemy import func
from database.models import DietRecord, AiDietPlan
from fastapi.responses import StreamingResponse
import json

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])
logger = logging.getLogger("ai.recognize")


def _cfg(db, user_id: int, cap: str, default_model: str) -> dict:
    """读取用户某套能力的调用配置。"""
    row = get_user_ai_settings(db, user_id)
    return build_cfg(row, cap, default_model)


# 常见图片格式的文件头（magic bytes），用于真实类型校验，避免仅靠扩展名被绕过
_IMAGE_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",          # JPEG
    b"\x89PNG\r\n\x1a\n": "image/png",      # PNG
}


def _sniff_image_mime(content: bytes) -> Optional[str]:
    """根据文件头嗅探真实图片 MIME，非 jpg/png 返回 None。"""
    for magic, mime in _IMAGE_MAGIC.items():
        if content.startswith(magic):
            return mime
    return None


def _save_and_recognize(content: bytes, mime: str, db: Session, user_id: int) -> tuple:
    """在线程池中执行：同步落盘 + 同步大模型推理，避免阻塞事件循环。"""
    upload_dir = os.getenv("UPLOAD_DIR", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    ext = ".jpg" if mime == "image/jpeg" else ".png"
    saved_name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(upload_dir, saved_name), "wb") as f:
        f.write(content)
    result = ai_service.recognize_food(
        content, mime, cfg=_cfg(db, user_id, "vision", "glm-4v-flash")
    )
    return saved_name, result


@router.post("/recognize-food")
async def recognize_food(
    file: UploadFile = File(..., description="图片文件，仅 jpg/png，≤5MB"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """上传食物图片，识别食物并估算营养。"""
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        logger.warning(
            "recognize-food 拒绝：图片 %d 字节超限（user=%s, filename=%s）",
            len(content), user_id, file.filename,
        )
        raise AppException(400, "图片大小不能超过 5MB")

    # 校验真实文件类型（magic bytes），仅依赖扩展名可被改名绕过
    mime = _sniff_image_mime(content)
    if mime is None:
        logger.warning(
            "recognize-food 拒绝：非 jpg/png（user=%s, filename=%s, head=%r）",
            user_id, file.filename, content[:12],
        )
        raise AppException(
            400, "图片格式不支持，请上传 JPG / PNG 图片（HEIC / WebP 请先另存为 JPG）"
        )

    # 文件落盘 + 模型推理为同步阻塞操作，交给线程池执行，保护事件循环吞吐
    loop = asyncio.get_event_loop()
    saved_name, result = await loop.run_in_executor(
        None, _save_and_recognize, content, mime, db, user_id
    )

    foods = [FoodItem(**item) for item in result.get("food_list", [])]
    return resp(200, "success", RecognizeResponse(
        food_list=foods,
        total_calorie=float(result.get("total_calorie", 0)),
        image_url=f"/uploads/{saved_name}",
    ).model_dump())


@router.post("/generate-plan")
def generate_plan(
    body: Optional[PlanRequest] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """生成一日减脂食谱（落库 ai_diet_plan）。"""
    target_date = parse_date(body.date) if body and body.date else date.today()
    user = get_current_user(db, user_id)
    # 当日已摄入热量
    eaten = float(
        db.query(func.coalesce(func.sum(DietRecord.calorie), 0.0)).filter(
            DietRecord.user_id == user_id, DietRecord.record_date == target_date
        ).scalar() or 0
    )
    plan = ai_service.generate_plan(
        db, user, target_date, eaten,
        cfg=_cfg(db, user_id, "text", "glm-4-flash"),
    )
    return resp(200, "success", {"plan": PlanResponse(**plan).model_dump()})


@router.get("/brief")
def brief(
    date: str = Query(None, description="YYYY-MM-DD，缺省为今天"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """用户今日画像：目标 / 已摄入 / 三大营养素 / 运动 / 饮水 / 体重 / 打卡。

    前端用它渲染 AI 页顶部的「今日画像」，后端同时把它压成文本注入对话系统提示词。
    """
    d = parse_date(date) if date else today()
    user = get_current_user(db, user_id)
    data = build_brief(db, user, d)
    data["text"] = brief_to_text(data)
    return resp(200, "success", data)


@router.post("/chat")
def chat(
    body: ChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """AI 减脂营养师对话（多轮携带上下文 + 长期记忆 + 今日实况）。"""
    user = get_current_user(db, user_id)
    snap = build_brief(db, user, today())
    reply = ai_service.chat(
        user, body.message, body.history or [], body.memories,
        cfg=_cfg(db, user_id, "text", "glm-4-flash"),
        brief={"text": brief_to_text(snap)},
    )
    return resp(200, "success", ChatResponse(reply=reply).model_dump())


@router.post("/chat/stream")
def chat_stream(
    body: ChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """AI 对话流式输出（SSE）。

    事件类型：
    - `delta`：带 data 字段的文本片段
    - `done`：流结束
    - `error`：出错（message 为提示文案）
    """
    from fastapi.responses import StreamingResponse
    from utils.exceptions import AppException

    user = get_current_user(db, user_id)
    snap = build_brief(db, user, today())

    def gen():
        def sse(event: str, payload: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        try:
            for piece in ai_service.chat_stream(
                user, body.message, body.history or [], body.memories,
                cfg=_cfg(db, user_id, "text", "glm-4-flash"),
                brief={"text": brief_to_text(snap)},
            ):
                yield sse("delta", {"data": piece})
            yield sse("done", {"data": ""})
        except AppException as e:
            yield sse("error", {"message": e.message})
        except Exception as e:  # noqa: BLE001
            yield sse("error", {"message": f"AI 服务异常：{e}"})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/daily-review")
def daily_review(
    date: str = Query(None, description="YYYY-MM-DD，缺省为今天"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """生成当日饮食复盘（≤300 字）。"""
    d = parse_date(date) if date else today()
    review = ai_service.daily_review(
        db, user_id, d, cfg=_cfg(db, user_id, "text", "glm-4-flash")
    )
    return resp(200, "success", DailyReviewResponse(review=review).model_dump())


@router.get("/plan")
def get_plan(
    date: str = Query(None, description="YYYY-MM-DD，缺省为今天"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """读取已保存的当日食谱（不触发 AI 生成，用于首屏快速加载）。"""
    d = parse_date(date) if date else today()
    row = (
        db.query(AiDietPlan)
        .filter(AiDietPlan.user_id == user_id, AiDietPlan.plan_date == d)
        .order_by(AiDietPlan.id.desc())
        .first()
    )
    if not row:
        return resp(200, "success", {"plan": None})

    plan = {
        "breakfast": json.loads(row.breakfast or "[]"),
        "lunch": json.loads(row.lunch or "[]"),
        "dinner": json.loads(row.dinner or "[]"),
        "total_calorie": float(row.total_calorie or 0),
        "adapt_desc": row.adapt_desc or "",
    }
    return resp(200, "success", {"plan": PlanResponse(**plan).model_dump()})


# =============================================================
#  AI 会话历史（服务端化） + 长期记忆
# =============================================================

def _iso(dt) -> str:
    if not dt:
        return ""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%d %H:%M:%S")


@router.post("/sessions")
def create_session_api(
    body: SessionCreate = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """新建对话会话，返回 sid。"""
    title = body.title if body and body.title else None
    s = create_session(db, user_id, title)
    return resp(200, "success", SessionOut(
        sid=s.sid, title=s.title, updated_at=_iso(s.updated_at),
        message_count=0, preview="",
    ).model_dump())


@router.get("/sessions")
def list_sessions_api(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出当前用户的全部对话会话（updated_at 倒序）。"""
    return resp(200, "success", {"sessions": list_sessions(db, user_id)})


@router.get("/sessions/{sid}")
def get_session_api(
    sid: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """取单个会话及其消息列表。"""
    s = get_session(db, user_id, sid)
    if not s:
        raise AppException(404, "会话不存在")
    msgs = get_messages(db, user_id, sid)
    return resp(200, "success", SessionDetail(
        sid=s.sid, title=s.title, updated_at=_iso(s.updated_at),
        messages=[
            MessageOut(role=m.role, content=m.content, image=m.image, created_at=_iso(m.created_at))
            for m in msgs
        ],
    ).model_dump())


@router.patch("/sessions/{sid}")
def rename_session_api(
    sid: str, body: RenameRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """改会话标题。"""
    s = rename_session(db, user_id, sid, body.title)
    if not s:
        raise AppException(404, "会话不存在")
    return resp(200, "success", {"sid": s.sid, "title": s.title})


@router.delete("/sessions/{sid}")
def delete_session_api(
    sid: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """删除会话（连同其消息）。"""
    ok = delete_session(db, user_id, sid)
    if not ok:
        raise AppException(404, "会话不存在")
    return resp(200, "success", {"success": True})


@router.get("/memories")
def list_memories_api(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """读取长期记忆列表。"""
    return resp(200, "success", {"memories": list_memories(db, user_id)})


@router.post("/memories")
def add_memory_api(
    body: MemoryRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """新增一条长期记忆（自动去重，最多 20 条）。"""
    try:
        mems = add_memory(db, user_id, body.text)
    except ValueError:
        raise AppException(400, f"最多保存 {MAX_MEMORIES} 条记忆")
    return resp(200, "success", {"memories": mems})


@router.delete("/memories")
def remove_memory_api(
    body: MemoryRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """删除一条长期记忆。"""
    mems = remove_memory(db, user_id, body.text)
    return resp(200, "success", {"memories": mems})


# =============================================================
#  会话内流式对话（落库）
# =============================================================

@router.post("/sessions/{sid}/chat")
def session_chat_stream(
    sid: str, body: ChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """在指定会话内发起对话（SSE 流式）。

    服务端拥有完整上下文：先从库里读出历史消息作为 history，再调用模型；
    用户消息与助手回复都会落库，刷新 / 换设备后仍可见完整对话。
    """
    session = get_session(db, user_id, sid)
    if not session:
        raise AppException(404, "会话不存在")

    message = (body.message or "").strip()
    if not message:
        raise AppException(400, "消息内容不能为空")

    # 历史消息（不含即将写入的这条用户消息）
    hist_msgs = get_messages(db, user_id, sid)
    history = [
        {"role": m.role, "content": m.content}
        for m in hist_msgs if m.role in ("user", "assistant")
    ]

    user = get_current_user(db, user_id)
    snap = build_brief(db, user, today())
    memories = list_memories(db, user_id)

    def gen():
        def sse(event, payload):
            return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        # 注意：本端点只负责「读历史 + 流式生成」；用户消息与助手回复的落库
        # 交由前端在流式结束后调用 /sessions/{sid}/turn 统一完成，
        # 避免流式失败走非流式兜底时与流式端点重复落库。
        full = ""
        try:
            for piece in ai_service.chat_stream(
                user, message, history, memories,
                cfg=_cfg(db, user_id, "text", "glm-4-flash"),
                brief={"text": brief_to_text(snap)},
            ):
                full += piece
                yield sse("delta", {"data": piece})
            yield sse("done", {"data": full})
        except AppException as e:
            yield sse("error", {"message": e.message})
        except Exception as e:  # noqa: BLE001
            yield sse("error", {"message": f"AI 服务异常：{e}"})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sessions/{sid}/turn")
def append_turn(
    sid: str, body: TurnRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """落库一个完整回合（用户消息 + 助手回复）。

    前端在流式对话结束后调用：把本轮的 user/assistant 写入会话，
    首次用户消息还会自动生成会话标题。图片（食物识别）随用户消息一并保存。
    """
    s = get_session(db, user_id, sid)
    if not s:
        raise AppException(404, "会话不存在")
    add_message(db, user_id, sid, "user", body.user_content, body.image)
    if body.assistant_content:
        add_message(db, user_id, sid, "assistant", body.assistant_content)
    touch_title(db, user_id, sid, body.user_content)
    return resp(200, "success", {"success": True})
