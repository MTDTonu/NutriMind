/**
 * 会话维持：Token 过期 / 缺失时，用记住的凭据静默重登。
 *
 * 三个入口：
 * 1. 路由守卫  —— 冷启动或深链接刷新不必回登录页
 * 2. 请求拦截器 —— 接口返回 401 时自动续期并重放原请求，用户无感知
 * 3. 登录页    —— 首次进入时若已记住凭据，直接自动登录
 *
 * 用独立的裸 axios 实例（不经 request.js），避免「401 → 重登 → 又 401」的递归。
 */
import axios from 'axios'
import { getToken, setToken, setUser, setProfileComplete } from '@/utils/auth'
import { getCredentials, hasCredentials, clearCredentials } from '@/utils/credentials'

const raw = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' }
})

export function isProfileComplete(user) {
  return !!(user && user.current_weight != null && user.target_weight != null && user.height != null)
}

/**
 * 本地判断 Token 是否已过期（含 60 秒缓冲，避免边界上刚好失效）。
 * JWT payload 是 Base64URL，需转为标准 Base64 再解。
 * 解析失败时保守判定为「未过期」，交给服务端裁决。
 */
export function tokenExpired() {
  const token = getToken()
  if (!token) return true
  try {
    const seg = token.split('.')[1]
    if (!seg) return false
    const payload = JSON.parse(decodeURIComponent(escape(atob(seg.replace(/-/g, '+').replace(/_/g, '/')))))
    if (!payload.exp) return false
    return payload.exp * 1000 - Date.now() < 60000
  } catch (e) {
    return false
  }
}

/** 同步写入 pinia（动态 import 打破 api → request → session → store 的循环依赖）。 */
async function syncPinia(token, user, complete) {
  try {
    const mod = await import('@/store/modules/user')
    mod.useUserStore().applySession(token, user, complete)
  } catch (e) {
    // pinia 尚未激活时忽略，localStorage 已写入，刷新后仍会生效
  }
}

async function doLogin(cred) {
  const { data } = await raw.post('/auth/login', { username: cred.username, password: cred.password })
  if (!data || data.code !== 200) {
    const err = new Error((data && data.message) || '自动登录失败')
    // 业务层明确拒绝 = 账号或密码确实不对（如改过密码、账号被删）
    err.invalidCredential = true
    throw err
  }
  const { token, user } = data.data
  const complete = isProfileComplete(user)
  setToken(token)
  setUser(user)
  setProfileComplete(complete)
  await syncPinia(token, user, complete)
  return true
}

// 并发去重：冷启动往往有多个守卫/请求同时触发恢复，只发一次登录请求
let restoring = null

/**
 * 恢复会话。
 * @param {boolean} force true=即使 Token 看起来有效也重新登录（用于 401 续期）
 * @returns {Promise<boolean>} 是否处于已登录状态
 */
export function restoreSession(force = false) {
  if (!hasCredentials()) return Promise.resolve(false)
  if (!force && getToken() && !tokenExpired()) return Promise.resolve(true)

  if (restoring) return restoring

  const cred = getCredentials()
  if (!cred) return Promise.resolve(false)

  restoring = doLogin(cred)
    .catch((err) => {
      // 只有「凭据确实无效」才清除；网络抖动 / 服务未启动必须保留，
      // 否则一次断网就把用户记住的账号抹掉了
      const status = err && err.response && err.response.status
      if (err && (err.invalidCredential || status === 401)) {
        clearCredentials()
      }
      return false
    })
    .finally(() => {
      // 留一个 tick 让并发调用方都能拿到这次结果
      setTimeout(() => {
        restoring = null
      }, 0)
    })

  return restoring
}

/** 彻底登出：清 Token + 用户信息 + 记住的凭据。 */
export async function forgetSession() {
  clearCredentials()
  try {
    const mod = await import('@/store/modules/user')
    mod.useUserStore().logout()
  } catch (e) {
    // ignore
  }
}
