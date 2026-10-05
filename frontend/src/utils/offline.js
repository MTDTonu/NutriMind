// 离线能力：把「断网就不能用」改成「断网也能记，联网自动补」。
//
// 分成两件互相独立的事：
// 1. **写**：离线时把写请求（记一餐、记体重、记饮水…）塞进 IndexedDB 队列，
//    联网后按原顺序补发。宁可让用户在地铁里记下来，也不要让他因为没信号干脆不记。
// 2. **读**：把关键读数接口的响应缓存一份，离线时拿缓存兜底，
//    页面上标注「离线数据」，避免「白屏 + 报错」这种最伤人的体验。
//
// 刻意不做的：乐观更新写本地 DB 再合并冲突。记录类应用冲突概率极低，
// 但工程量翻倍；这里只保证「离线能提交、联网能补、失败能看见」。

import { ref } from 'vue'

const DB_NAME = 'nutrimind-offline'
const DB_VERSION = 1
const WRITE_STORE = 'queue'
const READ_STORE = 'cache'

// 读数缓存有效期：超过 12 小时的数据不让它在离线时冒充「当前状态」
const CACHE_TTL_MS = 12 * 60 * 60 * 1000

// 允许排队的写请求（按 url 精确匹配，避免把登录、AI 对话这类东西也塞进队列）
const QUEUEABLE = new Set([
  '/diet/add',
  '/weight/add',
  '/water/add',
  '/exercise/add',
  '/data/reminders'
])

// 队列里的动态 url：/diet/{id} 的编辑与删除同样要能补发
const QUEUEABLE_DYNAMIC = [/^\/diet\/\d+$/, /^\/exercise\/\d+$/, /^\/weight\/\d+$/]

// 参与离线兜底的读数接口
const CACHEABLE = new Set([
  '/diet/today',
  '/diet/list',
  '/weight/list',
  '/water/today',
  '/exercise/list',
  '/exercise/weekly',
  '/stats/daily',
  '/stats/weekly',
  '/stats/weight-trend',
  '/stats/nutrient-trend',
  '/energy/target',
  '/ai/brief'
])

export const pendingCount = ref(0)
export const lastSyncAt = ref(0)
let flushing = false

// ---------- IndexedDB ----------
let _dbPromise = null

function openDB() {
  if (_dbPromise) return _dbPromise
  _dbPromise = new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('当前环境不支持 IndexedDB'))
      return
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(WRITE_STORE)) {
        db.createObjectStore(WRITE_STORE, { keyPath: 'id', autoIncrement: true })
      }
      if (!db.objectStoreNames.contains(READ_STORE)) {
        db.createObjectStore(READ_STORE, { keyPath: 'key' })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
  return _dbPromise
}

function tx(store, mode, fn) {
  return openDB().then(
    (db) =>
      new Promise((resolve, reject) => {
        const t = db.transaction(store, mode)
        const storeObj = t.objectStore(store)
        let result
        try {
          result = fn(storeObj)
        } catch (e) {
          reject(e)
          return
        }
        t.oncomplete = () => resolve(result && result.result !== undefined ? result.result : result)
        t.onerror = () => reject(t.error)
        t.onabort = () => reject(t.error)
      })
  )
}

// ---------- 写队列 ----------
export function isQueueable(config) {
  if (!config || !config.url) return false
  const url = String(config.url)
  const method = String(config.method || 'get').toLowerCase()
  if (!['post', 'put', 'delete', 'patch'].includes(method)) return false
  if (QUEUEABLE.has(url)) return true
  const dynamic = QUEUEABLE_DYNAMIC.some((re) => re.test(url))
  // 导出 / 导入 / AI 这类带副作用或大载荷的一律不排队
  if (url.startsWith('/auth/') || url.startsWith('/ai/') || url.startsWith('/push/')) return false
  if (url.startsWith('/data/import') || url.startsWith('/data/export')) return false
  return dynamic
}

export function cacheKey(config) {
  if (!config) return ''
  const url = String(config.url || '')
  const params = config.params ? JSON.stringify(config.params) : ''
  return `${String(config.method || 'get').toUpperCase()} ${url} ${params}`
}

export function isCacheable(config) {
  if (!config || String(config.method || 'get').toLowerCase() !== 'get') return false
  return CACHEABLE.has(String(config.url || ''))
}

export async function enqueue(config) {
  // 仅保留「内容类型」与「幂等键」：幂等键必须随补发原样带回，
  // 服务端才能把这次补发识别为同一次提交、避免离线期间重复落库。
  const keep = {}
  const h = config.headers || {}
  if (h['Content-Type']) keep['Content-Type'] = h['Content-Type']
  if (h['X-Idempotency-Key']) keep['X-Idempotency-Key'] = h['X-Idempotency-Key']
  if (h['idempotency-key']) keep['X-Idempotency-Key'] = h['idempotency-key']
  const item = {
    url: String(config.url),
    method: String(config.method || 'post').toLowerCase(),
    params: config.params || null,
    data: config.data || null,
    headers: Object.keys(keep).length ? keep : null,
    createdAt: Date.now(),
    tries: 0
  }
  await tx(WRITE_STORE, 'readwrite', (s) => s.add(item))
  await refreshPending()
  return item
}

export async function refreshPending() {
  try {
    const all = await tx(WRITE_STORE, 'readonly', (s) => s.getAll())
    pendingCount.value = Array.isArray(all) ? all.length : 0
  } catch (e) {
    pendingCount.value = 0
  }
  return pendingCount.value
}

async function remove(id) {
  return tx(WRITE_STORE, 'readwrite', (s) => s.delete(id))
}

/**
 * 联网后集中补发队列里的写请求。
 *
 * 只对「网络类失败」重试（5xx / 无响应）；4xx 属于请求本身有问题
 * （如删除一条已被删掉的记录），重试一万次也不会成功，直接丢弃并告知用户。
 */
export async function flushQueue(requestFn) {
  if (flushing) return { synced: 0, dropped: 0 }
  flushing = true
  const out = { synced: 0, dropped: 0, errors: [] }
  try {
    let items = []
    try {
      items = (await tx(WRITE_STORE, 'readonly', (s) => s.getAll())) || []
    } catch (e) {
      return out
    }
    for (const item of items) {
      try {
        await requestFn({
          url: item.url,
          method: item.method,
          params: item.params || undefined,
          data: item.data || undefined,
          headers: item.headers || undefined,
          skipErrorToast: true,
          __replay: true
        })
        await remove(item.id)
        out.synced += 1
      } catch (err) {
        const status = err && err.response && err.response.status
        const networkIssue = !status || status >= 500
        item.tries = (item.tries || 0) + 1
        if (!networkIssue || item.tries >= 5) {
          await remove(item.id)
          out.dropped += 1
          out.errors.push(`${item.url}：${(err && err.message) || '失败'}`)
        }
      }
    }
    lastSyncAt.value = Date.now()
  } finally {
    flushing = false
    await refreshPending()
  }
  return out
}

// ---------- 读数缓存 ----------
export async function saveCache(key, value) {
  if (!key) return
  try {
    await tx(READ_STORE, 'readwrite', (s) => s.put({ key, value, savedAt: Date.now() }))
  } catch (e) {
    /* 隐私模式写不进 IndexedDB：降级为纯在线，不影响主流程 */
  }
}

export async function loadCache(key) {
  if (!key) return null
  try {
    const row = await tx(READ_STORE, 'readonly', (s) => s.get(key))
    if (!row) return null
    if (Date.now() - row.savedAt > CACHE_TTL_MS) {
      await tx(READ_STORE, 'readwrite', (s) => s.delete(key))
      return null
    }
    return row.value
  } catch (e) {
    return null
  }
}

export async function clearCache() {
  try {
    await tx(READ_STORE, 'readwrite', (s) => s.clear())
  } catch (e) {
    /* 忽略 */
  }
}

// ---------- 生命周期 ----------
let started = false

export function startOfflineSync(requestFn) {
  if (started || typeof window === 'undefined') return
  started = true

  refreshPending()
  if (navigator.onLine) {
    flushQueue(requestFn)
  }

  window.addEventListener('online', () => {
    if (!navigator.onLine) return
    flushQueue(requestFn)
  })

  // 兜底轮询：某些环境下 online 事件不触发（如切 WiFi 的过程），
  // 有积压时每 60 秒试一次就足够了
  setInterval(() => {
    if (navigator.onLine && pendingCount.value > 0) {
      flushQueue(requestFn)
    }
  }, 60 * 1000)
}
