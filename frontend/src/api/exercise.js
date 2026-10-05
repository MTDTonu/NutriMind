import request from './request'
import { genIdemKey } from '@/utils/idem'

// 运动记录列表（传 date 只取当天；不传返回全部）
export function listExercise(params) {
  return request({
    url: '/exercise/list',
    method: 'get',
    params
  })
}

// 添加运动记录
export function addExercise(data) {
  return request({
    url: '/exercise/add',
    method: 'post',
    data,
    headers: { 'X-Idempotency-Key': genIdemKey() }
  })
}

// 按天聚合的运动小结（默认近 7 天）
export function weeklyExercise(params) {
  return request({
    url: '/exercise/weekly',
    method: 'get',
    params
  })
}

// 删除运动记录
export function deleteExercise(id) {
  return request({
    url: '/exercise/' + id,
    method: 'delete'
  })
}
