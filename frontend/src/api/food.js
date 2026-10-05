import request from './request'

// 分类字典
export function foodCategories() {
  return request({ url: '/foods/categories', method: 'get' })
}

// 食物搜索：keyword / category / favorite
export function searchFoods(params) {
  return request({ url: '/foods/search', method: 'get', params })
}

// 我的收藏
export function favoriteFoods() {
  return request({ url: '/foods/favorites', method: 'get' })
}

// 高频食物（快捷入口）
export function frequentFoods(params) {
  return request({ url: '/foods/frequent', method: 'get', params })
}

// 食物详情（含全部份量单位）
export function foodDetail(id) {
  return request({ url: '/foods/' + id, method: 'get' })
}

// 收藏 / 取消收藏
export function toggleFavorite(id) {
  return request({ url: '/foods/' + id + '/favorite', method: 'post' })
}

// 自定义食物
export function createFood(data) {
  return request({ url: '/foods/custom', method: 'post', data })
}

// 从食物库一键写入饮食记录（服务端完成换算）
export function quickAddFood(data) {
  return request({ url: '/foods/quick-add', method: 'post', data })
}
