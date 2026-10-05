import axios from 'axios'
import { showToast, showNotify } from 'vant'
import { getToken, clearAuth } from '@/utils/auth'
import { restoreSession } from '@/utils/session'
import {
  isQueueable,
  enqueue,
  isCacheable,
  cacheKey,
  saveCache,
  loadCache
} from '@/utils/offline'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

// 401 处理去重：token 失效时，冷启动往往有多个受保护接口同时返回 401
// （如挂载时的 fetchUserInfo + 首页统计等），若逐个处理会出现「重复弹窗 + 重复跳转」。
// 这里保证同一时间只处理一次，并异步延迟加载 router，打破与 @/router 的循环依赖。
let handling401 = false
async function handleUnauthorized(msg) {
  if (handling401) return
  handling401 = true
  clearAuth()
  if (msg) showNotify({ type: 'danger', message: msg })
  try {
    const mod = await import('@/router')
    if (mod.default.currentRoute.value.name !== 'login') {
      mod.default.replace({ name: 'login' })
    }
  } finally {
    // 留一个小窗口吸收并发 401，之后允许再次处理
    window.setTimeout(() => {
      handling401 = false
    }, 800)
  }
}

// 请求拦截器：注入 Bearer Token；离线时把写请求转入本地队列
service.interceptors.request.use(
  async (config) => {
    const token = getToken()
    if (token) {
      config.headers['Authorization'] = 'Bearer ' + token
    }

    // ---- 离线写 ----
    // navigator.onLine 只在明确断网时为 false；队列补发（__replay）本身走的就是在线请求，
    // 若此时又断网则会陷入「反复入队」的死循环，因此必须排除。
    if (
      typeof navigator !== 'undefined' &&
      navigator.onLine === false &&
      !config.__replay &&
      isQueueable(config)
    ) {
      try {
        await enqueue(config)
        const err = new Error('OFFLINE_QUEUED')
        err.__queued = true
        err.config = config
        throw err
      } catch (e) {
        if (e && e.__queued) throw e
        // 入队失败（隐私模式禁写 IndexedDB）：照常发请求，行为退化为原来的「在线才可用」
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：解包 {code, message, data}
service.interceptors.response.use(
  async (response) => {
    const res = response.data
    const skip = response.config && response.config.skipErrorToast
    if (res.code !== 200) {
      if (res.code === 401) {
        return handleTokenExpired(response.config, skip)
      }
      if (!skip) {
        showNotify({ type: 'danger', message: res.message || '请求失败' })
      }
      return Promise.reject(new Error(res.message || 'Error'))
    }
    // 读数缓存：成功响应顺手写一份，供离线时兜底
    if (isCacheable(response.config)) {
      saveCache(cacheKey(response.config), res.data)
    }
    return res.data
  },
  async (error) => {
    // 离线写：这不是失败，是「已排队待同步」
    if (error && error.__queued) {
      showToast({ type: 'success', message: '已离线保存，联网后自动同步' })
      return Promise.reject(error)
    }

    const res = error.response
    const skip = error.config && error.config.skipErrorToast
    if (res && res.status === 401) {
      return handleTokenExpired(error.config, skip)
    }

    // 网络层故障（没拿到响应）：尝试用缓存兜底，让页面不至于白屏报错
    if (!res && isCacheable(error.config)) {
      const cached = await loadCache(cacheKey(error.config))
      if (cached != null) {
        window.dispatchEvent(new CustomEvent('nm:offline-cache', { detail: cacheKey(error.config) }))
        return cached
      }
    }

    if (!skip) {
      const offline = typeof navigator !== 'undefined' && navigator.onLine === false
      showNotify({
        type: 'danger',
        message: offline
          ? '当前处于离线状态，正在展示上次缓存的数据'
          : (res && res.data && res.data.message) || '网络异常，请稍后重试'
      })
    }
    return Promise.reject(error)
  }
)

/**
 * Token 失效的统一出口：先用记住的凭据静默重登，成功则重放原请求（用户完全无感知），
 * 只有确实续不了（没记住过 / 密码改了）才走原来的 401 处理流程。
 */
async function handleTokenExpired(config, skip) {
  const already = config && config.__retriedAfterRefresh
  if (!already) {
    const ok = await restoreSession(true)
    if (ok && config) {
      // 标记后再请求一次；请求拦截器会重新读取新 Token
      return service({ ...config, __retriedAfterRefresh: true })
    }
  }
  handleUnauthorized(skip ? '' : '登录已过期，请重新登录')
  return Promise.reject(new Error('登录已过期'))
}

// 在途请求去重：同一「方法 + URL + body + params」的并发写请求只真正发一次，
// 其余直接复用同一个 Promise。这能天然兜住「双击提交 / 连点保存」造成的重复写，
// 又不影响两次意图不同的顺序提交（前一次 settled 后 pending 已清空）。
const _pending = new Map()

function _isFormData(v) {
  return typeof FormData !== 'undefined' && v instanceof FormData
}

function _requestSig(config) {
  return [
    String(config.method || 'get').toLowerCase(),
    config.url,
    _isFormData(config.data) ? '__formdata__' : JSON.stringify(config.data || ''),
    JSON.stringify(config.params || ''),
  ].join('|')
}

function request(config) {
  const method = String(config.method || 'get').toLowerCase()
  const mutating = ['post', 'put', 'patch', 'delete'].includes(method)
  // 离线补发（__replay）/ 文件上传 不参与去重
  if (!mutating || config.__replay || _isFormData(config.data)) {
    return service(config)
  }
  const sig = _requestSig(config)
  const existing = _pending.get(sig)
  if (existing) return existing
  const p = service(config).finally(() => _pending.delete(sig))
  _pending.set(sig, p)
  return p
}

export default request
