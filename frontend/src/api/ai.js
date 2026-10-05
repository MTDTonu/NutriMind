import request from './request'
import { getToken } from '@/utils/auth'

// 拍照识别食物（FormData: file）—— 视觉模型耗时较长，放宽超时；失败由页面内联提示
export function recognizeFood(formData) {
  return request({
    url: '/ai/recognize-food',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
    skipErrorToast: true
  })
}

// 生成饮食计划（AI 生成约需 30~40s，单独放宽超时；失败由后端降级为通用食谱）
export function generatePlan(data) {
  return request({
    url: '/ai/generate-plan',
    method: 'post',
    data,
    timeout: 90000,
    skipErrorToast: true
  })
}

// 读取已保存的当日食谱（不触发 AI，首屏秒开）
export function getPlan(params) {
  return request({
    url: '/ai/plan',
    method: 'get',
    params,
    skipErrorToast: true
  })
}

// AI 对话（单次生成实测 10~15s，默认 15s 超时太紧；失败由页面内联兜底文案）
export function aiChat(data) {
  return request({
    url: '/ai/chat',
    method: 'post',
    data,
    timeout: 60000,
    skipErrorToast: true
  })
}

// AI 对话 —— 流式（SSE）
// 不能用 axios：需要边读边渲染，故用原生 fetch + ReadableStream 解析 SSE。
// onDelta(piece): 每收到一段文本回调；返回 Promise，resolve 完整文本。
export async function aiChatStream(payload, onDelta) {
  const token = getToken()
  const base = import.meta.env.VITE_API_BASE || '/api/v1'
  const res = await fetch(base + '/ai/chat/stream', {
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
      /* 非 JSON 响应，保持默认文案 */
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

    // SSE 以空行分隔事件
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

// 今日画像：目标 / 已摄入 / 营养素 / 运动 / 饮水 / 体重 / 打卡
export function getBrief(params) {
  return request({
    url: '/ai/brief',
    method: 'get',
    params,
    skipErrorToast: true
  })
}

// 每日总结
export function dailyReview(params) {
  return request({
    url: '/ai/daily-review',
    method: 'get',
    params,
    timeout: 60000,
    skipErrorToast: true
  })
}
