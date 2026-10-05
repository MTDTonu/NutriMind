const TOKEN_KEY = 'jf_token'
const USER_KEY = 'jf_user'
const PROFILE_KEY = 'jf_profile_complete'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export function getUser() {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch (e) {
    return null
  }
}

export function setUser(user) {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function getProfileComplete() {
  return localStorage.getItem(PROFILE_KEY) === '1'
}

export function setProfileComplete(flag) {
  localStorage.setItem(PROFILE_KEY, flag ? '1' : '0')
}

export function isLoggedIn() {
  return !!getToken()
}

// 资料是否完善：token 存在 且 profile_complete 标记为 true
export function isProfileComplete() {
  return isLoggedIn() && getProfileComplete()
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(PROFILE_KEY)
}
