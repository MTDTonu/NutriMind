// 统一导航配置：桌面侧边栏 + 移动端底部 Tab 共用

// 桌面侧边栏（「我的」不在此列：由底部用户卡进入，避免两个入口重复）
export const navItems = [
  { name: 'home', label: '首页', icon: 'home', title: '首页' },
  { name: 'diet', label: '饮食记录', icon: 'diet', title: '饮食记录' },
  { name: 'exercise', label: '运动', icon: 'exercise', title: '运动' },
  { name: 'stats', label: '数据统计', icon: 'chart', title: '数据统计' },
  { name: 'ai', label: 'AI 助手', icon: 'ai', title: 'AI 助手' }
]

// 移动端底部 Tab（5 个）
// 「数据统计」不再占用 Tab：统计内容已并入首页；
// 空出的位置给「运动」（高频功能）。「我的」仍保留（移动端没有常驻侧栏）。
export const mobileTabs = [
  { name: 'home', label: '首页', icon: 'home' },
  { name: 'diet', label: '记录', icon: 'diet' },
  { name: 'ai', label: 'AI', icon: 'ai' },
  { name: 'exercise', label: '运动', icon: 'exercise' },
  { name: 'mine', label: '我的', icon: 'user' }
]

// 路由名 -> 页面标题（顶栏面包屑用；独立于 navItems，保证所有路由都有标题）
export const titleMap = {
  login: '登录',
  register: '注册',
  'profile-init': '完善资料',
  home: '首页',
  diet: '饮食记录',
  exercise: '运动',
  stats: '数据统计',
  ai: 'AI 助手',
  mine: '我的'
}
