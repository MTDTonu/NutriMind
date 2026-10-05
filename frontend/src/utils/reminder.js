// 提醒调度器：把「设置里的时间」真正变成一次触达。
//
// 实现边界（说清楚比假装更强重要）：
// - 这是一个**前台**调度器：页面在浏览器里打开（哪怕在后台标签页）才会触发。
//   关掉浏览器不会有系统级推送——那需要服务端推送通道与订阅机制，不在本版范围。
// - 触达方式有二：① 浏览器系统通知（需用户授权）；② 应用内提示条（无需授权，永远可用）。
// - 每条提醒当天只发一次，用 localStorage 去重，避免刷新页面后重复轰炸。

import { getReminders } from '@/api/data'
import { today } from '@/utils/format'

const TICK_MS = 30 * 1000 // 30 秒一跳：分钟级精度足够，也不会明显耗电
const REFETCH_MS = 10 * 60 * 1000 // 设置每 10 分钟同步一次，改完设置不用刷新页面
const FIRE_EVENT = 'nm:reminder'

let timer = null
let cfg = null
let lastFetchAt = 0
let started = false

// ---------- 时间工具 ----------
function toMinutes(hhmm) {
  if (typeof hhmm !== 'string') return null
  const m = hhmm.match(/^(\d{1,2}):(\d{2})$/)
  if (!m) return null
  const h = Number(m[1])
  const mi = Number(m[2])
  if (h > 23 || mi > 59) return null
  return h * 60 + mi
}

function nowMinutes() {
  const d = new Date()
  return d.getHours() * 60 + d.getMinutes()
}

// 免打扰支持跨零点（如 22:30–07:00）
function inQuiet(min) {
  if (!cfg || !cfg.quiet_enabled) return false
  const s = toMinutes(cfg.quiet_start)
  const e = toMinutes(cfg.quiet_end)
  if (s == null || e == null || s === e) return false
  if (s < e) return min >= s && min < e
  return min >= s || min < e
}

// 饮水提醒：从开始时间起按间隔铺到结束时间
function waterTimes() {
  if (!cfg || !cfg.water_enabled) return []
  const s = toMinutes(cfg.water_start)
  const e = toMinutes(cfg.water_end)
  if (s == null || e == null || e <= s) return []
  const step = Math.min(Math.max(Number(cfg.water_interval_hours) || 2, 1), 6) * 60
  const out = []
  for (let t = s; t <= e; t += step) out.push(t)
  return out
}

// ---------- 当天去重 ----------
function firedKey() {
  return 'nm:reminder:fired:' + today()
}

function loadFired() {
  try {
    const raw = localStorage.getItem(firedKey())
    return raw ? JSON.parse(raw) : []
  } catch (e) {
    return []
  }
}

function markFired(id) {
  try {
    const arr = loadFired()
    if (!arr.includes(id)) arr.push(id)
    localStorage.setItem(firedKey(), JSON.stringify(arr))
  } catch (e) {
    /* 隐私模式下写不进去：退化为「本次会话不去重」，不影响主流程 */
  }
}

// 清掉昨天及更早的去重记录，避免 localStorage 无限增长
function cleanOldFired() {
  try {
    const prefix = 'nm:reminder:fired:'
    const keep = prefix + today()
    Object.keys(localStorage)
      .filter((k) => k.startsWith(prefix) && k !== keep)
      .forEach((k) => localStorage.removeItem(k))
  } catch (e) {
    /* 忽略 */
  }
}

// ---------- 触达 ----------
export function notifySupported() {
  return typeof window !== 'undefined' && 'Notification' in window
}

export function notifyPermission() {
  if (!notifySupported()) return 'unsupported'
  return Notification.permission // 'default' | 'granted' | 'denied'
}

export async function requestNotifyPermission() {
  if (!notifySupported()) return 'unsupported'
  if (Notification.permission !== 'default') return Notification.permission
  try {
    return await Notification.requestPermission()
  } catch (e) {
    return 'denied'
  }
}

// 一次触达：系统通知 + 应用内事件（两者都发，保证「没授权也看得见」）
export function fireReminder({ id, title, body }) {
  if (notifySupported() && Notification.permission === 'granted') {
    try {
      new Notification(title, {
        body,
        icon: '/favicon.svg',
        badge: '/favicon.svg',
        tag: id, // 同一条提醒不堆叠
        requireInteraction: false
      })
    } catch (e) {
      // 部分环境（如移动端 Safari 的旧实现）需要用 service worker 注册通知，
      // 这里失败不重要：应用内提示条仍然会正常弹出
    }
  }
  window.dispatchEvent(new CustomEvent(FIRE_EVENT, { detail: { id, title, body } }))
}

export function sendTestReminder() {
  fireReminder({
    id: 'test-' + Date.now(),
    title: '知食 · 测试提醒',
    body: '这就是到点后的样子：记录一句话的事。'
  })
}

// ---------- 计划表 ----------
// 返回当天应触发的提醒：{ id, minute, title, body }
function buildPlan() {
  if (!cfg) return []
  const plan = []

  if (cfg.meal_enabled) {
    const meals = [
      { key: 'breakfast_time', label: '早餐' },
      { key: 'lunch_time', label: '午餐' },
      { key: 'dinner_time', label: '晚餐' }
    ]
    meals.forEach((m) => {
      const min = toMinutes(cfg[m.key])
      if (min == null) return
      plan.push({
        id: 'meal-' + m.label,
        minute: min,
        title: `该记${m.label}了`,
        body: '吃完顺手记一笔，比晚上回忆准得多。'
      })
    })
  }

  if (cfg.weigh_enabled) {
    const min = toMinutes(cfg.weigh_time)
    if (min != null) {
      plan.push({
        id: 'weigh',
        minute: min,
        title: '该称体重了',
        body: '晨起空腹最稳定，称完体重曲线才有意义。'
      })
    }
  }

  if (cfg.water_enabled) {
    waterTimes().forEach((min) => {
      const hh = String(Math.floor(min / 60)).padStart(2, '0')
      const mm = String(min % 60).padStart(2, '0')
      plan.push({
        id: 'water-' + hh + mm,
        minute: min,
        title: '喝杯水吧',
        body: '补水能明显降低「假饥饿」带来的加餐。'
      })
    })
  }

  return plan
}

function tick() {
  if (!cfg) return
  const now = nowMinutes()
  if (inQuiet(now)) return

  const fired = loadFired()
  buildPlan().forEach((item) => {
    if (item.minute !== now) return
    if (fired.includes(item.id)) return
    markFired(item.id)
    fireReminder(item)
  })
}

async function syncConfig(force) {
  const now = Date.now()
  if (!force && cfg && now - lastFetchAt < REFETCH_MS) return
  try {
    cfg = await getReminders()
    lastFetchAt = now
  } catch (e) {
    // 拉取失败保留旧配置：提醒晚一点比不发强
    if (!cfg) cfg = null
  }
}

export async function startReminderScheduler() {
  if (started || typeof window === 'undefined') return
  started = true

  cleanOldFired()
  await syncConfig(true)
  tick()

  timer = setInterval(async () => {
    await syncConfig(false)
    tick()
  }, TICK_MS)

  // 从后台标签页切回来时立刻补一次：睡着的计时器可能跳过整分钟
  document.addEventListener('visibilitychange', onVisible)
}

function onVisible() {
  if (document.visibilityState === 'visible') {
    syncConfig(true).then(tick)
  }
}

export function stopReminderScheduler() {
  if (timer) clearInterval(timer)
  timer = null
  started = false
  if (typeof document !== 'undefined') {
    document.removeEventListener('visibilitychange', onVisible)
  }
}

// 设置保存后调用：让新时间立刻生效，不用等 10 分钟
export function refreshReminders() {
  if (!started) return
  syncConfig(true)
}

// 供组件订阅应用内提示
export const REMINDER_EVENT = FIRE_EVENT
