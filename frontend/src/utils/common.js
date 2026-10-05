// 通用计算：BMI、BMR、TDEE、MET 估算

import { formatDate } from './format'

// 计算 BMI = 体重(kg) / 身高(m)^2
export function calcBMI(weight, heightCm) {
  if (!weight || !heightCm) return 0
  const h = Number(heightCm) / 100
  const bmi = Number(weight) / (h * h)
  return Math.round(bmi * 10) / 10
}

export function bmiLevel(bmi) {
  if (bmi < 18.5) return '偏瘦'
  if (bmi < 24) return '正常'
  if (bmi < 28) return '偏胖'
  return '肥胖'
}

// 活动系数映射
export const ACTIVITY_MAP = {
  sedentary: { label: '久坐少动', factor: 1.2 },
  light: { label: '轻度活动', factor: 1.375 },
  moderate: { label: '中度活动', factor: 1.55 },
  active: { label: '高强度活动', factor: 1.725 }
}

// 前端表单（字符串）与后端模型（int）之间的映射。
// 后端约定：gender 0 女 / 1 男；activity_level 1 久坐 / 2 轻度 / 3 中度 / 4 高强度。
// 前端若直接把 'male' / 'light' 提交，会被 pydantic 校验拦截（400），导致资料无法保存。
export const GENDER_TO_INT = { male: 1, female: 0 }
export const INT_TO_GENDER = { 1: 'male', 0: 'female' }

// 活动水平：前端 key -> 后端 int
const ACTIVITY_TO_INT = { sedentary: 1, light: 2, moderate: 3, active: 4 }
export function activityToInt(level) {
  return ACTIVITY_TO_INT[level] != null ? ACTIVITY_TO_INT[level] : 2
}
// 活动水平：后端 int -> 前端 key（用于回显）
const INT_TO_ACTIVITY = { 1: 'sedentary', 2: 'light', 3: 'moderate', 4: 'active' }
export function activityFromInt(level) {
  return INT_TO_ACTIVITY[level] != null ? INT_TO_ACTIVITY[level] : 'light'
}

// 基础代谢 BMR（Mifflin-St Jeor）
export function calcBMR({ gender, weight, height, age }) {
  if (!gender || !weight || !height || !age) return 0
  const s = gender === 'male' ? 5 : -161
  const bmr = 10 * Number(weight) + 6.25 * Number(height) - 5 * Number(age) + s
  return Math.round(bmr)
}

// 每日总消耗 TDEE = BMR * 活动系数
export function calcTDEE(bmr, activityLevel) {
  const factor = (ACTIVITY_MAP[activityLevel] || ACTIVITY_MAP.sedentary).factor
  return Math.round(bmr * factor)
}

// 推荐摄入热量（减脂：TDEE - 500 缺口，不低于 BMR*0.8）
export function calcRecommendCalorie(tdee, bmr) {
  let rec = tdee - 500
  const floor = Math.round(bmr * 0.8)
  if (rec < floor) rec = floor
  return Math.max(rec, 1000)
}

// 预计达成时间（周）：目标减重 / 每周可减(缺口/7700 kg)
export function estimateWeeks(weight, target, recommend, tdee) {
  const diff = Number(weight) - Number(target)
  if (diff <= 0) return 0
  const deficit = Math.max(tdee - recommend, 200) // kcal/天
  const weekLossKg = (deficit * 7) / 7700
  if (weekLossKg <= 0) return 0
  return Math.max(1, Math.ceil(diff / weekLossKg))
}

// MET 表（每分钟每千克体重消耗 kcal）
// 完整运动库已迁到 config/exercises.js（含分类、图标与时长档位），
// 这里保留旧导出名做兼容，避免历史引用点一次性全改引发漏改。
export { exerciseLabel, calcExerciseBurn } from '../config/exercises'

// 进食类型中文
export const MEAL_TYPE_MAP = {
  breakfast: '早餐',
  lunch: '午餐',
  dinner: '晚餐',
  snack: '加餐'
}

export function mealLabel(type) {
  return MEAL_TYPE_MAP[type] || type
}

// 当前日期字符串
export function nowDate() {
  return formatDate(new Date())
}
