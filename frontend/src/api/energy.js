import request from './request'

// 当前目标方案（TDEE 反推 + 目标计算）
export function energyTarget(params) {
  return request({ url: '/energy/target', method: 'get', params })
}

// 反推真实 TDEE（含数据充分性说明）
export function energyAdaptive(params) {
  return request({ url: '/energy/adaptive', method: 'get', params })
}

// 执行一次周校准（写入 tdee_adaptive 并重算推荐摄入）
export function calibrateEnergy(params) {
  return request({ url: '/energy/calibrate', method: 'post', params })
}

// 切换目标模式：deficit（热量缺口）/ rate（每周减重）
export function setEnergyTarget(data) {
  return request({ url: '/energy/target', method: 'post', data })
}
