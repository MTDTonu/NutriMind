/* 知食 NutriMind · Service Worker
 *
 * 目标：弱网/断网时应用壳仍可打开，已访问过的页面与静态资源秒开。
 * 边界：业务数据一律不缓存——饮食、体重这类数据一旦用旧值兜底，
 *       用户会以为记录成功，实际写的是上周的数据。宁可显示「离线」。
 *
 * 策略：
 *   /api/**、/uploads/**  → 只走网络，不做任何兜底
 *   导航请求（HTML）      → 网络优先，失败回退缓存的 index.html
 *   同源静态资源          → 缓存优先 + 后台更新
 */

// 版本号变了才会淘汰旧缓存：改缓存策略或大版本升级时记得 +1
const VERSION = 'v2'
const CACHE_NAME = 'nutrimind-' + VERSION
const SHELL_URLS = ['/', '/index.html', '/favicon.svg', '/manifest.webmanifest']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      // 单个资源失败不阻断安装：缺一张图标不该让离线能力整体失效
      .then((cache) => Promise.allSettled(SHELL_URLS.map((u) => cache.add(u))))
      .then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  )
})

function isDataRequest(url) {
  return url.pathname.startsWith('/api/') || url.pathname.startsWith('/uploads/')
}

self.addEventListener('fetch', (event) => {
  const req = event.request
  if (req.method !== 'GET') return

  let url
  try {
    url = new URL(req.url)
  } catch (e) {
    return
  }
  if (url.origin !== self.location.origin) return

  // 业务数据：只走网络，不做旧值兜底
  if (isDataRequest(url)) return

  // 导航请求：网络优先，断网时回退到应用壳
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone()
          caches.open(CACHE_NAME).then((c) => c.put('/index.html', copy)).catch(() => {})
          return res
        })
        .catch(() =>
          caches
            .match('/index.html')
            .then((cached) => cached || new Response('离线中，且本地没有缓存副本', { status: 503 }))
        )
    )
    return
  }

  // 静态资源：缓存优先 + 后台更新
  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          if (res && res.status === 200 && res.type === 'basic') {
            const copy = res.clone()
            caches.open(CACHE_NAME).then((c) => c.put(req, copy)).catch(() => {})
          }
          return res
        })
        .catch(() => cached)
      return cached || network
    })
  )
})

// 服务端 Web Push：页面关着也能弹出来。
// 载荷必须是 JSON（后端 pywebpush 加密后的明文正是 JSON），取不到就退化成一个兜底文案，
// 绝不让「解析失败」变成一条看不懂的通知。
self.addEventListener('push', (event) => {
  let data = {}
  if (event.data) {
    try {
      data = event.data.json()
    } catch (e) {
      data = { title: '知食提醒', body: (event.data && event.data.text()) || '' }
    }
  }

  const title = data.title || '知食提醒'
  const options = {
    body: data.body || '',
    icon: data.icon || '/icons/icon-192.png',
    badge: data.badge || '/icons/icon-192.png',
    tag: data.tag || 'nutrimind',
    renotify: true,
    lang: 'zh-CN',
    data: { url: data.url || '/' }
  }

  event.waitUntil(self.registration.showNotification(title, options))
})

// 通知点击：跳到 payload 指定的页面（如 /diet 直接开始记录），并聚焦已有窗口
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = (event.notification.data && event.notification.data.url) || '/'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const c of list) {
        // 已有同源窗口：聚焦后直接导航过去；navigate 在部分浏览器上不存在，
        // 此时退化成「只聚焦」，页面由前端路由自己决定落点
        if (c.url.includes(self.location.origin)) {
          c.focus()
          return c.navigate ? c.navigate(target).then(() => undefined) : undefined
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(target)
      return undefined
    })
  )
})

// 订阅过期被推送服务轮换时自动重订阅：否则用户会在毫无察觉的情况下收不到提醒
self.addEventListener('pushsubscriptionchange', (event) => {
  event.waitUntil(
    (async () => {
      try {
        const res = await fetch('/api/v1/push/public-key')
        const json = await res.json()
        const key = json && json.data && json.data.public_key
        if (!key) return
        // applicationServerKey 要求 Uint8Array；base64url 必须补齐 '=' 再 atob，
        // 否则长度对 4 取模为 1 时会直接抛 InvalidCharacterError
        const b64 = key.replace(/-/g, '+').replace(/_/g, '/')
        const padded = b64 + '='.repeat((4 - (b64.length % 4)) % 4)
        const raw = Uint8Array.from(atob(padded), (c) => c.charCodeAt(0))
        const sub = await self.registration.pushManager.subscribe({
          applicationServerKey: raw,
          userVisibleOnly: true
        })
        const s = sub.toJSON()
        await fetch('/api/v1/push/subscribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            endpoint: s.endpoint,
            p256dh: s.keys.p256dh,
            auth: s.keys.auth
          })
        })
      } catch (e) {
        /* 静默失败：下次打开设置页会重新提示订阅 */
      }
    })()
  )
})
