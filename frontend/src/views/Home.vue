<template>
  <div class="page home">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-main">
        <span class="eyebrow">{{ todayCn }}</span>
        <h2 class="hero-greet">{{ greeting }}，{{ nickname }}</h2>
        <p class="hero-sub">
          连续打卡 <b class="num">{{ checkinDays }}</b> 天
          <template v-if="gapKg > 0"> · 距离目标还差 <b class="num">{{ gapKg }}</b> kg</template>
        </p>
      </div>
      <button class="hero-cta" @click="openPicker()">
        <AppIcon name="plus" :size="16" />
        <span>记一笔</span>
        <kbd v-if="!isMobile">⌘K</kbd>
      </button>
    </section>

    <div class="home-grid">
      <!-- 左列：今天的状态 -->
      <div class="col stagger">
        <!-- 结论卡：先给可执行结论，再给数字 -->
        <section class="card verdict">
          <div class="v-text">
            <h3 class="v-title">
              <!-- 超额时文案必须跟着翻：否则会出现「今天还能吃 366」与「已超出 366」自相矛盾 -->
              {{ remaining < 0 ? '今天已超出' : '今天还能吃' }}
              <b class="num" :class="{ over: remaining < 0 }">{{ Math.abs(remaining) }}</b>
              <span class="v-unit">kcal</span>
            </h3>
            <p class="v-hint">{{ remainingHint }}</p>
            <div class="v-nums">
              <div><span>已摄入</span><b class="num">{{ Math.round(todayData.total_calorie) }}</b></div>
              <div><span>今日目标</span><b class="num">{{ recommend }}</b></div>
              <div><span>已记录</span><b class="num">{{ todayData.items?.length || 0 }}</b><i>条</i></div>
            </div>
          </div>
          <CalorieCard :intake="todayData.total_calorie" :recommend="recommend" :size="ringSize" />
        </section>

        <!-- 三餐时间轴：缺哪餐一眼看见，那一行本身就是入口 -->
        <section class="card timeline">
          <div class="tl-head">
            <h3>今天吃了什么</h3>
            <span class="tl-note">{{ eatenMeals }} / 3 餐已记录</span>
          </div>

          <div class="tl">
            <div class="tl-row" v-for="m in timeline" :key="m.type">
              <span class="tl-dot" :class="{ done: m.items.length }" />
              <div class="tl-body">
                <div class="tl-top">
                  <span class="tl-name">{{ m.label }}</span>
                  <span class="tl-time">{{ m.time }}</span>
                  <span class="tl-cal num" v-if="m.items.length">{{ m.total }} kcal</span>
                  <button class="tl-add" @click="openPicker(m.type)">
                    {{ m.items.length ? '再加' : '记录' }}
                  </button>
                </div>
                <ul class="tl-items" v-if="m.items.length">
                  <li v-for="it in m.items" :key="it.id">
                    <span class="ti-name ellipsis">{{ it.food_desc }}</span>
                    <span class="ti-cal num">{{ Math.round(it.calorie) }} kcal</span>
                  </li>
                </ul>
                <p v-else class="tl-empty">还没记录，点「记录」从食物库里选，1 步就完</p>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- 右列：营养、食谱、快捷操作 -->
      <div class="col stagger">
        <section class="card macros">
          <h3 class="m-title">三大营养素</h3>
          <div class="macro" v-for="n in nutri" :key="n.key">
            <div class="m-top">
              <span class="m-label">{{ n.label }}</span>
              <span class="m-val num">{{ n.cur }}<i>/{{ n.target }}g</i></span>
            </div>
            <div class="m-track">
              <span class="m-fill" :style="{ width: n.percent + '%', background: n.color }" />
            </div>
          </div>
        </section>

        <!-- AI 食谱 -->
        <section class="card plan">
          <div class="card-head">
            <h3 class="m-title">今日食谱建议</h3>
            <button class="ghost" @click="regeneratePlan" :disabled="planLoading">
              <AppIcon name="refresh" :size="13" />
              <span>{{ hasPlan ? '换一版' : '生成' }}</span>
            </button>
          </div>

          <div v-if="planLoading" class="plan-loading">
            <van-loading size="18px" color="var(--lime-ink)" />
            <span>正在按你的目标热量搭配…</span>
          </div>
          <div v-else-if="!hasPlan" class="plan-empty">
            <span class="pe-ico"><AppIcon name="bolt" :size="20" /></span>
            <p class="pe-title">还没有今日食谱</p>
            <p class="pe-sub">根据你的目标热量生成一日三餐，可直接照着吃</p>
            <button class="pe-btn" @click="regeneratePlan">立即生成</button>
          </div>
          <template v-else>
            <div class="meal" v-for="m in mealList" :key="m.type">
              <div class="meal-head">
                <span class="meal-name"><i class="m-dot" :class="m.type" />{{ m.label }}</span>
                <span class="meal-cal num">{{ m.total }} kcal</span>
              </div>
              <div class="meal-items">
                <button class="meal-item" v-for="(it, i) in m.items" :key="i" @click="showMealDetail(m.type, it)">
                  <span class="it-name ellipsis">{{ it.name }}</span>
                  <span class="it-cal num">{{ it.calorie }} kcal</span>
                </button>
                <div v-if="!m.items.length" class="meal-empty">暂无菜品</div>
              </div>
              <button class="meal-add" @click="openPicker(MEAL_INT[m.type])">照这餐记录</button>
            </div>
            <div class="adapt" v-if="plan.adapt_desc">
              <AppIcon name="bolt" :size="15" />
              <span>{{ plan.adapt_desc }}</span>
            </div>
          </template>
        </section>

        <!-- 快捷操作 -->
        <section class="card actions">
          <h3 class="m-title">顺手记一下</h3>
          <div class="act-grid">
            <button class="act" @click="showWeight = true">
              <span class="act-ico"><AppIcon name="target" :size="18" /></span>
              <span class="act-txt"><b>体重</b><i>{{ latestWeight ? latestWeight + ' kg' : '今天还没记' }}</i></span>
            </button>
            <button class="act" @click="openWater()">
              <span class="act-ico"><AppIcon name="drop" :size="18" /></span>
              <span class="act-txt">
                <b>饮水</b>
                <i>{{ waterToday.total_amount }} / {{ waterToday.target_amount }} ml</i>
              </span>
            </button>
            <button class="act" @click="router.push('/exercise')">
              <span class="act-ico"><AppIcon name="fire" :size="18" /></span>
              <span class="act-txt"><b>运动</b><i>记录消耗</i></span>
            </button>
            <button class="act" @click="router.push('/stats')">
              <span class="act-ico"><AppIcon name="chart" :size="18" /></span>
              <span class="act-txt"><b>数据</b><i>看趋势</i></span>
            </button>
          </div>
          <div class="water-bar" v-if="waterToday.target_amount">
            <span class="wb-fill" :style="{ width: waterPercent + '%' }" />
          </div>
        </section>
      </div>
    </div>

    <!-- 数据统计（移动端并入首页；桌面端走侧栏独立页，避免信息重复堆叠） -->
    <section class="card home-stats">
      <div class="hs-head">
        <h3 class="m-title">趋势</h3>
        <button class="hs-link" @click="router.push('/stats')">完整报告 →</button>
      </div>
      <StatsPanel />
    </section>

    <!-- 记录体重 -->
    <van-popup v-model:show="showWeight" position="bottom" round>
      <div class="popup-wrap">
        <div class="popup-title">记录今日体重</div>
        <van-field v-model="weightInput" type="digit" label="体重" placeholder="kg" :border="false" />
        <van-button type="primary" block round @click="saveWeight">保存</van-button>
      </div>
    </van-popup>

    <!-- 饮水 -->
    <van-popup v-model:show="showWater" position="bottom" round>
      <div class="popup-wrap">
        <div class="popup-title">今日饮水</div>
        <div class="water-info">
          <span class="cur num">{{ waterToday.total_amount }}</span>
          <span class="target num">/ {{ waterToday.target_amount }} ml</span>
        </div>
        <van-progress :percentage="waterPercent" :show-pivot="false" class="v-bar" />
        <div class="water-btns">
          <button class="wbtn wbtn--solid" @click="submitWater(200)">+200ml</button>
          <button class="wbtn" @click="submitWater(500)">+500ml</button>
        </div>
      </div>
    </van-popup>

    <!-- 食谱详情 -->
    <van-popup v-model:show="showMeal" position="bottom" round>
      <div class="popup-wrap" v-if="currentMeal">
        <div class="popup-title">{{ MEAL_TYPE_MAP[currentMeal.type] }} · {{ currentMeal.item.name }}</div>
        <div class="meal-detail">
          <div class="detail-row"><span>重量</span><b class="num">{{ currentMeal.item.weight }} g</b></div>
          <div class="detail-row"><span>热量</span><b class="num">{{ currentMeal.item.calorie }} kcal</b></div>
          <div class="detail-row"><span>做法</span><b>{{ currentMeal.item.practice || '—' }}</b></div>
        </div>
      </div>
    </van-popup>

    <!-- 食物库快捷录入 -->
    <FoodPicker
      v-model="showPicker"
      :meal-type="pickerMealType"
      :initial-keyword="pickerKeyword"
      @added="onFoodAdded"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import CalorieCard from '@/components/CalorieCard.vue'
import StatsPanel from '@/components/StatsPanel.vue'
import FoodPicker from '@/components/FoodPicker.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import { useUserStore } from '@/store/modules/user'
import { todayDiet } from '@/api/diet'
import { getMetrics, getCheckin } from '@/api/auth'
import { searchFoods, frequentFoods } from '@/api/food'
import { energyTarget } from '@/api/energy'
import { generatePlan, getPlan } from '@/api/ai'
import { listWeight } from '@/api/weight'
import { addWater, todayWater } from '@/api/water'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { today, weekdayCN, formatDate, roundNum } from '@/utils/format'
import { MEAL_TYPE_MAP } from '@/utils/common'
import { on } from '@/utils/bus'

const router = useRouter()
const userStore = useUserStore()

const isMobile = ref(typeof window !== 'undefined' ? window.innerWidth < 1024 : true)
function syncViewport() {
  isMobile.value = window.innerWidth < 1024
}
const nickname = computed(() => userStore.userInfo?.username || '瘦友')

// 作息/血压式的问候：跟随真实时钟，不用假数据
const nowHour = new Date().getHours()
const greeting = computed(() => {
  if (nowHour < 6) return '夜深了'
  if (nowHour < 11) return '早上好'
  if (nowHour < 14) return '中午好'
  if (nowHour < 18) return '下午好'
  return '晚上好'
})
const todayCn = computed(() => {
  const d = new Date()
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日 · ${weekdayCN(today())}`
})

const todayData = reactive({
  total_calorie: 0,
  total_protein: 0,
  total_fat: 0,
  total_carbohydrate: 0,
  items: []
})
const recommend = ref(0)
const checkinDays = ref(0)
const latestWeight = ref(0)
const gapKg = ref(0)

// 三者口径必须一致：优先用能量引擎算出的目标摄入，其次才是静态推荐值
async function fetchMetrics() {
  try {
    const t = await energyTarget()
    recommend.value = Math.round(t?.target?.target_calorie || 0)
  } catch (e) {
    /* 能量引擎未就绪时退回静态指标 */
  }
  if (!recommend.value) {
    try {
      const res = await getMetrics()
      recommend.value = Math.round(res.recommend_calorie || 0)
    } catch (e) { /* 保持 0，页面显示占位 */ }
  }
}

const remaining = computed(() => Math.round(recommend.value - todayData.total_calorie))

// ---------------------------------------------------------------- 结论文案
// 「还能吃 660 kcal」是数字；用户真正能执行的是「660 kcal 大概等于什么」。
// 这里用食物库里的真实条目换算，不在前端二次维护一份营养数据。
const anchors = ref([])
async function loadAnchors() {
  try {
    const picked = await Promise.all(
      ['米饭', '鸡胸肉', '苹果', '牛奶'].map(async (kw) => {
        const res = await searchFoods({ keyword: kw, limit: 1 })
        const f = (res.items || [])[0]
        if (!f) return null
        return {
          name: f.name,
          label: f.default_portion_label,
          grams: f.default_portion_grams,
          kcal: Math.round((f.calorie * f.default_portion_grams) / 100)
        }
      })
    )
    anchors.value = picked.filter(Boolean)
  } catch (e) {
    anchors.value = []
  }
}

const remainingHint = computed(() => {
  const left = remaining.value
  if (!recommend.value) return '先完善身高体重资料，就能算出你的目标热量'
  if (left <= 0) {
    return `今天已超出 ${Math.abs(left)} kcal，别焦虑，明天自然会调整回来`
  }
  if (!anchors.value.length) return '从食物库里挑，选好份量就能记'

  // 贪心：先放能放下的最大份，再配一件小的，最多两件
  const fits = anchors.value.filter((a) => a.kcal > 0 && a.kcal <= left)
  if (!fits.length) return `还剩一点空间，加个零食前先看一眼热量`
  fits.sort((a, b) => b.kcal - a.kcal)
  const combo = [fits[0]]
  let rest = left - fits[0].kcal
  const second = anchors.value.find((a) => a !== fits[0] && a.kcal > 0 && a.kcal <= rest)
  if (second) combo.push(second)
  return `≈ ${combo.map((c) => c.label + c.name).join(' + ')}`
})

// ---------------------------------------------------------------- 三餐时间轴
const MEAL_INT = { breakfast: 1, lunch: 2, dinner: 3, snack: 4 }
const MEAL_ROWS = [
  { type: 1, label: '早餐', time: '建议 7:00–9:00' },
  { type: 2, label: '午餐', time: '建议 11:30–13:30' },
  { type: 3, label: '晚餐', time: '建议 18:00–20:00' },
  { type: 4, label: '加餐', time: '饿了就补一点' }
]

const timeline = computed(() =>
  MEAL_ROWS.map((row) => {
    const items = (todayData.items || []).filter((it) => it.meal_type === row.type)
    return {
      ...row,
      items,
      total: roundNum(items.reduce((s, x) => s + Number(x.calorie || 0), 0), 0)
    }
  })
)
const eatenMeals = computed(() => [1, 2, 3].filter((t) => timeline.value.find((x) => x.type === t)?.items.length).length)

// ---------------------------------------------------------------- 营养素
const nutri = computed(() => {
  const rec = recommend.value || 1500
  const targets = {
    protein: roundNum((rec * 0.25) / 4, 1),
    fat: roundNum((rec * 0.25) / 9, 1),
    carbohydrate: roundNum((rec * 0.5) / 4, 1)
  }
  const make = (key, label, color, cur) => {
    const target = targets[key] || 1
    const percent = Math.min(Math.round((Number(cur || 0) / target) * 100), 100)
    return { key, label, color, cur: roundNum(cur || 0, 1), target, percent }
  }
  return [
    make('protein', '蛋白质', 'var(--lime-ink)', todayData.total_protein),
    make('fat', '脂肪', 'var(--clay)', todayData.total_fat),
    make('carbohydrate', '碳水', 'var(--sky)', todayData.total_carbohydrate)
  ]
})

// ---------------------------------------------------------------- AI 食谱
const plan = reactive({ breakfast: [], lunch: [], dinner: [], total_calorie: 0, adapt_desc: '' })
const planLoading = ref(false)
const mealList = computed(() => [
  { type: 'breakfast', label: '早餐', items: plan.breakfast, total: sumCal(plan.breakfast) },
  { type: 'lunch', label: '午餐', items: plan.lunch, total: sumCal(plan.lunch) },
  { type: 'dinner', label: '晚餐', items: plan.dinner, total: sumCal(plan.dinner) }
])
function sumCal(arr) {
  return roundNum((arr || []).reduce((s, x) => s + Number(x.calorie || 0), 0), 0)
}
const hasPlan = computed(() => plan.breakfast.length || plan.lunch.length || plan.dinner.length)

async function fetchPlan() {
  planLoading.value = true
  try {
    const saved = await getPlan({ date: today() })
    if (saved && saved.plan) {
      applyPlan(saved.plan)
      return
    }
    const res = await generatePlan({ date: today() })
    applyPlan(res.plan)
  } catch (e) {
    /* 保持空态，页面提供「立即生成」入口 */
  } finally {
    planLoading.value = false
  }
}
function applyPlan(p) {
  plan.breakfast = p.breakfast || []
  plan.lunch = p.lunch || []
  plan.dinner = p.dinner || []
  plan.total_calorie = p.total_calorie || 0
  plan.adapt_desc = p.adapt_desc || ''
}
async function regeneratePlan() {
  showLoadingToast({ message: '正在搭配食谱…', forbidClick: true, duration: 0 })
  let ok = false
  try {
    const res = await generatePlan({ date: today() })
    applyPlan(res.plan)
    ok = true
  } catch (e) {
    ok = false
  } finally {
    closeToast()
  }
  showToast({ type: ok ? 'success' : 'fail', message: ok ? '已更新食谱' : '生成失败，请稍后重试' })
}

// ---------------------------------------------------------------- 录入
const showPicker = ref(false)
const pickerMealType = ref(0)
const pickerKeyword = ref('')

function autoMealType() {
  const h = new Date().getHours()
  if (h < 10) return 1
  if (h < 15) return 2
  if (h < 21) return 3
  return 4
}
function openPicker(mealType) {
  pickerMealType.value = mealType || autoMealType()
  pickerKeyword.value = ''
  showPicker.value = true
}
function onFoodAdded() {
  fetchToday()
  fetchCheckin()
}

// ⌘K 选中食物后跳转过来选份量
let offBus = null
onMounted(() => {
  offBus = on('foodpicker:open', (payload = {}) => {
    pickerMealType.value = payload.mealType || autoMealType()
    pickerKeyword.value = payload.keyword || ''
    showPicker.value = true
  })
})
onBeforeUnmount(() => offBus && offBus())

const showWeight = ref(false)
const weightInput = ref('')
async function saveWeight() {
  if (!weightInput.value) return showToast('请输入体重')
  try {
    await addWeight({ record_date: today(), weight: Number(weightInput.value) })
    showToast({ type: 'success', message: '已记录' })
    showWeight.value = false
    fetchLatestWeight()
    fetchCheckin()
  } catch (e) { /* 统一错误提示已在拦截器处理 */ }
}

const showWater = ref(false)
const waterToday = reactive({ total_amount: 0, target_amount: 2000, date: '' })
const waterPercent = computed(() =>
  waterToday.target_amount
    ? Math.min(Math.round((waterToday.total_amount / waterToday.target_amount) * 100), 100)
    : 0
)
async function openWater() {
  showWater.value = true
  try {
    Object.assign(waterToday, await todayWater({ date: today() }))
  } catch (e) { /* 静默：保持上一次数值 */ }
}
async function submitWater(amount) {
  try {
    const res = await addWater({ record_date: today(), amount })
    waterToday.total_amount = res.total_amount
    waterToday.target_amount = res.target_amount
    showToast({ type: 'success', message: '已添加 ' + amount + 'ml' })
  } catch (e) { /* 同上 */ }
}

// ---------------------------------------------------------------- 数据
async function fetchToday() {
  try {
    const res = await todayDiet({ date: today() })
    Object.assign(todayData, res)
  } catch (e) { /* 首页允许降级为 0，不阻塞其它模块 */ }
}

async function fetchLatestWeight() {
  try {
    // 取近一周：今天没称重时至少还能显示最近一次，避免「今天还没记」造成误导
    const res = await listWeight({ type: 'week' })
    const rows = res.records || []
    latestWeight.value = rows.length ? Number(rows[0].weight) : 0
    const target = Number(userStore.userInfo?.target_weight || 0)
    if (latestWeight.value && target) gapKg.value = roundNum(latestWeight.value - target, 1)
  } catch (e) { /* 体重不是首屏关键数据 */ }
}

async function fetchCheckin() {
  try {
    const res = await getCheckin()
    checkinDays.value = Number(res?.continuous_days) || 0
  } catch (e) {
    checkinDays.value = 0
  }
}

const ringSize = computed(() => (isMobile.value ? 150 : 176))

onMounted(() => {
  syncViewport()
  window.addEventListener('resize', syncViewport)
  fetchToday()
  fetchMetrics()
  loadAnchors()
  fetchPlan()
  fetchCheckin()
  fetchLatestWeight()
  // 桌面不需要多余的等待：先把常用食物拉出来备用
  if (!isMobile.value) frequentFoods({ limit: 8 }).catch(() => {})
})
onBeforeUnmount(() => window.removeEventListener('resize', syncViewport))

watch(
  () => todayData.total_calorie,
  () => fetchCheckin()
)
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.page.home {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.m-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-1);
  margin: 0 0 14px;
}

// ---------- Hero ----------
.hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 2px 2px 0;

  .hero-greet {
    font-size: 27px;
    font-weight: 700;
    line-height: 1.15;
    margin: 8px 0 4px;
    letter-spacing: -0.01em;
  }
  .hero-sub {
    margin: 0;
    font-size: 13px;
    color: var(--text-3);

    b {
      color: var(--text-2);
      font-weight: 700;
    }
  }
}

.hero-cta {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 42px;
  padding: 0 18px;
  border: none;
  border-radius: 999px;
  background: var(--lime);
  color: var(--on-lime);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  flex-shrink: 0;
  transition: transform @dur-fast @ease-out, filter @dur-fast @ease-out;

  &:hover {
    filter: brightness(1.05);
  }
  &:active {
    transform: scale(0.97);
  }
  kbd {
    font-family: @font-body;
    font-size: 11px;
    background: rgba(35, 35, 31, 0.12);
    border-radius: 5px;
    padding: 1px 5px;
  }
}

// ---------- 栅格 ----------
.home-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  align-items: start;
}
.col {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

// ---------- 结论卡 ----------
.verdict {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 22px;

  .v-text {
    flex: 1;
    min-width: 0;
  }
  .v-title {
    margin: 0;
    font-size: 19px;
    font-weight: 600;
    line-height: 1.4;
    color: var(--text-1);

    .num {
      font-size: 34px;
      font-weight: 800;
      color: var(--lime-ink);
      margin: 0 4px;
      letter-spacing: -0.02em;

      &.over {
        color: var(--red);
      }
    }
    .v-unit {
      font-size: 13px;
      font-weight: 500;
      color: var(--text-3);
    }
  }
  .v-hint {
    margin: 6px 0 14px;
    font-size: 13px;
    color: var(--text-2);
    line-height: 1.6;
  }
  .v-nums {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;

    div {
      span {
        display: block;
        font-size: 11.5px;
        color: var(--text-3);
      }
      b {
        font-size: 17px;
        font-weight: 700;
        color: var(--text-1);
      }
      i {
        font-style: normal;
        font-size: 11px;
        color: var(--text-3);
        margin-left: 2px;
      }
    }
  }
}

// ---------- 三餐时间轴 ----------
.tl-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 4px;

  .tl-note {
    font-size: 12px;
    color: var(--text-3);
    margin-bottom: 14px;
  }
}

.tl {
  position: relative;
}

.tl-row {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid var(--border);

  &:first-child {
    border-top: none;
  }
}

.tl-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  background: var(--surface-2);
  border: 2px solid var(--border-2);
  transition: background @dur @ease-out, border-color @dur @ease-out;

  &.done {
    background: var(--lime);
    border-color: var(--lime);
  }
}

.tl-body {
  flex: 1;
  min-width: 0;
}

.tl-top {
  display: flex;
  align-items: center;
  gap: 8px;

  .tl-name {
    font-size: 14.5px;
    font-weight: 600;
    color: var(--text-1);
  }
  .tl-time {
    font-size: 11.5px;
    color: var(--text-3);
    flex: 1;
    min-width: 0;
  }
  .tl-cal {
    font-size: 12.5px;
    font-weight: 700;
    color: var(--text-2);
  }
}

.tl-add {
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-2);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
  font-family: @font-body;
  transition: all @dur-fast @ease-out;

  &:hover {
    background: var(--lime-soft);
    border-color: transparent;
    color: var(--lime-ink);
    font-weight: 600;
  }
}

.tl-items {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;

  li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 4px 0;
  }
  .ti-name {
    flex: 1;
    min-width: 0;
    font-size: 13px;
    color: var(--text-2);
  }
  .ti-cal {
    font-size: 12.5px;
    color: var(--text-3);
    flex-shrink: 0;
  }
}

.tl-empty {
  margin: 6px 0 0;
  font-size: 12.5px;
  color: var(--text-3);
}

// ---------- 营养素 ----------
.macro + .macro {
  margin-top: 13px;
}
.m-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 6px;

  .m-label {
    font-size: 12.5px;
    color: var(--text-2);
  }
  .m-val {
    font-size: 12.5px;
    color: var(--text-1);
    font-weight: 600;

    i {
      color: var(--text-3);
      font-style: normal;
      font-weight: 400;
    }
  }
}
.m-track {
  height: 7px;
  border-radius: 999px;
  background: var(--surface-2);
  overflow: hidden;
}
.m-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  transition: width @dur-slow @ease-out;
}

// ---------- 食谱 ----------
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  .m-title {
    margin-bottom: 0;
  }
}

.ghost {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-2);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 5px 11px;
  cursor: pointer;
  font-family: @font-body;
  transition: color @dur-fast @ease-out, background @dur-fast @ease-out;

  &:hover {
    color: var(--lime-ink);
    background: var(--lime-soft);
  }
}

.plan-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 0;
  color: var(--text-3);
  font-size: 13px;
}

.plan-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 22px 16px 16px;

  .pe-ico {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--lime-soft);
    color: var(--lime-ink);
    margin-bottom: 12px;
  }
  .pe-title {
    margin: 0;
    font-size: 14.5px;
    font-weight: 600;
    color: var(--text-1);
  }
  .pe-sub {
    margin: 6px 0 16px;
    font-size: 12.5px;
    color: var(--text-3);
    max-width: 260px;
    line-height: 1.6;
  }
  .pe-btn {
    border: none;
    background: var(--lime);
    color: var(--on-lime);
    border-radius: @r-md;
    padding: 10px 26px;
    font-size: 13.5px;
    font-weight: 700;
    cursor: pointer;

    &:hover {
      filter: brightness(1.05);
    }
  }
}

.meal {
  padding: 12px 0;
  border-bottom: 1px solid var(--border);

  &:last-of-type {
    border-bottom: none;
  }
}
.meal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;

  .meal-name {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-1);

    .m-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;

      &.breakfast { background: var(--clay); }
      &.lunch { background: var(--lime); }
      &.dinner { background: var(--sky); }
    }
  }
  .meal-cal {
    font-size: 12.5px;
    color: var(--text-2);
    font-weight: 600;
  }
}
.meal-items {
  display: flex;
  flex-direction: column;
}
.meal-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 6px 8px;
  border: none;
  background: transparent;
  border-radius: @r-sm;
  cursor: pointer;
  text-align: left;

  &:hover {
    background: var(--hover);
  }
  .it-name {
    font-size: 13.5px;
    color: var(--text-2);
    flex: 1;
    min-width: 0;
  }
  .it-cal {
    font-size: 12.5px;
    color: var(--text-3);
  }
}
.meal-empty {
  font-size: 12.5px;
  color: var(--text-3);
  padding: 4px 8px;
}
.meal-add {
  margin-top: 6px;
  border: 1px dashed var(--border-2);
  background: transparent;
  color: var(--text-2);
  border-radius: @r-sm;
  padding: 6px 10px;
  font-size: 12.5px;
  cursor: pointer;
  width: 100%;
  font-family: @font-body;

  &:hover {
    background: var(--lime-soft);
    border-style: solid;
    border-color: transparent;
    color: var(--lime-ink);
  }
}

.adapt {
  margin-top: 14px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 14px;
  border-radius: @r-md;
  background: var(--lime-soft);
  color: var(--lime-ink);
  font-size: 13px;
  line-height: 1.6;
}

// ---------- 快捷操作 ----------
.act-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.act {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border: 1px solid var(--border);
  border-radius: @r-md;
  background: var(--surface-2);
  cursor: pointer;
  text-align: left;
  transition: background @dur-fast @ease-out, border-color @dur-fast @ease-out,
    transform @dur-fast @ease-out;

  &:hover {
    transform: translateY(-2px);
    border-color: var(--border-2);
    background: var(--hover);
  }
  .act-ico {
    width: 34px;
    height: 34px;
    border-radius: 10px;
    background: var(--surface);
    color: var(--lime-ink);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .act-txt {
    min-width: 0;

    b {
      display: block;
      font-size: 13.5px;
      color: var(--text-1);
      font-weight: 600;
    }
    i {
      display: block;
      font-style: normal;
      font-size: 11.5px;
      color: var(--text-3);
    }
  }
}

.water-bar {
  margin-top: 12px;
  height: 6px;
  border-radius: 999px;
  background: var(--surface-2);
  overflow: hidden;

  .wb-fill {
    display: block;
    height: 100%;
    border-radius: 999px;
    background: var(--sky);
    transition: width @dur-slow @ease-out;
  }
}

// ---------- 弹窗 ----------
.popup-wrap {
  padding: 22px 20px calc(22px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  gap: 14px;

  .popup-title {
    font-size: 16.5px;
    font-weight: 700;
    text-align: center;
  }
}
.water-info {
  text-align: center;

  .cur {
    font-size: 30px;
    font-weight: 800;
    color: var(--sky);
  }
  .target {
    font-size: 14px;
    color: var(--text-3);
  }
}
.water-btns {
  display: flex;
  gap: 12px;
}
.wbtn {
  flex: 1;
  height: 42px;
  border-radius: @r-md;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-1);
  font-size: 13.5px;
  cursor: pointer;

  &--solid {
    background: var(--lime);
    border-color: transparent;
    color: var(--on-lime);
    font-weight: 700;
  }
}
.meal-detail .detail-row {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  font-size: 14px;

  span {
    color: var(--text-3);
  }
  b {
    color: var(--text-1);
  }
}

.v-bar :deep(.van-progress__portion) {
  background: var(--sky);
}

// ---------- 首页统计（仅移动端） ----------
.home-stats {
  .hs-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .hs-link {
    border: none;
    background: transparent;
    padding: 0;
    font-family: @font-body;
    font-size: 12.5px;
    color: var(--lime-ink);
    cursor: pointer;
    margin-bottom: 14px;
  }
  :deep(.chart-card .chart-line),
  :deep(.chart-card .chart-pie) {
    height: 240px !important;
  }
}

// ---------- 响应式 ----------
@media (min-width: 1024px) {
  .home-grid {
    grid-template-columns: 1.08fr 1fr;
  }
  .home-stats {
    display: none;
  }
  .verdict {
    padding: 26px;
  }
}

@media (max-width: 560px) {
  .hero {
    align-items: center;
  }
  .hero-greet {
    font-size: 22px;
  }
  .verdict {
    flex-direction: column;
    align-items: stretch;
    text-align: left;

    .v-title .num {
      font-size: 30px;
    }
  }
  .act-grid {
    grid-template-columns: 1fr;
  }
  .tl-time {
    display: none;
  }
}
</style>
