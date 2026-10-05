<template>
  <van-popup
    v-model:show="visible"
    position="bottom"
    round
    :style="{ maxHeight: '86vh' }"
    @opened="focusInput"
  >
    <div class="fp">
      <header class="fp-head">
        <div class="fp-title">
          <h3>{{ title }}</h3>
          <span class="fp-sub">{{ subTitle }}</span>
        </div>
        <button class="fp-close" aria-label="关闭" @click="close">
          <AppIcon name="close" :size="16" />
        </button>
      </header>

      <!-- 搜索 -->
      <div class="fp-search">
        <AppIcon name="search" :size="16" />
        <input
          ref="inputRef"
          v-model="keyword"
          type="search"
          :placeholder="placeholder"
          @input="onInput"
        />
        <button v-if="keyword" class="fp-clear" @click="keyword = ''; load('')">清空</button>
      </div>

      <!-- 分类 chips -->
      <div class="fp-chips" v-if="categories.length">
        <button
          v-for="c in categories"
          :key="c.key"
          class="chip"
          :class="{ on: activeCat === c.key }"
          @click="pickCategory(c.key)"
        >
          {{ c.label }}
        </button>
      </div>

      <!-- 结果 -->
      <div class="fp-body">
        <div v-if="loading" class="fp-state">
          <van-loading size="18px" color="var(--lime-ink)" />
          <span>正在查找…</span>
        </div>

        <div v-else-if="!items.length" class="fp-state fp-empty">
          <span class="fe-ico"><AppIcon name="search" :size="20" /></span>
          <p class="fe-title">没找到「{{ keyword }}」</p>
          <p class="fe-sub">换更短的词试试，比如「鸡胸」「米饭」；也可以自己新建。</p>
          <button class="fe-btn" @click="startCustom">手动添加这条食物</button>
        </div>

        <ul v-else class="fp-list">
          <li v-for="f in items" :key="f.id">
            <button class="fp-item" @click="select(f)">
              <span class="fi-main">
                <span class="fi-name">
                  {{ f.name }}
                  <i v-if="f.source === 'user'" class="tag tag--est">自估</i>
                  <i v-else-if="f.source !== 'system'" class="tag">{{ f.source.toUpperCase() }}</i>
                </span>
                <span class="fi-meta">
                  {{ f.default_portion_label }} {{ f.default_portion_grams }}g
                  · 约 {{ Math.round((f.calorie * f.default_portion_grams) / 100) }} kcal
                </span>
              </span>
              <span class="fi-cal num">{{ f.calorie }}<i>/100g</i></span>
            </button>
            <button
              class="fp-star"
              :class="{ on: f.favorited }"
              :aria-label="f.favorited ? '取消收藏' : '收藏'"
              @click.stop="fav(f)"
            >
              <AppIcon name="star" :size="15" />
            </button>
          </li>
        </ul>
      </div>

      <!-- 第二步：份量 + 份数 -->
      <div class="fp-confirm" v-if="picked">
        <div class="pc-info">
          <div class="pc-name">{{ picked.name }}</div>
          <div class="pc-note">
            {{ picked.portion_label }} {{ baseGrams }}g × {{ quantity }}
            = <b>{{ totalGrams }}g</b> · <b class="kcal">{{ kcal }} kcal</b>
          </div>
          <div class="pc-nutri" v-if="pickedPortionCount">
            蛋白 {{ Math.round((picked.protein * totalGrams) / 100) }}g
            · 脂肪 {{ Math.round((picked.fat * totalGrams) / 100) }}g
            · 碳水 {{ Math.round((picked.carbohydrate * totalGrams) / 100) }}g
          </div>
        </div>

        <div class="pc-row" v-if="portions.length > 1">
          <button
            v-for="p in portions"
            :key="p.id"
            class="chip chip--sm"
            :class="{ on: portionId === p.id }"
            @click="choosePortion(p)"
          >
            {{ p.label }} {{ p.grams }}g
          </button>
        </div>

        <div class="pc-row pc-stepper">
          <span class="pc-label">份数</span>
          <button class="st-btn" @click="quantity = Math.max(0.5, +(quantity - 0.5).toFixed(1))">−</button>
          <span class="st-val num">{{ quantity }}</span>
          <button class="st-btn" @click="quantity = Math.min(10, +(quantity + 0.5).toFixed(1))">＋</button>
        </div>

        <div class="pc-actions">
          <button class="btn-ghost" @click="picked = null">返回</button>
          <button class="btn-primary" :disabled="saving" @click="confirm">
            {{ saving ? '正在记录…' : '记下这一笔' }}
          </button>
        </div>
      </div>
    </div>
  </van-popup>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import { searchFoods, foodCategories, foodDetail, toggleFavorite, quickAddFood } from '@/api/food'
import { today } from '@/utils/format'
import { showToast } from 'vant'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // 目标餐型：1 早 / 2 午 / 3 晚 / 4 加餐；不传时自动按当前时间推断
  mealType: { type: Number, default: 0 },
  recordDate: { type: String, default: '' },
  // 外部带入的初始关键词（⌘K 选中某食物后直接跳到这里选份量）
  initialKeyword: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue', 'added'])

const visible = ref(props.modelValue)
watch(() => props.modelValue, (v) => { visible.value = v })
watch(visible, (v) => emit('update:modelValue', v))

const inputRef = ref(null)
const keyword = ref('')
const categories = ref([])
const activeCat = ref('')
const items = ref([])
const loading = ref(false)
const portions = ref([])
const picked = ref(null)
const portionId = ref(null)
const quantity = ref(1)
const saving = ref(false)

let timer = null
function onInput() {
  clearTimeout(timer)
  timer = setTimeout(() => load(keyword.value), 220)
}

const title = computed(() => (mealLabel.value ? `记 ${mealLabel.value}` : '记一笔'))
const subTitle = computed(() => '先从食物库里挑，选好份量就能直接记')
const placeholder = computed(() => '搜食物，如「鸡胸」「米饭」「奶茶」')
const isDesktop = computed(() => typeof window !== 'undefined' && window.innerWidth >= 1024)

const resolvedMealType = computed(() => {
  if (props.mealType) return props.mealType
  const h = new Date().getHours()
  if (h < 10) return 1
  if (h < 15) return 2
  if (h < 21) return 3
  return 4
})
const MEAL_LABEL = { 1: '早餐', 2: '午餐', 3: '晚餐', 4: '加餐' }
const mealLabel = computed(() => MEAL_LABEL[resolvedMealType.value] || '')

const pickedPortionCount = computed(() => portions.value.length)
const baseGrams = computed(() => {
  const p = portions.value.find((x) => x.id === portionId.value)
  return p ? p.grams : 100
})
const totalGrams = computed(() => Math.round(baseGrams.value * quantity.value * 10) / 10)
const kcal = computed(() => Math.round((picked.value?.calorie || 0) * totalGrams.value / 100))

async function loadCats() {
  try {
    categories.value = (await foodCategories()).categories || []
  } catch (e) { /* 分类是可选装饰，失败不影响搜索 */ }
}

async function load(kw = '') {
  loading.value = true
  try {
    const res = await searchFoods({ keyword: kw, category: activeCat.value, limit: 30 })
    items.value = res.items || []
  } catch (e) {
    items.value = []
  } finally {
    loading.value = false
  }
}

function pickCategory(key) {
  activeCat.value = activeCat.value === key ? '' : key
  load(keyword.value)
}

function focusInput() {
  if (isDesktop.value) nextTick(() => inputRef.value?.focus())
}

async function select(f) {
  try {
    const d = await foodDetail(f.id)
    picked.value = d
    portions.value = d.portions || []
    const def = portions.value.find((p) => p.is_default) || portions.value[0]
    portionId.value = def?.id ?? null
    quantity.value = 1
  } catch (e) {
    // 详情取不到时退化：用列表数据 + 默认份量，保证录入不中断
    picked.value = { ...f, portions: [] }
    portions.value = []
    portionId.value = null
    quantity.value = 1
  }
}

function choosePortion(p) {
  portionId.value = p.id
}

async function fav(f) {
  try {
    const res = await toggleFavorite(f.id)
    f.favorited = res.favorited
    showToast({ type: 'success', message: res.favorited ? '已加入常用' : '已移出常用' })
  } catch (e) { /* 静默：收藏不是主链路 */ }
}

async function confirm() {
  if (!picked.value) return
  saving.value = true
  try {
    const rec = await quickAddFood({
      record_date: props.recordDate || today(),
      meal_type: resolvedMealType.value,
      food_id: picked.value.id,
      portion_id: portionId.value,
      quantity: quantity.value
    })
    showToast({ type: 'success', message: `已记入${mealLabel.value} · ${kcal.value} kcal` })
    emit('added', rec)
    picked.value = null
    keyword.value = ''
    activeCat.value = ''
    load('')
  } catch (e) {
    /* 错误提示由 request 拦截器统一弹出 */
  } finally {
    saving.value = false
  }
}

function startCustom() {
  showToast('自定义食物请到「记录」页新建（即将开放）')
}

function close() {
  visible.value = false
}

watch(visible, (v) => {
  if (v) {
    loadCats()
    // 从 ⌘K 带词进来时直接执行搜索，省掉用户再打一遍
    keyword.value = props.initialKeyword || ''
    load(keyword.value)
  }
})
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.fp {
  padding: 20px 20px calc(20px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 60vh;
}

.fp-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;

  h3 {
    font-size: 17px;
    margin: 0;
  }
  .fp-sub {
    display: block;
    margin-top: 3px;
    font-size: 12.5px;
    color: var(--text-3);
  }
  .fp-close {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: none;
    background: var(--surface-2);
    color: var(--text-2);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    &:hover {
      background: var(--hover);
      color: var(--text-1);
    }
  }
}

.fp-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  height: 44px;
  border-radius: 999px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-3);

  input {
    flex: 1;
    min-width: 0;
    border: none;
    background: transparent;
    outline: none;
    font-size: 14px;
    color: var(--text-1);
    font-family: @font-body;

    &::placeholder {
      color: var(--text-3);
    }
  }
  .fp-clear {
    border: none;
    background: transparent;
    color: var(--text-3);
    font-size: 12px;
    cursor: pointer;
  }
}

.fp-chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
  scrollbar-width: none;
  &::-webkit-scrollbar { display: none; }
}

.chip {
  flex-shrink: 0;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-2);
  border-radius: 999px;
  padding: 7px 13px;
  font-size: 12.5px;
  cursor: pointer;
  font-family: @font-body;
  transition: all @dur-fast @ease-out;

  &:hover {
    background: var(--hover);
    color: var(--text-1);
  }
  &.on {
    background: var(--lime-soft);
    border-color: transparent;
    color: var(--lime-ink);
    font-weight: 600;
  }
  &--sm {
    padding: 5px 11px;
    font-size: 12px;
  }
}

.fp-body {
  flex: 1;
  min-height: 200px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.fp-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 12px;
  color: var(--text-3);
  font-size: 13px;
}

.fp-empty {
  .fe-ico {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: var(--lime-soft);
    color: var(--lime-ink);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .fe-title {
    margin: 4px 0 0;
    font-size: 14.5px;
    font-weight: 600;
    color: var(--text-1);
  }
  .fe-sub {
    margin: 0 0 6px;
    font-size: 12.5px;
    max-width: 280px;
    text-align: center;
    line-height: 1.6;
  }
  .fe-btn {
    border: none;
    background: var(--lime);
    color: var(--on-lime);
    border-radius: @r-md;
    padding: 10px 22px;
    font-size: 13.5px;
    font-weight: 600;
    cursor: pointer;
  }
}

.fp-list {
  list-style: none;
  margin: 0;
  padding: 0;

  li {
    position: relative;
    display: flex;
    align-items: center;
  }
}

.fp-item {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 11px 40px 11px 10px;
  border: none;
  background: transparent;
  border-radius: @r-md;
  cursor: pointer;
  text-align: left;
  transition: background @dur-fast @ease-out;

  &:hover {
    background: var(--hover);
  }

  .fi-main {
    min-width: 0;
  }
  .fi-name {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14.5px;
    color: var(--text-1);
    font-weight: 500;
  }
  .fi-meta {
    display: block;
    margin-top: 2px;
    font-size: 12px;
    color: var(--text-3);
  }
  .fi-cal {
    font-size: 14px;
    font-weight: 700;
    color: var(--text-1);
    flex-shrink: 0;

    i {
      font-style: normal;
      font-size: 11px;
      font-weight: 400;
      color: var(--text-3);
    }
  }
}

.tag {
  font-style: normal;
  font-size: 10.5px;
  padding: 1px 5px;
  border-radius: 5px;
  background: var(--surface-2);
  color: var(--text-3);
  border: 1px solid var(--border);

  &--est {
    background: var(--clay-soft);
    color: var(--clay);
    border-color: transparent;
  }
}

.fp-star {
  position: absolute;
  right: 6px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--text-3);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background: var(--hover);
  }
  &.on {
    color: var(--lime-ink);
  }
}

.fp-confirm {
  border-top: 1px solid var(--border);
  padding-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;

  .pc-info {
    .pc-name {
      font-size: 15px;
      font-weight: 700;
      color: var(--text-1);
    }
    .pc-note {
      margin-top: 3px;
      font-size: 12.5px;
      color: var(--text-2);

      b {
        color: var(--text-1);
      }
      .kcal {
        color: var(--lime-ink);
      }
    }
    .pc-nutri {
      margin-top: 2px;
      font-size: 12px;
      color: var(--text-3);
    }
  }

  .pc-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .pc-stepper {
    .pc-label {
      font-size: 12.5px;
      color: var(--text-3);
      margin-right: 4px;
    }
    .st-btn {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      border: 1px solid var(--border);
      background: var(--surface-2);
      color: var(--text-1);
      cursor: pointer;
      font-size: 16px;
      line-height: 1;

      &:hover {
        background: var(--hover);
      }
    }
    .st-val {
      min-width: 34px;
      text-align: center;
      font-size: 15px;
      font-weight: 700;
    }
  }

  .pc-actions {
    display: flex;
    gap: 10px;

    .btn-ghost {
      flex: 0 0 84px;
      height: 44px;
      border-radius: @r-md;
      border: 1px solid var(--border);
      background: transparent;
      color: var(--text-2);
      font-size: 13.5px;
      cursor: pointer;

      &:hover {
        background: var(--hover);
      }
    }
    .btn-primary {
      flex: 1;
      height: 44px;
      border-radius: @r-md;
      border: none;
      background: var(--lime);
      color: var(--on-lime);
      font-size: 14.5px;
      font-weight: 700;
      cursor: pointer;
      transition: transform @dur-fast @ease-out, filter @dur-fast @ease-out;

      &:hover {
        filter: brightness(1.05);
      }
      &:active {
        transform: scale(0.985);
      }
      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    }
  }
}

@media (min-width: 1024px) {
  .fp {
    min-height: auto;
  }
  .fp-body {
    max-height: 46vh;
  }
}
</style>
