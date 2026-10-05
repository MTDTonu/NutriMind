/**
 * 品牌标识集中管理。
 *
 * 全站文案（标题、侧栏、登录页、文档标题）一律从这里取值，
 * 改品牌名只需要动这一个文件。
 *
 * 命名依据：docs/升级改造方案-v3.md §1
 *   中文「知」承担智能感、「食」承担品类；英文 NutriMind 为合成词，便于域名与商店包名占位。
 */
export const BRAND = {
  // 中文名（双字，便于口语传播）
  name: '知食',
  // 英文名 / 包名用便名
  nameEn: 'NutriMind',
  // 中英联名，用于页面 <title> 与登录页主视觉
  full: '知食 NutriMind',
  // 一句话定位：让一条餐食记录 ≤15 秒，并把记录翻译成可执行建议
  tagline: '看懂你怎么吃',
  // 副标题：产品形态
  slogan: 'AI 饮食教练',
  // 完整描述（README / meta）
  desc: 'AI 智能减脂管理系统 · 自适应代谢 + 食物库 + 可视化复盘',
  version: '2.0.0'
}

/** 组合页面标题，如 document.title = pageTitle('首页') */
export function docTitle(page = '') {
  return page ? `${page} · ${BRAND.full}` : `${BRAND.full} · ${BRAND.tagline}`
}

export default BRAND
