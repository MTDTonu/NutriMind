<template>
  <div class="stats-panel">
    <div class="sp-top">
      <p class="sp-lead">别只看图表，重点是这段时间的判断。</p>
      <button class="sp-export" :disabled="exporting" @click="doExport">
        <AppIcon name="display" :size="15" />
        {{ exporting ? '生成中…' : '导出近 30 天 CSV' }}
      </button>
    </div>

    <van-tabs v-model:active="active" class="stats-tabs">
      <van-tab title="体重趋势">
        <div class="tab-body">
          <div class="seg">
            <van-radio-group v-model="range" direction="horizontal">
              <van-radio name="day">日</van-radio>
              <van-radio name="week">周</van-radio>
              <van-radio name="month">月</van-radio>
            </van-radio-group>
          </div>

          <div class="conclusion">
            <AppIcon name="chart" :size="16" />
            <span>{{ weightConclusion }}</span>
          </div>

          <div class="tiles">
            <div class="tile"><span>初始</span><b class="num">{{ weightStat.initial }}</b><i>kg</i></div>
            <div class="tile"><span>当前</span><b class="num">{{ weightStat.current }}</b><i>kg</i></div>
            <div class="tile good"><span>累计减重</span><b class="num">{{ weightStat.lost }}</b><i>kg</i></div>
            <div class="tile"><span>目标</span><b class="num">{{ weightStat.target }}</b><i>kg</i></div>
          </div>

          <div class="card card--edge chart-card">
            <div class="eyebrow">体重变化曲线</div>
            <div v-if="weightEmpty" class="chart-empty">
              <AppIcon name="chart" :size="26" />
              <p>暂无体重记录</p>
              <span>记录体重后即可查看变化趋势</span>
            </div>
            <ChartLine v-else :option="weightOption" height="320px" />
          </div>
        </div>
      </van-tab>

      <van-tab title="营养分析">
        <div class="tab-body">
          <div class="conclusion">
            <AppIcon name="fire" :size="16" />
            <span>{{ macroConclusion }}</span>
          </div>

          <div class="grid-3">
            <div class="card card--edge chart-card">
              <div class="eyebrow">近 7 日热量摄入</div>
              <div v-if="calorieEmpty" class="chart-empty">
                <AppIcon name="chart" :size="26" />
                <p>暂无摄入数据</p>
                <span>记录饮食后即可查看</span>
              </div>
              <ChartLine
                v-else
                :option="calorieOption"
                height="280px"
                pickable
                @pick="onPickDay"
              />
            </div>
            <div class="card card--edge chart-card">
              <div class="eyebrow">三大营养素供能比</div>
              <div v-if="calorieEmpty" class="chart-empty">
                <AppIcon name="chart" :size="26" />
                <p>暂无营养数据</p>
                <span>记录饮食后即可查看</span>
              </div>
              <ChartPie v-else :option="nutriPieOption" height="280px" />
            </div>
            <div class="card card--edge chart-card">
              <div class="eyebrow">每日营养素克数</div>
              <div v-if="calorieEmpty" class="chart-empty">
                <AppIcon name="chart" :size="26" />
                <p>暂无营养数据</p>
                <span>记录饮食后即可查看</span>
              </div>
              <ChartLine v-else :option="macroOption" height="280px" />
            </div>
          </div>

          <!-- 桌面端明细表：图表点选某天即筛选该天，表头可排序 -->
          <div v-if="!isMobile" class="card card--edge detail-card">
            <div class="dc-head">
              <div class="eyebrow">每日明细</div>
              <div class="dc-tools">
                <span v-if="pickedDay" class="dc-picked">
                  已选 {{ pickedDay }}
                  <button class="dc-clear" aria-label="清除筛选" @click="pickedDay = ''">清除</button>
                </span>
                <span v-else class="dc-hint">点击上方图表中的某一天可只看那天</span>
              </div>
            </div>

            <div class="dc-scroll">
              <table class="dc-table">
                <thead>
                  <tr>
                    <th
                      v-for="col in detailCols"
                      :key="col.key"
                      :class="{ sortable: true, on: sortKey === col.key, num: col.num }"
                      @click="toggleSort(col.key)"
                    >
                      {{ col.label }}
                      <span class="dc-arrow">{{ sortKey === col.key ? (sortAsc ? '↑' : '↓') : '↕' }}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in detailRows"
                    :key="row.date"
                    :class="{ picked: pickedDay === row.date, over: row.diff > 0 }"
                    @click="pickedDay = pickedDay === row.date ? '' : row.date"
                  >
                    <td>{{ row.date.slice(5) }}</td>
                    <td class="num">{{ row.calorie }}</td>
                    <td class="num">{{ row.protein }}</td>
                    <td class="num">{{ row.fat }}</td>
                    <td class="num">{{ row.carbohydrate }}</td>
                    <td class="num" :class="{ up: row.diff > 0, down: row.diff < 0 }">
                      {{ row.diff == null ? '—' : (row.diff > 0 ? '+' + row.diff : row.diff) }}
                    </td>
                  </tr>
                  <tr v-if="!detailRows.length">
                    <td :colspan="detailCols.length" class="dc-empty">暂无明细数据</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <p class="dc-foot">{{ detailConclusion }}</p>
          </div>
        </div>
      </van-tab>

      <van-tab title="周度报告">
        <div class="tab-body">
          <div class="tiles">
            <div class="tile"><span>平均体重</span><b class="num">{{ weekly.avg_weight }}</b><i>kg</i></div>
            <div class="tile good"><span>平均缺口</span><b class="num">{{ weekly.avg_deficit }}</b><i>kcal</i></div>
            <div class="tile good"><span>达标率</span><b class="num">{{ weekly.goal_rate }}</b><i>%</i></div>
          </div>

          <div class="card card--edge chart-card">
            <div class="eyebrow">本周摄入 vs 消耗</div>
            <div v-if="weeklyEmpty" class="chart-empty">
              <AppIcon name="chart" :size="26" />
              <p>本周暂无数据</p>
              <span>记录饮食与运动后即可查看</span>
            </div>
            <ChartLine v-else :option="weeklyOption" height="280px" />
          </div>

          <div class="card card--edge report-summary">
            <AppIcon name="bolt" :size="18" />
            <p>{{ weekly.summary || '保持节奏，本周表现不错，继续坚持即可达成目标。' }}</p>
          </div>
        </div>
      </van-tab>
    </van-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, computed } from 'vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import ChartLine from '@/components/ChartLine.vue'
import ChartPie from '@/components/ChartPie.vue'
import { weightTrend, nutrientTrend, weeklyStats } from '@/api/stats'
import { exportData } from '@/api/data'
import { energyTarget } from '@/api/energy'
import { isMobileRef } from '@/utils/breakpoint'

// 统计面板：独立「数据统计」页与首页移动端区块共用，
// 数据全部来自后端统计接口，不做本地伪造。
const active = ref(0)
const range = ref('week')

// 图表配色跟随「温润生机」主题：暖灰轴 + 橄榄/陶土/天蓝三种可读色。
// 不用纯青柠做细线——在暖白底上对比度不足，青柠留给面积与命中态。
const AXIS = '#8a8578'
const SPLIT = 'rgba(138,133,120,0.18)'
const MAIN = '#6e9433' // 橄榄
const CLAY = '#c97a45' // 陶土
const SKY = '#4a8fa8' // 天蓝
const LIME = MAIN
const ORANGE = CLAY
const CYAN = SKY

const weightStat = reactive({ initial: '—', current: '—', lost: '—', target: '—' })
const weightOption = ref({})
const calorieOption = ref({})
const nutriPieOption = ref({})
const weeklyOption = ref({})
const weekly = reactive({ avg_weight: '—', avg_deficit: '—', goal_rate: '—', summary: '' })

const weightEmpty = ref(true)
const calorieEmpty = ref(true)
const weeklyEmpty = ref(true)

// 结论计算所需的原始序列（图表之外的第二手数据，用于生成可执行文案）
const weightMeta = reactive({ points: 0, target: null })
const macroOption = ref({})
const exporting = ref(false)

// 体重结论：不给裸露数字，给「按这个速度什么时候到」的判断
const weightConclusion = computed(() => {
  const i = Number(weightStat.initial)
  const c = Number(weightStat.current)
  const t = Number(weightStat.target)
  if (!i || !c) return '先记录两三次体重，这里会给出你的实际下降速度。'
  const lost = i - c
  const weeks = Math.max(weightMeta.points / 7, 0.01)
  const perWeek = lost / weeks
  if (Math.abs(lost) < 0.05) return '这段时间体重基本持平，平台期很正常，先别急着加大缺口。'
  if (lost > 0) {
    const remain = t ? Math.max(c - t, 0) : 0
    const days = perWeek > 0 ? Math.ceil((remain / perWeek) * 7) : 0
    const tail = remain > 0 && days > 0 ? `照此速度还需约 ${days} 天到达目标。` : '已达成目标体重。'
    return `这段时间下降 ${lost.toFixed(1)} kg，平均每周 ${perWeek.toFixed(2)} kg。${tail}`
  }
  return `这段时间上升 ${Math.abs(lost).toFixed(1)} kg，平均每周 ${Math.abs(perWeek).toFixed(2)} kg，建议先复盘晚餐与加餐。`
})

// 营养结论：把「吃了多少」翻译成「够不够」
const macroConclusion = computed(() => {
  if (!nutrientRaw.dates.length) return '记录三餐后，这里会告诉你蛋白质是否吃够。'
  return `近 7 天平均每日蛋白 ${macroAvg.value.protein} g / 脂肪 ${macroAvg.value.fat} g / 碳水 ${macroAvg.value.carbohydrate} g。`
})

const macroAvg = computed(() => {
  const d = nutrientRaw.dates.length || 1
  const sum = (arr) => arr.reduce((a, b) => a + Number(b || 0), 0)
  return {
    protein: Math.round(sum(nutrientRaw.protein) / d),
    fat: Math.round(sum(nutrientRaw.fat) / d),
    carbohydrate: Math.round(sum(nutrientRaw.carbohydrate) / d)
  }
})

const nutrientRaw = reactive({ dates: [], protein: [], fat: [], carbohydrate: [], calorie: [] })

/* ---------------- 桌面端：每日明细表 + 图表交叉筛选 ----------------
 * 图表给「形状」，表格给「可核对的数字」。点图上的某一天即只看那一天，
 * 点表头可按该列排序——这是桌面端比移动端多出来的那部分信息密度。 */
const isMobile = isMobileRef
const targetKcal = ref(0)
const pickedDay = ref('')
const sortKey = ref('date')
const sortAsc = ref(false)

const detailCols = [
  { key: 'date', label: '日期' },
  { key: 'calorie', label: '热量 kcal', num: true },
  { key: 'protein', label: '蛋白 g', num: true },
  { key: 'fat', label: '脂肪 g', num: true },
  { key: 'carbohydrate', label: '碳水 g', num: true },
  { key: 'diff', label: '与目标差', num: true }
]

const detailAll = computed(() =>
  nutrientRaw.dates.map((date, i) => {
    const calorie = Math.round(Number(nutrientRaw.calorie[i] || 0))
    return {
      date,
      calorie,
      protein: Math.round(Number(nutrientRaw.protein[i] || 0)),
      fat: Math.round(Number(nutrientRaw.fat[i] || 0)),
      carbohydrate: Math.round(Number(nutrientRaw.carbohydrate[i] || 0)),
      diff: targetKcal.value ? calorie - Math.round(targetKcal.value) : null
    }
  })
)

const detailRows = computed(() => {
  const rows = pickedDay.value
    ? detailAll.value.filter((r) => r.date === pickedDay.value)
    : detailAll.value.slice()
  const k = sortKey.value
  rows.sort((a, b) => {
    const va = a[k]
    const vb = b[k]
    if (va == null) return 1
    if (vb == null) return -1
    const cmp = k === 'date' ? String(va).localeCompare(String(vb)) : Number(va) - Number(vb)
    return sortAsc.value ? cmp : -cmp
  })
  return rows
})

function toggleSort(key) {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value
  } else {
    sortKey.value = key
    // 数值列默认从大到小（先看最多的那天），日期列默认从新到旧
    sortAsc.value = key === 'date' ? false : false
  }
}

function onPickDay(day) {
  // 图上类目是 YYYY-MM-DD，与明细行的 date 一致；再点一次同一天则取消筛选
  pickedDay.value = pickedDay.value === day ? '' : day
}

// 明细表结论：把表格里最值得注意的那一天点出来
const detailConclusion = computed(() => {
  const rows = detailAll.value.filter((r) => r.calorie > 0)
  if (!rows.length) return '记录三餐后，这里可以逐天核对热量与营养素。'
  const over = rows.filter((r) => r.diff != null && r.diff > 0)
  const worst = over.slice().sort((a, b) => b.diff - a.diff)[0]
  const avg = Math.round(rows.reduce((a, b) => a + b.calorie, 0) / rows.length)
  if (!worst) {
    return `这 ${rows.length} 天平均每日 ${avg} kcal，全部控制在目标内，节奏很稳。`
  }
  return `这 ${rows.length} 天平均每日 ${avg} kcal，其中 ${over.length} 天超出目标；超得最多的是 ${worst.date.slice(5)}（+${worst.diff} kcal）。`
})

async function loadTarget() {
  try {
    const res = await energyTarget()
    targetKcal.value = Number(res?.target?.target_calorie || res?.target_calorie || 0)
  } catch (e) {
    targetKcal.value = 0
  }
}

async function doExport() {
  if (exporting.value) return
  exporting.value = true
  try {
    const blob = await exportData({ days: 30, format: 'csv' })
    const url = window.URL.createObjectURL(new Blob([blob]))
    const a = document.createElement('a')
    a.href = url
    a.download = `nutrimind-export-${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    exporting.value = false
  }
}

// scaleY：不强制从 0 起标。体重这种「变化只有零点几公斤」的曲线必须开，
// 否则 0~80 的坐标轴会把整条线压成一条直线，图表与结论自相矛盾。
// 开了之后要手动把目标线算进值域，否则 markLine 会被裁到轴外。
function lineOption({ dates, series, markLineVal, area, scaleY }) {
  let yRange = {}
  if (scaleY) {
    const vals = series
      .reduce((acc, s) => acc.concat(s.data || []), [])
      .filter((v) => v != null)
      .map(Number)
    if (markLineVal != null) vals.push(Number(markLineVal))
    if (vals.length) {
      const lo = Math.min(...vals)
      const hi = Math.max(...vals)
      const pad = Math.max((hi - lo) * 0.18, 0.4)
      yRange = {
        min: Math.floor((lo - pad) * 10) / 10,
        max: Math.ceil((hi + pad) * 10) / 10
      }
    }
  }
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: '12%', right: '4%', top: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: AXIS } },
      axisLabel: { color: AXIS, fontSize: 10 },
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      ...yRange,
      axisLabel: { color: AXIS, fontSize: 10 },
      splitLine: { lineStyle: { color: SPLIT } }
    },
    series: series.map((s, i) => ({
      name: s.name,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      data: s.data,
      itemStyle: { color: s.color },
      lineStyle: { color: s.color, width: 2 },
      areaStyle: area
        ? { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: s.color + '55' }, { offset: 1, color: s.color + '05' }] } }
        : undefined,
      // 目标线挂在第一条折线上（此前判断的是未传入的 s.markLine，导致目标线从未渲染）
      markLine:
        markLineVal != null && i === 0
          ? {
              silent: true,
              symbol: 'none',
              lineStyle: { color: ORANGE, type: 'dashed' },
              data: [{ yAxis: markLineVal }],
              label: { formatter: '目标 ' + markLineVal, color: ORANGE, fontSize: 10 }
            }
          : undefined
    }))
  }
}

async function loadWeight() {
  try {
    const res = await weightTrend({ range: range.value })
    const dates = res.dates || []
    const weights = res.weights || []
    weightOption.value = lineOption({
      dates,
      series: [{ name: '体重', data: weights, color: LIME }],
      markLineVal: res.target_weight,
      area: true,
      scaleY: true
    })
    const nums = weights.filter((w) => w != null).map(Number)
    weightMeta.points = dates.length
    weightMeta.target = res.target_weight != null ? Number(res.target_weight) : null
    weightEmpty.value = nums.length === 0
    weightStat.initial = nums.length ? nums[0] : '—'
    weightStat.current = nums.length ? nums[nums.length - 1] : '—'
    weightStat.lost =
      nums.length >= 2 ? (Number(nums[0]) - Number(nums[nums.length - 1])).toFixed(1) : '—'
    weightStat.target = res.target_weight != null ? res.target_weight : '—'
  } catch (e) {
    weightOption.value = lineOption({ dates: [], series: [{ name: '体重', data: [], color: LIME }] })
  }
}

async function loadNutrient() {
  try {
    const res = await nutrientTrend({ days: 7 })
    const dates = res.dates || []
    calorieOption.value = lineOption({
      dates,
      series: [{ name: '热量', data: res.calorie || [], color: ORANGE }],
      area: true
    })
    // 供能比：蛋白*4 / 脂肪*9 / 碳水*4
    const ps = (res.protein || []).reduce((a, b) => a + Number(b || 0), 0)
    const fs = (res.fat || []).reduce((a, b) => a + Number(b || 0), 0)
    const cs = (res.carbohydrate || []).reduce((a, b) => a + Number(b || 0), 0)
    const pe = ps * 4
    const fe = fs * 9
    const ce = cs * 4
    calorieEmpty.value = pe + fe + ce === 0
    nutrientRaw.dates = dates
    nutrientRaw.protein = res.protein || []
    nutrientRaw.fat = res.fat || []
    nutrientRaw.carbohydrate = res.carbohydrate || []
    nutrientRaw.calorie = res.calorie || []
    macroOption.value = {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: { data: ['蛋白质', '脂肪', '碳水'], top: 0, textStyle: { color: AXIS } },
      grid: { left: '12%', right: '4%', top: 40, bottom: 30 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: AXIS } },
        axisLabel: { color: AXIS, fontSize: 10 }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: AXIS, fontSize: 10 },
        splitLine: { lineStyle: { color: SPLIT } }
      },
      series: [
        { name: '蛋白质', type: 'bar', stack: 'macro', data: res.protein || [], itemStyle: { color: MAIN } },
        { name: '脂肪', type: 'bar', stack: 'macro', data: res.fat || [], itemStyle: { color: CLAY } },
        { name: '碳水', type: 'bar', stack: 'macro', data: res.carbohydrate || [], itemStyle: { color: SKY } }
      ]
    }
    nutriPieOption.value = {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item', formatter: '{b}: {c} kcal ({d}%)' },
      legend: { bottom: 0, textStyle: { color: AXIS } },
      series: [
        {
          type: 'pie',
          radius: ['42%', '66%'],
          center: ['50%', '45%'],
          label: { color: AXIS, formatter: '{b}\n{d}%' },
          data: [
            { name: '蛋白质', value: Math.round(pe), itemStyle: { color: LIME } },
            { name: '脂肪', value: Math.round(fe), itemStyle: { color: ORANGE } },
            { name: '碳水', value: Math.round(ce), itemStyle: { color: CYAN } }
          ]
        }
      ]
    }
  } catch (e) {
    calorieOption.value = lineOption({ dates: [], series: [{ name: '热量', data: [], color: ORANGE }] })
  }
}

async function loadWeekly() {
  try {
    const res = await weeklyStats()
    weekly.avg_weight = res.avg_weight != null ? res.avg_weight : '—'
    weekly.avg_deficit = res.avg_deficit != null ? res.avg_deficit : '—'
    weekly.goal_rate = res.goal_rate != null ? res.goal_rate : '—'
    weekly.summary = res.summary || ''
    weeklyEmpty.value = ![...(res.intake || []), ...(res.burned || [])].some(
      (v) => Number(v) > 0
    )
    weeklyOption.value = {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: { data: ['摄入', '消耗'], top: 0, textStyle: { color: AXIS } },
      grid: { left: '12%', right: '4%', top: 40, bottom: 30 },
      xAxis: {
        type: 'category',
        data: res.days || [],
        axisLine: { lineStyle: { color: AXIS } },
        axisLabel: { color: AXIS, fontSize: 10 }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: AXIS, fontSize: 10 },
        splitLine: { lineStyle: { color: SPLIT } }
      },
      series: [
        {
          name: '摄入',
          type: 'bar',
          data: res.intake || [],
          itemStyle: { color: ORANGE, borderRadius: [4, 4, 0, 0] }
        },
        {
          name: '消耗',
          type: 'bar',
          data: res.burned || [],
          itemStyle: { color: LIME, borderRadius: [4, 4, 0, 0] }
        }
      ]
    }
  } catch (e) {
    weekly.summary = '暂无周报数据，坚持记录后我会为你生成专属总结。'
  }
}

watch(range, loadWeight)

onMounted(() => {
  loadWeight()
  loadNutrient()
  loadWeekly()
  loadTarget()
})
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.stats-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

// 顶部引导 + 导出
.sp-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.sp-lead {
  margin: 0;
  font-size: 13px;
  color: var(--text-3);
}

.sp-export {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-2);
  font-size: 12.5px;
  cursor: pointer;
  transition: all @dur-fast @ease-out;

  &:hover {
    border-color: var(--lime-ink);
    color: var(--text-1);
    background: var(--hover);
  }
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

/* ---------------- 桌面端：每日明细表 ---------------- */
.detail-card {
  padding: 16px 18px 14px;
}

.dc-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.dc-tools {
  font-size: 12px;
  color: var(--text-3);
}

.dc-picked {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 3px 4px 3px 10px;
  border-radius: 999px;
  background: var(--olive-soft);
  color: var(--lime-ink);
  font-weight: 600;

  .dc-clear {
    border: none;
    background: transparent;
    color: inherit;
    font-size: 11.5px;
    cursor: pointer;
    padding: 1px 6px;
    border-radius: 999px;

    &:hover {
      background: var(--hover);
    }
  }
}

.dc-scroll {
  overflow-x: auto;
}

.dc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th,
  td {
    padding: 9px 12px;
    text-align: left;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  th {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-3);
    background: var(--surface-2);
    position: sticky;
    top: 0;

    &.sortable {
      cursor: pointer;
      user-select: none;
      transition: color @dur-fast @ease-out;

      &:hover {
        color: var(--text-1);
      }
      &.on {
        color: var(--lime-ink);
      }
    }
    .dc-arrow {
      margin-left: 4px;
      opacity: 0.55;
      font-size: 10px;
    }
  }
  td.num,
  th.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  tbody tr {
    cursor: pointer;
    transition: background @dur-fast @ease-out;

    &:hover {
      background: var(--hover);
    }
    &.picked {
      background: var(--olive-soft);
    }
    &.over td:last-child {
      font-weight: 600;
    }
  }
  .up {
    color: var(--red);
  }
  .down {
    color: var(--lime-ink);
  }
  .dc-empty {
    text-align: center;
    color: var(--text-3);
    padding: 20px 0;
  }
}

.dc-foot {
  margin: 10px 0 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text-2);
}

// 结论条：先给判断，再给图表
.conclusion {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 13px 15px;
  border-radius: @r-md;
  background: var(--olive-soft);
  border: 1px solid var(--border);
  font-size: 13.5px;
  line-height: 1.65;
  color: var(--text-1);

  span {
    flex: 1;
  }
}

// 顶部引导 + 导出
.sp-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.tab-body {
  padding: 18px 0 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.seg {
  display: inline-flex;
  align-self: center;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.tile {
  padding: 16px 12px;
  border-radius: @r-md;
  background: var(--surface);
  border: 1px solid var(--border);
  text-align: center;

  span {
    display: block;
    font-size: 11.5px;
    color: var(--text-3);
    margin-bottom: 8px;
    letter-spacing: 0.03em;
  }
  b {
    font-size: 26px;
    font-weight: 800;
    color: var(--text-1);
    line-height: 1;
  }
  i {
    font-size: 11px;
    color: var(--text-3);
    font-style: normal;
    margin-left: 3px;
  }
  &.good b {
    color: var(--lime-ink);
  }
}

.chart-card {
  .eyebrow {
    margin-bottom: 14px;
  }
}

.chart-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-height: 190px;
  gap: 4px;
  color: var(--text-3);

  svg {
    color: var(--border-2);
    margin-bottom: 8px;
  }
  p {
    font-size: 13.5px;
    color: var(--text-2);
    font-weight: 500;
  }
  span {
    font-size: 12px;
    color: var(--text-3);
  }
}

.report-summary {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  background: var(--lime-soft);
  border-color: transparent;

  :deep(svg) {
    color: var(--lime-ink);
    flex-shrink: 0;
    margin-top: 2px;
  }
  p {
    margin: 0;
    font-size: 13.5px;
    line-height: 1.6;
    color: var(--lime-ink);
  }
}

// Vant tabs 分段感
:deep(.van-tabs__wrap) {
  margin-bottom: 4px;
}
:deep(.van-tab) {
  font-family: @font-body;
  font-size: 14.5px;
}

// 分段选择（日/周/月）
:deep(.van-radio-group) {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px;
  gap: 4px;
  display: inline-flex;
}
:deep(.van-radio) {
  padding: 6px 18px;
  border-radius: 999px;
  margin-right: 0;
}
:deep(.van-radio__icon) {
  display: none;
}
:deep(.van-radio__label) {
  color: var(--text-2);
  font-size: 13px;
}
:deep(.van-radio--checked) {
  background: var(--lime);
}
:deep(.van-radio--checked .van-radio__label) {
  color: var(--on-lime);
  font-weight: 600;
}

@media (max-width: 1023px) {
  .tiles {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
