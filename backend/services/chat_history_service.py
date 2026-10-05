"""AI 会话历史的持久化服务：会话、消息、长期记忆的 CRUD。

设计要点：
- 会话用 sid（uuid4 hex）对外，隐藏自增 id。
- 消息按 seq 排序，稳定不乱序（即便同秒插入）。
- 长期记忆带唯一约束（user_id + text），新增时自动去重，上限 20 条。
- 所有写操作都先校验归属（user_id），杜绝越权访问他人会话。
"""
import uuid
from datetime import datetime
from sqlalchemy import func, select

from database.models import (
    AiChatSession,
    AiChatMessage,
    UserMemory,
)


def _iso(dt) -> str:
    if not dt:
        return ""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def create_session(db, user_id: int, title: str = "新对话") -> AiChatSession:
    """新建会话，返回 ORM 对象（已落库）。"""
    title = (title or "新对话").strip()[:100] or "新对话"
    session = AiChatSession(
        sid=uuid.uuid4().hex,
        user_id=user_id,
        title=title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db, user_id: int, sid: str) -> AiChatSession | None:
    """按 sid 取会话，并校验归属；不存在或不属于该用户都返回 None。"""
    return (
        db.query(AiChatSession)
        .filter(AiChatSession.sid == sid, AiChatSession.user_id == user_id)
        .first()
    )


def list_sessions(db, user_id: int) -> list[dict]:
    """列出当前用户的会话（updated_at 倒序），带消息数与最近一条用户消息预览。"""
    sessions = (
        db.query(AiChatSession)
        .filter(AiChatSession.user_id == user_id)
        .order_by(AiChatSession.updated_at.desc())
        .all()
    )
    if not sessions:
        return []

    sids = [s.sid for s in sessions]
    # 批量统计每个会话的消息数
    counts = dict(
        db.query(AiChatMessage.session_sid, func.count(AiChatMessage.id))
        .filter(AiChatMessage.session_sid.in_(sids))
        .group_by(AiChatMessage.session_sid)
        .all()
    )
    # 批量取每个会话最近的「用户」消息做预览
    previews = {}
    for s in sessions:
        last_user = (
            db.query(AiChatMessage)
            .filter(AiChatMessage.session_sid == s.sid, AiChatMessage.role == "user")
            .order_by(AiChatMessage.seq.desc(), AiChatMessage.id.desc())
            .first()
        )
        previews[s.sid] = (last_user.content[:18] if last_user else "")

    return [
        {
            "sid": s.sid,
            "title": s.title,
            "updated_at": _iso(s.updated_at),
            "message_count": int(counts.get(s.sid, 0)),
            "preview": previews.get(s.sid, ""),
        }
        for s in sessions
    ]


def delete_session(db, user_id: int, sid: str) -> bool:
    """删除会话及其全部消息；返回是否真的删到了。"""
    session = get_session(db, user_id, sid)
    if not session:
        return False
    db.query(AiChatMessage).filter(AiChatMessage.session_sid == sid).delete()
    db.delete(session)
    db.commit()
    return True


def rename_session(db, user_id: int, sid: str, title: str) -> AiChatSession | None:
    """改名；返回更新后的会话或 None。"""
    session = get_session(db, user_id, sid)
    if not session:
        return None
    session.title = (title or "").strip()[:100] or session.title
    db.commit()
    db.refresh(session)
    return session


def _next_seq(db, sid: str) -> int:
    cur = (
        db.query(func.coalesce(func.max(AiChatMessage.seq), 0))
        .filter(AiChatMessage.session_sid == sid)
        .scalar()
    )
    return int(cur or 0) + 1


def add_message(
    db, user_id: int, sid: str, role: str, content: str, image: str | None = None
) -> AiChatMessage:
    """追加一条消息（user / assistant），顺带刷新会话 updated_at。"""
    session = get_session(db, user_id, sid)
    if not session:
        raise ValueError("session_not_found")
    msg = AiChatMessage(
        session_sid=sid,
        user_id=user_id,
        role=role,
        content=content,
        image=image,
        seq=_next_seq(db, sid),
    )
    db.add(msg)
    session.updated_at = datetime.now()
    db.commit()
    db.refresh(msg)
    return msg


def get_messages(db, user_id: int, sid: str) -> list[AiChatMessage]:
    """取会话内全部消息（按 seq 升序）。"""
    session = get_session(db, user_id, sid)
    if not session:
        return []
    return (
        db.query(AiChatMessage)
        .filter(AiChatMessage.session_sid == sid)
        .order_by(AiChatMessage.seq.asc(), AiChatMessage.id.asc())
        .all()
    )


def touch_title(db, user_id: int, sid: str, first_user_content: str) -> None:
    """首条用户消息到达且会话仍为默认标题时，用它生成标题。"""
    session = get_session(db, user_id, sid)
    if not session:
        return
    if session.title == "新对话" and first_user_content:
        session.title = first_user_content[:14] or "新对话"
        db.commit()


# ---------------- 长期记忆 ----------------

MAX_MEMORIES = 20


def list_memories(db, user_id: int) -> list[str]:
    rows = (
        db.query(UserMemory)
        .filter(UserMemory.user_id == user_id)
        .order_by(UserMemory.id.asc())
        .all()
    )
    return [r.text for r in rows]


def add_memory(db, user_id: int, text: str) -> list[str]:
    """新增一条记忆（自动去重 + 上限 20）；返回最新列表。"""
    text = (text or "").strip()[:200]
    if not text:
        return list_memories(db, user_id)
    existing = list_memories(db, user_id)
    if text in existing:
        return existing
    if len(existing) >= MAX_MEMORIES:
        raise ValueError("memory_limit")
    db.add(UserMemory(user_id=user_id, text=text))
    db.commit()
    return list_memories(db, user_id)


def remove_memory(db, user_id: int, text: str) -> list[str]:
    """删除一条记忆（按内容精确匹配）；返回最新列表。"""
    text = (text or "").strip()
    db.query(UserMemory).filter(
        UserMemory.user_id == user_id, UserMemory.text == text
    ).delete()
    db.commit()
    return list_memories(db, user_id)
