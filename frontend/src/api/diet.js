import request from './request'
import { genIdemKey } from '@/utils/idem'

// 添加饮食记录
export function addDiet(data) {
  return request({
    url: '/diet/add',
    method: 'post',
    data,
    headers: { 'X-Idempotency-Key': genIdemKey() }
  })
}

// 饮食记录列表（按日期）
export function listDiet(params) {
  return request({
    url: '/diet/list',
    method: 'get',
    params
  })
}

// 更新某条饮食记录
export function updateDiet(id, data) {
  return request({
    url: '/diet/' + id,
    method: 'put',
    data
  })
}

// 删除某条饮食记录
export function deleteDiet(id) {
  return request({
    url: '/diet/' + id,
    method: 'delete'
  })
}

// 今日饮食汇总
export function todayDiet(params) {
  return request({
    url: '/diet/today',
    method: 'get',
    params
  })
}
