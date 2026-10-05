// 极简事件总线：用于跨组件的轻量通信（如 ⌘K 唤起食物选择器）。
// 只在确实需要「任意组件 -> 任意组件」的场景使用，优先仍应使用 props / emit。
const listeners = new Map()

export function on(event, fn) {
  if (!listeners.has(event)) listeners.set(event, new Set())
  listeners.get(event).add(fn)
  return () => off(event, fn)
}

export function off(event, fn) {
  const set = listeners.get(event)
  if (set) set.delete(fn)
}

export function emit(event, payload) {
  const set = listeners.get(event)
  if (!set) return
  set.forEach((fn) => {
    try {
      fn(payload)
    } catch (e) {
      // 单个订阅者异常不应影响其它订阅者
      console.error('[bus]', event, e)
    }
  })
}

export default { on, off, emit }
