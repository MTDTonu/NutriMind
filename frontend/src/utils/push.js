// Web Push 订阅：让「页面关着也能收到提醒」成为可能。
//
// 三个必须同时满足的条件（缺一个就退化成前台提醒）：
// 1. 浏览器支持 pushManager（Safari 16.4+ / Chrome / Edge / Firefox 均可）
// 2. 已注册 Service Worker（main.js 只在生产构建里注册）
// 3. 用户授予通知权限
//
// 注意 applicationServerKey 必须转成 Uint8Array 传入，直接传字符串会抛 InvalidCharacterError。

import { getPushPublicKey, subscribePush, unsubscribePush, getPushStatus } from '@/api/push'

export function pushSupported() {
  return (
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  )
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = window.atob(base64)
  const output = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; ++i) output[i] = raw.charCodeAt(i)
  return output
}

function currentSubscription() {
  return navigator.serviceWorker.ready.then((reg) => reg.pushManager.getSubscription())
}

export function getExistingSubscription() {
  if (!pushSupported()) return Promise.resolve(null)
  return currentSubscription().catch(() => null)
}

/**
 * 建立推送订阅并上报服务端。
 *
 * 幂等：已有订阅时先退订旧的再重新订阅——这样「服务器 VAPID 密钥换过」的情况
 * 也能自愈，否则会出现「前端显示已订阅，但服务端推不过去」的诡异现象。
 *
 * @returns {Promise<{ok: boolean, reason?: string}>}
 */
export async function enablePush() {
  if (!pushSupported()) return { ok: false, reason: 'unsupported' }

  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return { ok: false, reason: 'denied' }

  try {
    const { public_key: publicKey } = await getPushPublicKey()
    if (!publicKey) return { ok: false, reason: 'no-key' }

    const reg = await navigator.serviceWorker.ready
    const old = await reg.pushManager.getSubscription()
    if (old) {
      await old.unsubscribe().catch(() => {})
    }

    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey)
    })
    const json = sub.toJSON()
    await subscribePush({
      endpoint: json.endpoint,
      p256dh: json.keys.p256dh,
      auth: json.keys.auth,
      user_agent: navigator.userAgent
    })
    return { ok: true }
  } catch (e) {
    return { ok: false, reason: 'error', message: String((e && e.message) || e) }
  }
}

/** 关闭后台提醒：本地退订 + 通知服务端删除记录。 */
export async function disablePush() {
  if (!pushSupported()) return { ok: false, reason: 'unsupported' }
  try {
    const sub = await currentSubscription()
    const endpoint = sub ? sub.endpoint : null
    if (sub) await sub.unsubscribe().catch(() => {})
    await unsubscribePush(endpoint)
    return { ok: true }
  } catch (e) {
    return { ok: false, reason: 'error', message: String((e && e.message) || e) }
  }
}

/** 拉取服务端视角的订阅与调度器状态（含当天计划表）。 */
export function pushStatus() {
  return getPushStatus()
}
