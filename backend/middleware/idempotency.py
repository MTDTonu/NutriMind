"""写入幂等中间件：基于 X-Idempotency-Key 去重，防止重复提交。

适用场景：
- 仅对带 X-Idempotency-Key 头、且 Content-Type 为 application/json 的写请求生效
  （POST / PUT / PATCH / DELETE）。其余请求（如登录、读接口、图片上传、流式对话）
  一律放行，零额外开销。
- 同一 key 的重复提交（网络重试 / 离线补发 / 手抖双点）只会真正执行一次，
  其余直接回放首次响应。

状态机：
- processing：请求正在执行中，重复 key 此时到达 -> 409「请求处理中」。
- done：执行成功（HTTP < 300）并已存响应；未过期 -> 直接回放原始响应字节。
- 非 2xx（校验失败 / 404 / 5xx）-> 删除记录，允许客户端用同 key 修正后重试。

实现细节：
- 读取请求体做回放前必须先重新注入 request._receive，否则下游 Pydantic 模型读不到 body。
- Starlette 在 call_next 返回后 response.body 已不可靠（被消费），因此用
  response.body_iterator 把响应体完整读出来、再重建一个等价 Response 返回给客户端，
  同时把原始字节存库用于回放。
- 必须放在 AuthMiddleware 之后（更内层）执行，才能拿到已鉴权的请求；这里也自行
  解码 Bearer Token 取 user_id，与中间件顺序解耦。
"""
from datetime import datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi import Request
from sqlalchemy.exc import IntegrityError

from database.db import SessionLocal
from database.models import RequestIdempotency
from utils.security import decode_access_token
import json

# 流式对话端点不读 body、不能缓冲，直接放行（其去重由前端 thinking 锁 + 业务层保证）
_STREAMING_MARKERS = ("/chat/stream", "/sessions/", "/ai/chat")
_IDEMPOTENCY_TTL_HOURS = 24


def _is_eligible(request: Request) -> bool:
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return False
    ctype = request.headers.get("content-type", "")
    if "application/json" not in ctype.lower():
        return False
    key = request.headers.get("X-Idempotency-Key") or request.headers.get("Idempotency-Key")
    if not key:
        return False
    path = request.url.path
    if any(m in path for m in _STREAMING_MARKERS):
        return False
    return True


def _user_id_from_request(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = decode_access_token(auth[len("Bearer "):].strip())
        return payload.get("user_id")
    except Exception:
        return None


def _rebuild(response, captured: bytes) -> Response:
    """用已读出的字节重建一个等价 Response 返回给客户端。"""
    return Response(
        content=captured,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """写入幂等中间件。"""

    async def dispatch(self, request: Request, call_next):
        if not _is_eligible(request):
            return await call_next(request)

        key = (request.headers.get("X-Idempotency-Key") or request.headers.get("Idempotency-Key")).strip()
        user_id = _user_id_from_request(request) or 0
        path = request.url.path

        # 读取并缓存请求体，供下游 / 回放使用
        raw_body = await request.body()
        received = {"consumed": False}

        async def _receive():
            if not received["consumed"]:
                received["consumed"] = True
                return {"type": "http.request", "body": raw_body, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        request._receive = _receive

        db = SessionLocal()
        try:
            now = datetime.now()
            record = db.get(RequestIdempotency, key)
            if record is not None:
                if record.status == "done" and record.expires_at and record.expires_at > now:
                    body = record.response_body or "{}"
                    return Response(
                        content=body.encode("utf-8"),
                        status_code=record.response_code or 200,
                        media_type="application/json",
                        headers={"Content-Type": "application/json"},
                    )
                if record.status == "processing":
                    return Response(
                        content=json.dumps({"code": 409, "message": "请求处理中，请勿重复提交", "data": None}).encode("utf-8"),
                        status_code=409,
                        media_type="application/json",
                        headers={"Content-Type": "application/json"},
                    )
                # 已过期：删掉重来
                db.delete(record)
                db.commit()

            # 新请求：登记为 processing（唯一键冲突即视为并发重复）
            rec = RequestIdempotency(
                key=key,
                user_id=user_id,
                path=path,
                status="processing",
                expires_at=now + timedelta(hours=_IDEMPOTENCY_TTL_HOURS),
            )
            db.add(rec)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                return Response(
                    content=json.dumps({"code": 409, "message": "请求处理中，请勿重复提交", "data": None}).encode("utf-8"),
                    status_code=409,
                    media_type="application/json",
                    headers={"Content-Type": "application/json"},
                )

            # 执行真实请求
            response = await call_next(request)

            # 通过迭代器读出完整响应体（call_next 后 response.body 不可靠）
            captured = b""
            async for chunk in response.body_iterator:
                if isinstance(chunk, (bytes, bytearray)):
                    captured += chunk
                else:
                    captured += chunk.encode("utf-8") if isinstance(chunk, str) else b""

            # 只有成功响应才落库回放；非 2xx 视为可重试，删除登记
            if response.status_code < 300:
                try:
                    rec2 = db.get(RequestIdempotency, key)
                    if rec2 is not None:
                        rec2.status = "done"
                        rec2.response_code = response.status_code
                        rec2.response_body = captured.decode("utf-8", "replace")
                        db.commit()
                except Exception:  # noqa: BLE001
                    db.rollback()
                return _rebuild(response, captured)
            else:
                rec2 = db.get(RequestIdempotency, key)
                if rec2 is not None:
                    db.delete(rec2)
                    db.commit()
                return _rebuild(response, captured)
        finally:
            db.close()
