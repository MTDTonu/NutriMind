import request from './request'

// 添加饮水记录
export function addWater(data) {
  return request({
    url: '/water/add',
    method: 'post',
    data
  })
}

// 今日饮水汇总
export function todayWater(params) {
  return request({
    url: '/water/today',
    method: 'get',
    params
  })
}
