import request from './request'

// 每日统计
export function dailyStats(params) {
  return request({
    url: '/stats/daily',
    method: 'get',
    params
  })
}

// 周度报告
export function weeklyStats() {
  return request({
    url: '/stats/weekly',
    method: 'get'
  })
}

// 体重趋势 range=day|week|month
export function weightTrend(params) {
  return request({
    url: '/stats/weight-trend',
    method: 'get',
    params
  })
}

// 营养素趋势 days=7
export function nutrientTrend(params) {
  return request({
    url: '/stats/nutrient-trend',
    method: 'get',
    params
  })
}
