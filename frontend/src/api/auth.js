import request from './request'

// 注册
export function register(data) {
  return request({
    url: '/auth/register',
    method: 'post',
    data
  })
}

// 登录
export function login(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data
  })
}

// 获取当前用户信息
export function getInfo() {
  return request({
    url: '/auth/info',
    method: 'get'
  })
}

// 更新用户资料
export function updateProfile(data) {
  return request({
    url: '/user/profile',
    method: 'put',
    data
  })
}

// 更新饮食偏好
export function updatePreference(data) {
  return request({
    url: '/user/preference',
    method: 'put',
    data
  })
}

// 获取指标（BMR/TDEE/推荐热量/BMI）
export function getMetrics() {
  return request({
    url: '/user/metrics',
    method: 'get'
  })
}

// 获取真实打卡数据（连续天数 / 累计天数 / 当月打卡日期），不做任何本地伪造
export function getCheckin(params) {
  return request({
    url: '/user/checkin',
    method: 'get',
    params,
    skipErrorToast: true
  })
}
