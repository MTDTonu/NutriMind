"""Web Push 订阅相关请求结构。"""
from pydantic import BaseModel
from typing import Optional


class PushSubscribeIn(BaseModel):
    """浏览器 ​pushManager.subscribe() 产出的订阅信息。

    endpoint + p256dh + auth 三件套，缺一不可；历史上不少推送失败
    都是前端只传了 endpoint 漏了钥匙。
    """

    endpoint: str
    p256dh: str
    auth: str
    user_agent: Optional[str] = None


class PushUnsubscribeIn(BaseModel):
    """退订。不传 endpoint 表示退订该用户的全部设备。"""

    endpoint: Optional[str] = None


class PushTestIn(BaseModel):
    """发送一条测试推送，用于让用户立刻确认「这条路通不通」。"""

    title: Optional[str] = None
    body: Optional[str] = None
