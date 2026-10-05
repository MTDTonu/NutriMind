// 服务端 AI 会话 / 长期记忆 API。
// 会话与记忆统一存在后端，刷新 / 换设备都不丢；离线时前端用 localStorage 兜底缓存。
import request from './request'
import { getToken } from '@/utils/auth'
import { genIdemKey } from '@/utils/idem'

// 会话列表（updated_at 倒序）
export function listSessions() {
  return request({ url: '/ai/sessions', method: 'get', skipErrorToast: true })
}

// 新建会话，返回 {sid, title, updated_at, message_count, preview}
export function createSession(title) {
  return request({
    url: '/ai/sessions',
    method: 'post',
    data: title ? { title } : {},
    headers: { 'X-Idempotency-Key': genIdemKey() },
    skipErrorToast: true
  })
}

// 取会话详情 + 消息列表
export function getSession(sid) {
  return request({ url: `/ai/sessions/${sid}`, method: 'get', skipErrorToast: true })
}

// 改标题
export function renameSession(sid, title) {
  return request({ url: `/ai/sessions/${sid}`, method: 'patch', data: { title }, skipErrorToast: true })
}

// 删除会话
export function deleteSession(sid) {
  return request({
    url: `/ai/sessions/${sid}`,
    method: 'delete',
    headers: { 'X-Idempotency-Key': genIdemKey() },
    skipErrorToast: true
  })
}

// 落库一个完整回合（用户消息 + 助手回复），带幂等键避免重复写
export function appendTurn(sid, payload) {
  return request({
    url: `/ai/sessions/${sid}/turn`,
    method: 'post',
    data: payload,
    headers: { 'X-Idempotency-Key': genIdemKey() },
    skipErrorToast: true
  })
}

// 长期记忆
export function getMemories() {
  return request({ url: '/ai/memories', method: 'get', skipErrorToast: true })
}
export function addMemory(text) {
  return request({
    url: '/ai/memories',
    method: 'post',
    data: { text },
    headers: { 'X-Idempotency-Key': genIdemKey() },
    skipErrorToast: true
  })
}
export function removeMemory(text) {
  return request({
    url: '/ai/memories',
    method: 'delete',
    data: { text },
    headers: { 'X-Idempotency-Key': genIdemKey() },
    skipErrorToast: true
  })
}

// 会话内流式对话（SSE）。onDelta(piece) 每收到一段回调；返回完整文本。
// 服务端拥有完整上下文，这里只需发送最新一条用户消息。
export async function chatStream(sid, payload, onDelta) {
  const token = getToken()
  const base = import.meta.env.VITE_API_BASE || '/api/v1'
  const res = await fetch(base + `/ai/sessions/${sid}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: 'Bearer ' + token
    },
    body: JSON.stringify(payload)
  })
  if (!res.ok || !res.body) {
    let msg = 'AI 服务异常'
    try {
      const j = await res.json()
      msg = (j && j.message) || msg
    } catch (e) {
      /* 非 JSON 响应 */
    }
    throw new Error(msg)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buf = ''
  let full = ''
  let failed = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let sep
    while ((sep = buf.indexOf('\n\n')) !== -1) {
      const raw = buf.slice(0, sep)
      buf = buf.slice(sep + 2)
      let event = 'message'
      const dataLines = []
      for (const line of raw.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
      }
      if (!dataLines.length) continue
      const data = dataLines.join('\n')
      let obj = {}
      try {
        obj = JSON.parse(data)
      } catch (e) {
        obj = { data }
      }
      if (event === 'delta') {
        const piece = obj.data || ''
        if (piece) {
          full += piece
          if (onDelta) onDelta(piece, full)
        }
      } else if (event === 'error') {
        failed = new Error(obj.message || 'AI 服务异常')
      }
    }
  }
  if (failed) throw failed
  return full
}
