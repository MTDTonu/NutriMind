<template>
  <div class="page exercise">
    <NavBar title="运动与饮水" />

    <!-- 结论条：先回答「今天动了多少」，再给操作 -->
    <section class="card verdict">
      <div class="v-main">
        <h3 class="v-title">
          今天消耗
          <b class="num">{{ totalBurn }}</b>
          <span class="v-unit">kcal</span>
        </h3>
        <p class="v-hint">{{ todayHint }}</p>
        <div class="v-nums">
          <div><span>今日时长</span><b class="num">{{ todayMinutes }}</b><i>分钟</i></div>
          <div><span>今日次数</span><b class="num">{{ list.length }}</b><i>次</i></div>
          <div><span>本周累计</span><b class="num">{{ Math.round(weekly.total_calorie || 0) }}</b><i>kcal</i></div>
          <div><span>本周动过</span><b class="num">{{ weekly.active_days || 0 }}</b><i>/ {{ weekly.span_days || 7 }} 天</i></div>
        </div>
      </div>
      <div class="v-side">
        <span class="v-ring" :style="{ '--p': activePercent }">
          <b class="num">{{ activePercent }}%</b>
          <i>本周活跃度</i>
        </span>
      </div>
    </section>

    <div class="ex-layout" :class="{ 'with-side': !isMobile }">
      <!-- 左列：记一笔运动 -->
      <div class="col">
        <section class="card picker">
          <div class="card-head">
            <h3 class="c-title">记一笔运动</h3>
            <span class="c-sub">选项目 → 定时长 → 保存</span>
          </div>

          <div class="pk-search">
            <AppIcon name="search" :size="15" class="s-ico" />
            <input v-model="kw" type="search" placeholder="搜索运动，如 跑步 / 瑜伽" />
          </div>

          <div class="pk-cats">
            <button
              v-for="c in cats"
              :key="c.key"
              class="cat"
              :class="{ on: cat === c.key }"
              @click="cat = c.key"
            >
              {{ c.label }}
            </button>
          </div>

          <div class="pk-grid">
            <button
              v-for="it in filtered"
              :key="it.key"
              class="pk-item"
              :class="{ on: form.exercise_type === it.key }"
              @click="pick(it)"
            >
              <span class="pk-ico"><AppIcon :name="it.icon" :size="18" /></span>
              <span class="pk-name">{{ it.label }}</span>
              <span class="pk-met num">MET {{ it.met }}</span>
            </button>
          </div>
          <p v-if="!filtered.length" class="pk-empty">没找到「{{ kw }}」，换个词或选上面的分类</p>

          <!-- 时长与预估：选中后立即显示，避免弹窗往返 -->
          <div v-if="form.exercise_type" class="pk-form">
            <div class="pk-picked">
              <span class="pk-ico"><AppIcon :name="picked.icon" :size="18" /></span>
              <b>{{ picked.label }}</b>
              <span class="pk-met">MET {{ picked.met }}</span>
            </div>

            <div class="pk-dur">
              <span class="d-label">时长</span>
              <div class="d-presets">
                <button
                  v-for="d in DURATION_PRESETS"
                  :key="d"
                  class="dp"
                  :class="{ on: Number(form.duration) === d }"
                  @click="form.duration = String(d)"
                >
                  {{ d }}′
                </button>
                <input
                  v-model="form.duration"
                  type="number"
                  min="1"
                  max="600"
                  class="d-input num"
                  placeholder="自定义"
                />
              </div>
            </div>

            <div class="pk-est">
              <div class="est-line">
                <span>预计消耗</span>
                <b class="num" :class="{ muted: !estBurn }">{{ estBurn || '—' }}</b>
                <i>kcal</i>
              </div>
              <p v-if="!weight" class="est-warn">
                还没填真实体重，无法估算消耗。去「我的 · 个人资料」补上就能算。
              </p>
              <p v-else class="est-note">
                按 {{ weight }} kg × {{ form.duration || 0 }} 分钟估算；MET 是群体统计值，个体会有 ±20% 波动。
              </p>
            </div>

            <button class="pk-save" :disabled="!canSave || saving" @click="onAdd">
              {{ saving ? '保存中…' : '保存这条运动' }}
            </button>
          </div>
        </section>

        <!-- 今日记录 -->
        <section class="card today">
          <div class="card-head">
            <h3 class="c-title">今日运动</h3>
            <span class="c-sub">{{ list.length ? list.length + ' 条' : '还没有记录' }}</span>
          </div>

          <p v-if="!list.length" class="t-empty">
            动过就记一笔：它和吃进去的热量一起决定体重曲线。
          </p>

          <div v-for="item in list" :key="item.id" class="t-item">
            <span class="t-ico"><AppIcon :name="exerciseIcon(item.exercise_type)" :size="17" /></span>
            <div class="t-info">
              <div class="t-name">{{ exerciseLabel(item.exercise_type) }}</div>
              <div class="t-meta num">{{ item.duration }} 分钟 · {{ Math.round(item.calorie_burn) }} kcal</div>
            </div>
            <button class="t-del" @click="onDelete(item)" aria-label="删除">
              <AppIcon name="trash" :size="16" />
            </button>
          </div>
        </section>
      </div>

      <!-- 右列：本周小结 + 饮水 -->
      <div class="col">
        <section class="card week">
          <div class="card-head">
            <h3 class="c-title">本周小结</h3>
            <span class="c-sub">近 {{ weekly.span_days || 7 }} 天</span>
          </div>

          <div class="w-bars">
            <div v-for="d in weekly.days || []" :key="d.date" class="wb">
              <div class="wb-track">
                <span class="wb-fill" :style="{ height: barHeight(d.calorie) }" :title="d.calorie + ' kcal'" />
              </div>
              <span class="wb-day">{{ dayLabel(d.date) }}</span>
            </div>
          </div>

          <div class="w-sum">
            <div><span>总消耗</span><b class="num">{{ Math.round(weekly.total_calorie || 0) }}</b></div>
            <div><span>总时长</span><b class="num">{{ weekly.total_minutes || 0 }}</b><i>分钟</i></div>
            <div><span>日均</span><b class="num">{{ dailyAvg }}</b><i>kcal</i></div>
          </div>

          <p class="w-tip">{{ weekTip }}</p>
        </section>

        <section class="card water">
          <div class="card-head">
            <h3 class="c-title">今日饮水</h3>
            <span class="c-sub">目标 {{ water.target_amount }} ml</span>
          </div>

          <div class="w-amount">
            <b class="num">{{ water.total_amount }}</b>
            <span>/ {{ water.target_amount }} ml</span>
          </div>
          <van-progress :percentage="waterPercent" color="var(--sky)" :show-pivot="false" class="w-bar" />

          <div class="w-quick">
            <button class="wq" @click="submitWater(100)">+100</button>
            <button class="wq" @click="submitWater(300)">+300</button>
            <button class="wq" @click="submitWater(500)">+500</button>
          </div>
          <p class="w-note">{{ waterNote }}</p>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import { addExercise, listExercise, deleteExercise, weeklyExercise } from '@/api/exercise'
import { addWater, todayWater } from '@/api/water'
import { showToast, showConfirmDialog } from 'vant'
import { today } from '@/utils/format'
import { isMobileRef } from '@/utils/breakpoint'
import {
  EXERCISE_CATEGORIES,
  EXERCISE_LIBRARY,
  DURATION_PRESETS,
  exerciseLabel,
  exerciseIcon,
  findExercise,
  calcExerciseBurn
} from '@/config/exercises'
import { useUserStore } from '@/store/modules/user'

const userStore = useUserStore()
const isMobile = isMobileRef
// 体重必须取真实值：没有就按 0 处理，绝不用 60kg 之类的假设值参与热量计算
const weight = computed(() => Number(userStore.userInfo?.current_weight) || 0)

const cats = [{ key: 'all', label: '全部' }, ...EXERCISE_CATEGORIES.filter((c) => c.key !== 'legacy')]
const cat = ref('all')
const kw = ref('')

const filtered = computed(() => {
  const k = kw.value.trim().toLowerCase()
  return EXERCISE_LIBRARY.filter((x) => {
    if (cat.value !== 'all' && x.cat !== cat.value) return false
    if (!k) return true
    return x.label.toLowerCase().includes(k) || x.key.includes(k)
  })
})

const form = reactive({ exercise_type: 'walking', duration: '30' })
const picked = computed(() => findExercise(form.exercise_type) || EXERCISE_LIBRARY[0])

function pick(it) {
  form.exercise_type = it.key
}

const estBurn = computed(() => calcExerciseBurn(form.exercise_type, Number(form.duration), weight.value))
const canSave = computed(() => !!weight.value && Number(form.duration) > 0 && !!form.exercise_type)

const list = ref([])
const saving = ref(false)
const weekly = ref({ days: [], total_calorie: 0, total_minutes: 0, active_days: 0, span_days: 7 })

const totalBurn = computed(() => Math.round(list.value.reduce((s, x) => s + Number(x.calorie_burn || 0), 0)))
const todayMinutes = computed(() => list.value.reduce((s, x) => s + Number(x.duration || 0), 0))
const activePercent = computed(() => {
  const span = weekly.value.span_days || 7
  return Math.round(((weekly.value.active_days || 0) / span) * 100)
})
const dailyAvg = computed(() => {
  const span = weekly.value.span_days || 7
  return Math.round((weekly.value.total_calorie || 0) / span)
})

const todayHint = computed(() => {
  if (!list.value.length) {
    const sample = calcExerciseBurn('walking', 30, weight.value)
    return sample
      ? `还没记录。以你现在的体重，快走 30 分钟约消耗 ${sample} kcal。`
      : '还没记录。先去「我的 · 个人资料」填上体重，才能估算消耗。'
  }
  const walk = calcExerciseBurn('walking', 1, weight.value)
  if (!walk) return `已记 ${list.value.length} 次，共 ${todayMinutes.value} 分钟。`
  const equiv = Math.round(totalBurn.value / walk)
  return `已记 ${list.value.length} 次 · 共 ${todayMinutes.value} 分钟，约等于快走 ${equiv} 分钟。`
})

const weekTip = computed(() => {
  const d = weekly.value.active_days || 0
  if (!d) return '这一周还没有运动记录。不用追求强度，先让身体动起来两天。'
  if (d <= 2) return `这周动了 ${d} 天。再加 1 天，减脂的复利就开始明显了。`
  if (d <= 4) return `这周动了 ${d} 天，节奏不错。保持住，别一次性补太多。`
  return `这周动了 ${d} 天，很稳。记得留一天给恢复，恢复也是训练的一部分。`
})

const water = reactive({ total_amount: 0, target_amount: 2000, date: '' })
const waterPercent = computed(() =>
  water.target_amount ? Math.min(Math.round((water.total_amount / water.target_amount) * 100), 100) : 0
)
const waterNote = computed(() => {
  const p = waterPercent.value
  if (p >= 100) return '今日饮水已达标。'
  const left = Math.max((water.target_amount || 0) - (water.total_amount || 0), 0)
  return `还差 ${left} ml，大约 ${Math.max(Math.ceil(left / 200), 1)} 杯。`
})

function barHeight(cal) {
  const max = Math.max(...(weekly.value.days || []).map((d) => d.calorie || 0), 1)
  const pct = max ? Math.round(((cal || 0) / max) * 100) : 0
  return Math.max(pct, cal > 0 ? 6 : 0) + '%'
}

function dayLabel(d) {
  const dt = new Date(d + 'T00:00:00')
  return ['日', '一', '二', '三', '四', '五', '六'][dt.getDay()]
}

async function loadList() {
  try {
    const res = await listExercise({ date: today() })
    list.value = res.records || []
  } catch (e) {
    list.value = []
  }
}

async function loadWeekly() {
  try {
    weekly.value = await weeklyExercise({ days: 7 })
  } catch (e) {
    weekly.value = { days: [], total_calorie: 0, total_minutes: 0, active_days: 0, span_days: 7 }
  }
}

async function onAdd() {
  if (!weight.value) {
    showToast({ type: 'fail', message: '请先在「我的 · 个人资料」填写真实体重' })
    return
  }
  if (!Number(form.duration)) {
    showToast({ type: 'fail', message: '请填写运动时长' })
    return
  }
  saving.value = true
  try {
    await addExercise({
      record_date: today(),
      exercise_type: form.exercise_type,
      duration: Number(form.duration),
      calorie_burn: estBurn.value
    })
    showToast({ type: 'success', message: '已记录 ' + estBurn.value + ' kcal' })
    loadList()
    loadWeekly()
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    saving.value = false
  }
}

async function onDelete(item) {
  try {
    await showConfirmDialog({ title: '提示', message: '确定删除这条运动记录？' })
    await deleteExercise(item.id)
    showToast({ type: 'success', message: '已删除' })
    loadList()
    loadWeekly()
  } catch (e) {
    /* 用户取消 */
  }
}

async function loadWater() {
  try {
    const res = await todayWater({ date: today() })
    Object.assign(water, res)
  } catch (e) {
    /* 拦截器已提示 */
  }
}

async function submitWater(amount) {
  try {
    const res = await addWater({ record_date: today(), amount })
    water.total_amount = res.total_amount
    water.target_amount = res.target_amount
    showToast({ type: 'success', message: '已添加 ' + amount + 'ml' })
  } catch (e) {
    /* 拦截器已提示 */
  }
}

onMounted(() => {
  loadList()
  loadWeekly()
  loadWater()
})
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.page.exercise {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;

  .c-title {
    margin: 0;
    font-size: 15.5px;
    font-weight: 700;
    color: var(--text-1);
  }
  .c-sub {
    font-size: 11.5px;
    color: var(--text-3);
  }
}

// ---------- 结论条 ----------
.verdict {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 20px 20px;

  .v-title {
    margin: 0;
    font-size: 15px;
    font-weight: 500;
    color: var(--text-2);

    b {
      font-size: 34px;
      font-weight: 800;
      color: var(--lime-ink);
      margin: 0 6px;
      font-variant-numeric: tabular-nums;
    }
    .v-unit {
      font-size: 13px;
      color: var(--text-3);
    }
  }
  .v-hint {
    margin: 8px 0 0;
    font-size: 13px;
    line-height: 1.6;
    color: var(--text-2);
  }
  .v-nums {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 22px;
    margin-top: 14px;

    > div {
      display: flex;
      align-items: baseline;
      gap: 5px;
      font-size: 12px;
      color: var(--text-3);

      b {
        font-size: 16px;
        font-weight: 700;
        color: var(--text-1);
        font-variant-numeric: tabular-nums;
      }
      i {
        font-style: normal;
        font-size: 11px;
      }
    }
  }
  .v-ring {
    --p: 0;
    position: relative;
    flex-shrink: 0;
    width: 96px;
    height: 96px;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    // 外圈是进度环，内圈用同底色挖空成环（比 mask 兼容性好）
    background: conic-gradient(var(--lime) calc(var(--p) * 1%), var(--surface-2) 0);

    &::after {
      content: '';
      position: absolute;
      inset: 9px;
      border-radius: 50%;
      background: var(--surface);
    }

    b,
    i {
      position: relative;
      z-index: 1;
    }

    b {
      font-size: 19px;
      font-weight: 800;
      color: var(--text-1);
      font-variant-numeric: tabular-nums;
    }
    i {
      font-style: normal;
      font-size: 10.5px;
      color: var(--text-3);
    }
  }
}

// ---------- 布局 ----------
.ex-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;

  &.with-side {
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
    gap: 16px;
    align-items: start;
  }
  .col {
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-width: 0;
  }
}

// ---------- 运动库 ----------
.pk-search {
  position: relative;
  margin-bottom: 10px;

  .s-ico {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-3);
  }
  input {
    width: 100%;
    height: 40px;
    padding: 0 12px 0 34px;
    border-radius: @r-md;
    border: 1px solid var(--border);
    background: var(--surface-2);
    color: var(--text-1);
    font-size: 14px;

    &:focus {
      outline: none;
      border-color: var(--lime-ink);
      background: var(--surface);
    }
  }
}

.pk-cats {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-bottom: 12px;

  .cat {
    padding: 6px 13px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-2);
    font-size: 12.5px;
    cursor: pointer;
    transition: all @dur-fast @ease-out;

    &:hover {
      border-color: var(--lime-ink);
      color: var(--lime-ink);
    }
    &.on {
      background: var(--lime);
      border-color: var(--lime);
      color: var(--on-lime);
      font-weight: 600;
    }
  }
}

.pk-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
  gap: 8px;

  .pk-item {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 3px;
    padding: 10px 11px;
    border-radius: @r-md;
    border: 1px solid var(--border);
    background: var(--surface-2);
    cursor: pointer;
    text-align: left;
    transition: all @dur-fast @ease-out;

    .pk-ico {
      width: 28px;
      height: 28px;
      border-radius: 9px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--surface);
      color: var(--text-2);
      margin-bottom: 2px;
    }
    .pk-name {
      font-size: 13.5px;
      font-weight: 600;
      color: var(--text-1);
    }
    .pk-met {
      font-size: 11px;
      color: var(--text-3);
    }

    &:hover {
      transform: translateY(-1px);
      border-color: var(--lime-ink);
    }
    &.on {
      border-color: var(--lime-ink);
      background: var(--lime-soft);

      .pk-ico {
        background: var(--lime);
        color: var(--on-lime);
      }
    }
  }
}

.pk-empty {
  margin: 10px 0 0;
  font-size: 12.5px;
  color: var(--text-3);
}

.pk-form {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 12px;

  .pk-picked {
    display: flex;
    align-items: center;
    gap: 9px;

    .pk-ico {
      width: 30px;
      height: 30px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--lime);
      color: var(--on-lime);
    }
    b {
      font-size: 15px;
      color: var(--text-1);
    }
    .pk-met {
      font-size: 11.5px;
      color: var(--text-3);
    }
  }

  .pk-dur {
    .d-label {
      display: block;
      font-size: 12.5px;
      color: var(--text-2);
      margin-bottom: 8px;
    }
    .d-presets {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;

      .dp {
        min-width: 48px;
        height: 34px;
        padding: 0 11px;
        border-radius: @r-sm;
        border: 1px solid var(--border);
        background: var(--surface-2);
        color: var(--text-2);
        font-size: 13px;
        font-variant-numeric: tabular-nums;
        cursor: pointer;
        transition: all @dur-fast @ease-out;

        &:hover {
          border-color: var(--lime-ink);
          color: var(--lime-ink);
        }
        &.on {
          background: var(--lime);
          border-color: var(--lime);
          color: var(--on-lime);
          font-weight: 600;
        }
      }
      .d-input {
        width: 84px;
        height: 34px;
        padding: 0 10px;
        border-radius: @r-sm;
        border: 1px solid var(--border);
        background: var(--surface);
        color: var(--text-1);
        font-size: 13px;

        &:focus {
          outline: none;
          border-color: var(--lime-ink);
        }
      }
    }
  }

  .pk-est {
    padding: 12px 14px;
    border-radius: @r-md;
    background: var(--surface-2);

    .est-line {
      display: flex;
      align-items: baseline;
      gap: 6px;
      font-size: 13px;
      color: var(--text-2);

      b {
        font-size: 22px;
        font-weight: 800;
        color: var(--lime-ink);
        font-variant-numeric: tabular-nums;

        &.muted {
          color: var(--text-3);
        }
      }
      i {
        font-style: normal;
        font-size: 11.5px;
        color: var(--text-3);
      }
    }
    .est-warn,
    .est-note {
      margin: 7px 0 0;
      font-size: 11.5px;
      line-height: 1.6;
    }
    .est-warn {
      color: var(--clay);
    }
    .est-note {
      color: var(--text-3);
    }
  }

  .pk-save {
    height: 46px;
    border-radius: 999px;
    border: none;
    background: var(--lime);
    color: var(--on-lime);
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: var(--glow-lime);

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      box-shadow: none;
    }
  }
}

// ---------- 今日记录 ----------
.t-empty {
  margin: 0;
  font-size: 13px;
  color: var(--text-3);
  padding: 12px 0;
}

.t-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);

  &:last-child {
    border-bottom: none;
  }
  .t-ico {
    width: 36px;
    height: 36px;
    border-radius: @r-md;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--lime-soft);
    color: var(--lime-ink);
    flex-shrink: 0;
  }
  .t-info {
    flex: 1;
    min-width: 0;

    .t-name {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-1);
    }
    .t-meta {
      font-size: 12px;
      color: var(--text-3);
      margin-top: 2px;
    }
  }
  .t-del {
    width: 32px;
    height: 32px;
    border: none;
    border-radius: @r-sm;
    background: transparent;
    color: var(--text-3);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;

    &:hover {
      color: var(--red);
      background: var(--red-soft);
    }
  }
}

// ---------- 本周小结 ----------
.w-bars {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 108px;
  padding-top: 6px;

  .wb {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    height: 100%;

    .wb-track {
      flex: 1;
      width: 100%;
      display: flex;
      align-items: flex-end;
      justify-content: center;

      .wb-fill {
        width: 100%;
        max-width: 26px;
        border-radius: 6px 6px 3px 3px;
        background: var(--olive);
        transition: height @dur @ease-out;
      }
    }
    .wb-day {
      font-size: 11px;
      color: var(--text-3);
    }
  }
}

.w-sum {
  display: flex;
  gap: 8px 20px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
  flex-wrap: wrap;

  > div {
    display: flex;
    align-items: baseline;
    gap: 5px;
    font-size: 12px;
    color: var(--text-3);

    b {
      font-size: 16px;
      font-weight: 700;
      color: var(--text-1);
      font-variant-numeric: tabular-nums;
    }
    i {
      font-style: normal;
      font-size: 11px;
    }
  }
}

.w-tip {
  margin: 12px 0 0;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text-2);
}

// ---------- 饮水 ----------
.water {
  .w-amount {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 12px;

    b {
      font-size: 34px;
      font-weight: 800;
      line-height: 1;
      color: var(--sky);
      font-variant-numeric: tabular-nums;
    }
    span {
      font-size: 13px;
      color: var(--text-3);
    }
  }
  .w-bar {
    margin-bottom: 14px;
  }
  .w-quick {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 9px;

    .wq {
      padding: 11px 0;
      border-radius: @r-md;
      border: 1px solid var(--border);
      background: var(--sky-soft);
      color: var(--sky);
      font-weight: 600;
      font-size: 13px;
      font-variant-numeric: tabular-nums;
      cursor: pointer;
      transition: transform @dur-fast @ease-out, border-color @dur-fast @ease-out;

      &:hover {
        transform: translateY(-1px);
        border-color: var(--sky);
      }
    }
  }
  .w-note {
    margin: 11px 0 0;
    font-size: 12px;
    color: var(--text-3);
  }
}

@media (max-width: 1023px) {
  .verdict {
    flex-direction: column;
    align-items: flex-start;

    .v-ring {
      display: none;
    }
  }
}

@media (min-width: 1024px) {
  // 桌面端把运动库限高：30+ 项全铺开会把「时长/预估/保存」推到首屏之外，
  // 用户第一眼看到的是清单而不是操作。滚动放在库内部，操作区始终可见。
  .pk-grid {
    max-height: 300px;
    overflow-y: auto;
    padding-right: 4px;

    &::-webkit-scrollbar {
      width: 6px;
    }
    &::-webkit-scrollbar-thumb {
      border-radius: 999px;
      background: var(--border-2);
    }
  }
}
</style>
