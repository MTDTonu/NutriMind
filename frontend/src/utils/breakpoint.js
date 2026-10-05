// 响应式断点：以 1024px 为界区分桌面 / 移动
import { ref } from 'vue'

const MOBILE_MAX = 1023
export const isMobileRef = ref(
  typeof window !== 'undefined'
    ? window.matchMedia(`(max-width: ${MOBILE_MAX}px)`).matches
    : false
)

let mql = null
function handler(e) {
  isMobileRef.value = e.matches
}

export function setupBreakpoint() {
  if (typeof window === 'undefined') return
  mql = window.matchMedia(`(max-width: ${MOBILE_MAX}px)`)
  mql.addEventListener('change', handler)
}
