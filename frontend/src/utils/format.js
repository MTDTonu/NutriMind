// 日期、数值格式化工具

export function padZero(n) {
  return n < 10 ? '0' + n : '' + n
}

// 格式化日期为 YYYY-MM-DD
export function formatDate(date) {
  const d = date instanceof Date ? date : new Date(date)
  if (isNaN(d.getTime())) return ''
  return (
    d.getFullYear() +
    '-' +
    padZero(d.getMonth() + 1) +
    '-' +
    padZero(d.getDate())
  )
}

// YYYY-MM-DD HH:mm
export function formatDateTime(date) {
  const d = date instanceof Date ? date : new Date(date)
  if (isNaN(d.getTime())) return ''
  return formatDate(d) + ' ' + padZero(d.getHours()) + ':' + padZero(d.getMinutes())
}

// 取今天 YYYY-MM-DD
export function today() {
  return formatDate(new Date())
}

// 相对今天的偏移日期 YYYY-MM-DD
export function offsetDate(days) {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return formatDate(d)
}

// 数值保留 n 位小数（去掉末尾 0）
export function roundNum(val, digits = 0) {
  if (val == null || isNaN(Number(val))) return 0
  const n = Number(val)
  const fixed = Number(n.toFixed(digits))
  return fixed
}

// 千分位
export function thousands(val) {
  if (val == null) return '0'
  return Number(val).toLocaleString('en-US')
}

// 星期中文
export function weekdayCN(dateStr) {
  const d = new Date(dateStr)
  const arr = ['日', '一', '二', '三', '四', '五', '六']
  return '周' + arr[d.getDay()]
}

// 友好日期：今天 / 昨天 / YYYY-MM-DD
export function friendlyDate(dateStr) {
  const t = today()
  if (dateStr === t) return '今天'
  if (dateStr === offsetDate(-1)) return '昨天'
  return dateStr
}
