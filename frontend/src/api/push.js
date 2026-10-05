import request from './request'

// VAPID 公钥：浏览器订阅时的 applicationServerKey
export function getPushPublicKey() {
  return request({ url: '/push/public-key', method: 'get' })
}

// 订阅 / 状态 / 退订
export function getPushStatus() {
  return request({ url: '/push/status', method: 'get' })
}

export function subscribePush(data) {
  return request({ url: '/push/subscribe', method: 'post', data })
}

export function unsubscribePush(endpoint) {
  return request({ url: '/push/unsubscribe', method: 'delete', data: { endpoint } })
}

export function testPush(payload) {
  return request({ url: '/push/test', method: 'post', data: payload || {} })
}
