import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, register as registerApi, getInfo } from '@/api/auth'
import * as authUtil from '@/utils/auth'
import { saveCredentials, clearCredentials } from '@/utils/credentials'
import { isProfileComplete as judgeProfileComplete } from '@/utils/session'

const TOKEN_KEY = 'jf_token'
const USER_KEY = 'jf_user'
const PROFILE_KEY = 'jf_profile_complete'

export const useUserStore = defineStore(
  'user',
  () => {
    const token = ref(authUtil.getToken() || '')
    const userInfo = ref(authUtil.getUser() || {})
    const isProfileComplete = ref(authUtil.isProfileComplete())

    const isLoggedIn = computed(() => !!token.value)

    // 登录
    // remember=true 时记住凭据：之后 Token 过期会静默重登，等价于长期保持登录
    async function login(payload) {
      const data = await loginApi({ username: payload.username, password: payload.password })
      const complete = judgeProfileComplete(data.user)
      applySession(data.token, data.user, complete)
      if (payload.remember !== false) {
        saveCredentials(payload.username, payload.password)
      } else {
        clearCredentials()
      }
      return data
    }

    /**
     * 把一次成功的登录结果写入本地 + 本 store。
     * 普通登录与静默重登共用同一条路径，保证两边状态永远一致。
     */
    function applySession(newToken, user, complete) {
      token.value = newToken
      userInfo.value = { ...user, is_profile_complete: complete }
      isProfileComplete.value = complete
      authUtil.setToken(newToken)
      authUtil.setUser(userInfo.value)
      authUtil.setProfileComplete(complete)
    }

    // 注册
    async function register(payload) {
      const data = await registerApi(payload)
      token.value = data.token
      userInfo.value = data.user
      isProfileComplete.value = false
      authUtil.setToken(data.token)
      authUtil.setUser(data.user)
      authUtil.setProfileComplete(false)
      return data
    }

    // 拉取最新用户信息
    async function fetchUserInfo() {
      const user = await getInfo()
      userInfo.value = user
      const complete =
        user &&
        user.current_weight != null &&
        user.target_weight != null &&
        user.height != null
      isProfileComplete.value = complete
      userInfo.value.is_profile_complete = complete
      authUtil.setUser(user)
      authUtil.setProfileComplete(complete)
      return user
    }

    // 更新本地用户信息（资料保存后调用）
    function updateUserInfo(partial) {
      userInfo.value = { ...userInfo.value, ...partial }
      const complete =
        userInfo.value.current_weight != null &&
        userInfo.value.target_weight != null &&
        userInfo.value.height != null
      isProfileComplete.value = complete
      userInfo.value.is_profile_complete = complete
      authUtil.setUser(userInfo.value)
      authUtil.setProfileComplete(complete)
    }

    // 设置资料完成状态
    function setProfileCompleteFlag(flag) {
      isProfileComplete.value = flag
      authUtil.setProfileComplete(flag)
    }

    // 登出（同时清除「记住的凭据」，否则下一次进入会被自动重登回去）
    function logout() {
      token.value = ''
      userInfo.value = {}
      isProfileComplete.value = false
      clearCredentials()
      authUtil.clearAuth()
    }

    return {
      token,
      userInfo,
      isProfileComplete,
      isLoggedIn,
      login,
      register,
      fetchUserInfo,
      updateUserInfo,
      setProfileCompleteFlag,
      applySession,
      logout
    }
  },
  {
    persist: false // 已通过 utils/auth.js 手动持久化到 localStorage
  }
)
