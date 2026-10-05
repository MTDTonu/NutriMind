// 运动库：内置常见运动及其 MET 值（每分钟每千克体重消耗的 kcal）
//
// MET 取自 Ainsworth《Compendium of Physical Activities》的常用区间中位值，
// 属于群体统计值：同一运动不同强度可差 2 倍，因此这里只做「量级可信」的估算，
// 具体消耗仍以体重 × 时长为主变量，界面上不谎报精度。

export const EXERCISE_CATEGORIES = [
  { key: 'cardio', label: '有氧' },
  { key: 'strength', label: '力量' },
  { key: 'ball', label: '球类' },
  { key: 'mind', label: '柔韧' },
  { key: 'daily', label: '日常' },
  { key: 'legacy', label: '其他' }
]

// key 沿用旧值（running / walking ...）以保证历史记录仍能反查到中文名，
// 新增运动用可读英文 key，避免中文 key 在导入导出与未来迁移中产生编码问题。
export const EXERCISE_LIBRARY = [
  // 有氧
  { key: 'walking', label: '快走', cat: 'cardio', met: 4.3, icon: 'bolt' },
  { key: 'running', label: '跑步', cat: 'cardio', met: 9.8, icon: 'bolt' },
  { key: 'jogging', label: '慢跑', cat: 'cardio', met: 7.0, icon: 'bolt' },
  { key: 'cycling', label: '骑行', cat: 'cardio', met: 7.5, icon: 'bolt' },
  { key: 'swimming', label: '游泳', cat: 'cardio', met: 7.0, icon: 'drop' },
  { key: 'rope', label: '跳绳', cat: 'cardio', met: 11.0, icon: 'bolt' },
  { key: 'hiit', label: 'HIIT', cat: 'cardio', met: 9.0, icon: 'fire' },
  { key: 'elliptical', label: '椭圆机', cat: 'cardio', met: 5.0, icon: 'bolt' },
  { key: 'stair', label: '爬楼梯', cat: 'cardio', met: 8.8, icon: 'bolt' },
  { key: 'rowing', label: '划船机', cat: 'cardio', met: 7.0, icon: 'bolt' },
  { key: 'aerobics', label: '有氧操', cat: 'cardio', met: 6.5, icon: 'fire' },

  // 力量
  { key: 'strength', label: '力量训练', cat: 'strength', met: 5.0, icon: 'exercise' },
  { key: 'strength_hard', label: '大重量训练', cat: 'strength', met: 6.0, icon: 'exercise' },
  { key: 'dumbbell', label: '哑铃训练', cat: 'strength', met: 3.5, icon: 'exercise' },
  { key: 'squat', label: '深蹲', cat: 'strength', met: 5.0, icon: 'exercise' },
  { key: 'pushup', label: '俯卧撑', cat: 'strength', met: 8.0, icon: 'exercise' },
  { key: 'plank', label: '平板支撑', cat: 'strength', met: 3.3, icon: 'exercise' },

  // 球类
  { key: 'basketball', label: '篮球', cat: 'ball', met: 8.0, icon: 'target' },
  { key: 'badminton', label: '羽毛球', cat: 'ball', met: 5.5, icon: 'target' },
  { key: 'tabletennis', label: '乒乓球', cat: 'ball', met: 4.0, icon: 'target' },
  { key: 'tennis', label: '网球', cat: 'ball', met: 7.3, icon: 'target' },
  { key: 'soccer', label: '足球', cat: 'ball', met: 7.0, icon: 'target' },
  { key: 'volleyball', label: '排球', cat: 'ball', met: 4.0, icon: 'target' },

  // 柔韧
  { key: 'yoga', label: '瑜伽', cat: 'mind', met: 3.0, icon: 'star' },
  { key: 'pilates', label: '普拉提', cat: 'mind', met: 3.0, icon: 'star' },
  { key: 'stretch', label: '拉伸', cat: 'mind', met: 2.3, icon: 'star' },
  { key: 'taichi', label: '太极', cat: 'mind', met: 3.0, icon: 'star' },

  // 日常
  { key: 'stroll', label: '散步', cat: 'daily', met: 3.0, icon: 'bolt' },
  { key: 'commute_bike', label: '骑车通勤', cat: 'daily', met: 6.8, icon: 'bolt' },
  { key: 'hike', label: '徒步', cat: 'daily', met: 6.0, icon: 'bolt' },
  { key: 'housework', label: '家务劳动', cat: 'daily', met: 3.5, icon: 'bolt' },
  { key: 'dogwalk', label: '遛狗', cat: 'daily', met: 3.0, icon: 'bolt' },
  { key: 'dance', label: '跳舞', cat: 'daily', met: 5.0, icon: 'fire' }
]

const BY_KEY = EXERCISE_LIBRARY.reduce((m, x) => {
  m[x.key] = x
  return m
}, {})

// 历史数据里存过中文名（早期版本与演示数据直接写「瑜伽」「户外骑行」），
// 只按 key 查会漏掉这些记录：补一层「中文名 → 条目」的反查。
const BY_LABEL = EXERCISE_LIBRARY.reduce((m, x) => {
  m[x.label] = x
  return m
}, {})

// 演示数据/旧版里出现过、但与库中名称不完全一致的叫法
const ALIASES = {
  户外骑行: 'commute_bike',
  骑车: 'cycling',
  跑步机: 'running',
  举铁: 'strength'
}

export function findExercise(type) {
  if (!type) return null
  if (BY_KEY[type]) return BY_KEY[type]
  if (BY_LABEL[type]) return BY_LABEL[type]
  const alias = ALIASES[type]
  return alias ? BY_KEY[alias] : null
}

// 未收录的运动照原样显示：显示「别的运动」比显示「unknown」强得多
export function exerciseLabel(type) {
  const item = findExercise(type)
  return item ? item.label : type
}

export function exerciseIcon(type) {
  const item = findExercise(type)
  return item ? item.icon : 'fire'
}

// 运动消耗估算：kcal = MET × 体重(kg) × 时长(小时)
// 体重缺失时返回 0：宁可不给数，也不用一个编造的体重算出来假数据。
export function calcExerciseBurn(type, durationMin, weightKg) {
  const item = findExercise(type)
  const met = item ? item.met : 5.0
  if (!durationMin || !weightKg) return 0
  const hours = Number(durationMin) / 60
  return Math.round(met * Number(weightKg) * hours)
}

// 时长档位：把「填多少分钟」变成一个决策成本更低的选择
export const DURATION_PRESETS = [10, 20, 30, 45, 60, 90]
