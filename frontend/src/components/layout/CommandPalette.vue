<template>
  <van-popup v-model:show="open" position="bottom" round :style="{ maxHeight: '72vh' }">
    <div class="cp">
      <div class="cp-search">
        <AppIcon name="search" :size="17" />
        <input
          ref="inputRef"
          v-model="keyword"
          type="text"
          placeholder="搜索功能或直接记一笔食物…"
          @input="run"
          @keydown.down.prevent="move(1)"
          @keydown.up.prevent="move(-1)"
          @keydown.enter.prevent="enter"
        />
        <kbd class="cp-kbd">Esc</kbd>
      </div>

      <div class="cp-body">
        <!-- 食物结果：直接录入，不用先跳页面 -->
        <template v-if="foodItems.length">
          <div class="cp-group">食物 · 回车直接记入{{ currentMealLabel }}</div>
          <button
            v-for="(f, i) in foodItems"
            :key="'f' + f.id"
            class="cp-row"
            :class="{ on: cursor === i }"
            @mouseenter="cursor = i"
            @click="pick(f)"
          >
            <span class="cp-ico cp-ico--lime"><AppIcon name="diet" :size="15" /></span>
            <span class="cp-text">
              <span class="cp-name">{{ f.name }}</span>
              <span class="cp-meta">
                {{ f.default_portion_label }} {{ f.default_portion_grams }}g ·
                约 {{ Math.round((f.calorie * f.default_portion_grams) / 100) }} kcal
              </span>
            </span>
            <span class="cp-side">记录</span>
          </button>
        </template>

        <!-- 页面导航 -->
        <template v-if="pages.length">
          <div class="cp-group">前往</div>
          <button
            v-for="(p, i) in pages"
            :key="'p' + p.name"
            class="cp-row"
            :class="{ on: cursor === foodItems.length + i }"
            @mouseenter="cursor = foodItems.length + i"
            @click="go(p)"
          >
            <span class="cp-ico"><AppIcon :name="p.icon" :size="15" /></span>
            <span class="cp-text">
              <span class="cp-name">{{ p.title }}</span>
              <span class="cp-meta">{{ p.desc }}</span>
            </span>
            <span class="cp-side">打开</span>
          </button>
        </template>

        <div v-if="!foodItems.length && !pages.length" class="cp-empty">
          没有匹配结果，换个词试试
        </div>
      </div>

      <footer class="cp-foot">
        <span><kbd>↑</kbd><kbd>↓</kbd> 选择</span>
        <span><kbd>Enter</kbd> 确认</span>
        <span><kbd>Esc</kbd> 关闭</span>
      </footer>
    </div>
  </van-popup>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/icons/AppIcon.vue'
import { searchFoods } from '@/api/food'
import { today } from '@/utils/format'
import { showToast } from 'vant'
import bus from '@/utils/bus'

const router = useRouter()
const open = ref(false)
const keyword = ref('')
const foodItems = ref([])
const cursor = ref(0)
const inputRef = ref(null)

// 桌面端才启用：移动端已有底部 Tab，快捷键在这里没有意义
const isDesktop = () => typeof window !== 'undefined' && window.innerWidth >= 1024

const PAGES = [
  { name: 'home', title: '首页', desc: '今天还能吃多少', icon: 'home' },
  { name: 'diet', title: '饮食记录', desc: '按餐查看与补录', icon: 'diet' },
  { name: 'exercise', title: '运动', desc: '记录消耗', icon: 'exercise' },
  { name: 'stats', title: '数据', desc: '体重与热量趋势', icon: 'chart' },
  { name: 'ai', title: '问一问', desc: 'AI 减脂助手', icon: 'ai' },
  { name: 'mine', title: '我的', desc: '目标、资料与设置', icon: 'user' }
]

const pages = computed(() => {
  const kw = keyword.value.trim()
  if (!kw) return PAGES
  return PAGES.filter((p) => (p.title + p.desc).includes(kw))
})

// 按当前时间推断餐型：>=21 点算加餐，避免夜里填错到晚餐
const currentMealType = computed(() => {
  const h = new Date().getHours()
  if (h < 10) return 1
  if (h < 15) return 2
  if (h < 21) return 3
  return 4
})
const currentMealLabel = computed(() => ({ 1: '早餐', 2: '午餐', 3: '晚餐', 4: '加餐' }[currentMealType.value]))

let timer = null
function run() {
  cursor.value = 0
  clearTimeout(timer)
  timer = setTimeout(async () => {
    const kw = keyword.value.trim()
    if (!kw) {
      foodItems.value = []
      return
    }
    try {
      const res = await searchFoods({ keyword: kw, limit: 6 })
      foodItems.value = res.items || []
    } catch (e) {
      foodItems.value = []
    }
  }, 200)
}

const total = computed(() => foodItems.value.length + pages.value.length)
function move(step) {
  if (!total.value) return
  cursor.value = (cursor.value + step + total.value) % total.value
}

function enter() {
  const i = cursor.value
  if (i < foodItems.value.length) pick(foodItems.value[i])
  else go(pages.value[i - foodItems.value.length])
}

function pick(f) {
  open.value = false
  // 交给首页的食物选择器完成「选份量 → 记录」，这条路只有一份实现
  bus.emit('foodpicker:open', { keyword: f.name, mealType: currentMealType.value })
}

function go(p) {
  open.value = false
  keyword.value = ''
  foodItems.value = []
  router.push({ name: p.name })
}

function close() {
  open.value = false
}

function toggle() {
  if (open.value) {
    close()
    return
  }
  if (!isDesktop()) {
    showToast('⌘K 命令面板仅在电脑端可用')
    return
  }
  open.value = true
  nextTick(() => inputRef.value?.focus())
}

function onKey(e) {
  const k = (e.key || '').toLowerCase()
  if ((e.metaKey || e.ctrlKey) && k === 'k') {
    e.preventDefault()
    toggle()
  } else if (k === 'escape' && open.value) {
    close()
  } else if (k === '/' && !open.value && isDesktop()) {
    // 输入框里打 / 是正常输入，这里只响应页面空白处的 /
    const tag = (document.activeElement?.tagName || '').toLowerCase()
    if (tag !== 'input' && tag !== 'textarea') {
      e.preventDefault()
      toggle()
    }
  }
}

watch(open, (v) => {
  if (v) {
    nextTick(() => inputRef.value?.focus())
    run()
  }
})

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style lang="less" scoped>
@import '../../styles/variable.less';

.cp {
  padding: 16px 16px calc(14px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cp-search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  height: 48px;
  border-radius: @r-md;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-3);

  input {
    flex: 1;
    min-width: 0;
    border: none;
    outline: none;
    background: transparent;
    font-size: 15px;
    color: var(--text-1);
    font-family: @font-body;
  }
}

.cp-kbd,
kbd {
  font-family: @font-body;
  font-size: 11px;
  color: var(--text-3);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1px 6px;
}

.cp-body {
  max-height: 46vh;
  overflow-y: auto;
}

.cp-group {
  padding: 10px 6px 6px;
  font-size: 11.5px;
  color: var(--text-3);
  letter-spacing: 0.04em;
}

.cp-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 9px 10px;
  border: none;
  background: transparent;
  border-radius: @r-md;
  cursor: pointer;
  text-align: left;

  &.on {
    background: var(--hover);
  }

  .cp-ico {
    width: 30px;
    height: 30px;
    border-radius: 9px;
    background: var(--surface-2);
    color: var(--text-2);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .cp-ico--lime {
    background: var(--lime-soft);
    color: var(--lime-ink);
  }
  .cp-text {
    flex: 1;
    min-width: 0;
  }
  .cp-name {
    display: block;
    font-size: 14px;
    color: var(--text-1);
    font-weight: 500;
  }
  .cp-meta {
    display: block;
    font-size: 11.5px;
    color: var(--text-3);
  }
  .cp-side {
    font-size: 12px;
    color: var(--text-3);
    flex-shrink: 0;
  }
}

.cp-empty {
  padding: 34px 12px;
  text-align: center;
  font-size: 13px;
  color: var(--text-3);
}

.cp-foot {
  display: flex;
  gap: 14px;
  padding-top: 6px;
  border-top: 1px solid var(--border);
  font-size: 11.5px;
  color: var(--text-3);
}
</style>
