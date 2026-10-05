import request from './request'

// 读取当前用户的三套大模型配置（文字 / 视觉理解 / 语言转文字），api_key 已脱敏
export function getAISettings() {
  return request({
    url: '/user/ai-settings',
    method: 'get'
  })
}

// 更新三套大模型配置；保存后会自动同步写回 .env
// data 形如 { text: {provider, api_key, model, base_url}, vision: {...}, asr: {...} }
// 仅传入需要修改的能力；某能力不传则保持原值。api_key 传空字符串表示「保持原值不修改」。
export function updateAISettings(data) {
  return request({
    url: '/user/ai-settings',
    method: 'put',
    data,
    skipErrorToast: true
  })
}

// 可选厂商及其默认模型（用于下拉与厂商切换自动填值）
export function getAISettingsProviders() {
  return request({
    url: '/user/ai-settings/providers',
    method: 'get'
  })
}
