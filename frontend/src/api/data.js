import request from './request'

// 导出：返回 Blob（带鉴权头，不能用 window.open 直链）
export function exportData(params) {
  return request({
    url: '/data/export',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

// 导入：kind = weight | diet，file 为 File 对象
export function importData(kind, file) {
  const fd = new FormData()
  fd.append('file', file)
  return request({
    url: '/data/import',
    method: 'post',
    params: { kind },
    data: fd,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 提醒设置
export function getReminders() {
  return request({ url: '/data/reminders', method: 'get' })
}

export function updateReminders(data) {
  return request({ url: '/data/reminders', method: 'put', data })
}
