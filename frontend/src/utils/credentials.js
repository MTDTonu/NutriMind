/**
 * 登录凭据持久化（「一次登录，长期保持」的基础设施）。
 *
 * 设计取向：不是签发一个永不过期的 Token，而是「记住账号密码 + Token 失效时静默重登」。
 * 这样后端随时可以让某个 Token 失效、也可以改密码强制下线，比长期 Token 安全得多，
 * 用户体验上又等价于永久登录。
 *
 * 存储安全：做一层可逆混淆（XOR + Base64），避免明文密码直接躺在 localStorage。
 * 注意：混淆不等于加密——能拦住随手翻控制台的人，拦不住本机恶意程序。
 * 本项目定位为个人/家庭单机部署，此取舍可接受；若部署到公网多人使用，
 * 应改为 httpOnly Cookie + Refresh Token 方案。
 */

const CRED_KEY = 'jf_cred'
const OBFUSCATE_KEY = 'slim-enjoyment'

// 演示账号（同时用于登录页自动填充）
export const DEMO_ACCOUNT = {
  username: 'demo',
  password: 'demo1234'
}

function encode(str) {
  let mixed = ''
  for (let i = 0; i < str.length; i++) {
    mixed += String.fromCharCode(str.charCodeAt(i) ^ OBFUSCATE_KEY.charCodeAt(i % OBFUSCATE_KEY.length))
  }
  return btoa(unescape(encodeURIComponent(mixed)))
}

function decode(b64) {
  const mixed = decodeURIComponent(escape(atob(b64)))
  let str = ''
  for (let i = 0; i < mixed.length; i++) {
    str += String.fromCharCode(mixed.charCodeAt(i) ^ OBFUSCATE_KEY.charCodeAt(i % OBFUSCATE_KEY.length))
  }
  return str
}

/** 保存凭据（记住登录）。 */
export function saveCredentials(username, password) {
  if (!username || !password) return
  try {
    localStorage.setItem(CRED_KEY, JSON.stringify({ u: encode(username), p: encode(password) }))
  } catch (e) {
    // 隐私模式下 localStorage 可能不可写，忽略即可（退化为不记住）
  }
}

/** 读取凭据，未保存或解析失败返回 null。 */
export function getCredentials() {
  try {
    const raw = localStorage.getItem(CRED_KEY)
    if (!raw) return null
    const obj = JSON.parse(raw)
    if (!obj || !obj.u || !obj.p) return null
    return { username: decode(obj.u), password: decode(obj.p) }
  } catch (e) {
    return null
  }
}

export function hasCredentials() {
  return !!getCredentials()
}

/** 忘记已保存的凭据（登出/切换账号时调用）。 */
export function clearCredentials() {
  try {
    localStorage.removeItem(CRED_KEY)
  } catch (e) {
    // ignore
  }
}
