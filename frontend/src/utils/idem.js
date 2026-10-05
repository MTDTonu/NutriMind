// 生成一个一次性幂等键：每个「用户主动提交动作」一份，随请求头 X-Idempotency-Key 发送。
// 同一次提交（含离线补发 / 网络重试）复用同一把 key，服务端据此去重，避免重复落库。
export function genIdemKey() {
  try {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
      return window.crypto.randomUUID()
    }
  } catch (e) {
    /* 个别隐私模式下 crypto 不可用，回退到随机串 */
  }
  return 'idem-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10)
}
