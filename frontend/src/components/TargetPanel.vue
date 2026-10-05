<template>
  <div class="tp">
    <!-- 加载骨架 -->
    <div v-if="loading && !plan" class="tp-skeleton">
      <span class="sk-line" />
      <span class="sk-line short" />
    </div>

    <template v-else-if="plan">
      <!-- 结论：一句话说清正在执行什么计划 -->
      <div class="tp-conclusion">
        <div class="tpc-main">
          <b class="num">{{ plan.target.target_calorie }}</b>
          <span class="tpc-unit">kcal / 天</span>
        </div>
        <p class="tpc-desc">
          每天留出
          <b>{{ plan.target.deficit }}</b> kcal 缺口，按此速度约
          <b>每周 {{ Math.abs(plan.target.weekly_loss_kg) }} kg</b>{{ etaText }}
        </p>
        <div class="tpc-source">
          <span class="dot" :class="{ on: plan.using_adaptive }" />
          {{
            plan.using_adaptive
              ? `目标基于你自己的代谢反推值 ${plan.base_tdee} kcal`
              : `目标基于公式估算 ${plan.base_tdee} kcal`
          }}
        </div>
      </div>

      <!-- 护栏告警：不要默默改用户的目标 -->
      <div v-if="plan.target.warnings && plan.target.warnings.length" class="tp-warn">
        <AppIcon name="info" :size="15" />
        <div>
          <p v-for="(w, i) in plan.target.warnings" :key="i">{{ w }}</p>
        </div>
      </div>

      <!-- 模式切换 -->
      <div class="tp-modes">
        <button
          class="tp-mode"
          :class="{ on: mode === 'rate' }"
          @click="pickMode('rate')"
        >
          <b>按速度</b>
          <span>我每周想减 X kg</span>
        </button>
        <button
          class="tp-mode"
          :class="{ on: mode === 'deficit' }"
          @click="pickMode('deficit')"
        >
          <b>按缺口</b>
          <span>我每天想少 X kcal</span>
        </button>
      </div>

      <!-- 参数：滑块驱动，实时预览目标热量 -->
      <div v-if="mode === 'rate'" class="tp-slider">
        <div class="tps-head">
          <span>每周减重</span>
          <b class="num">{{ rate.toFixed(1) }} kg</b>
        </div>
        <input
          v-model.number="rate"
          type="range"
          min="0.1"
          max="1"
          step="0.1"
          class="range"
        />
        <p class="tps-tip">健康减重区间 0.2–1.0 kg/周；超过 0.8 需要更高的蛋白质与力量训练配合。</p>
      </div>

      <div v-else class="tp-slider">
        <div class="tps-head">
          <span>每日热量缺口</span>
          <b class="num">{{ deficit }} kcal</b>
        </div>
        <input
          v-model.number="deficit"
          type="range"
          min="100"
          max="900"
          step="50"
          class="range"
        />
        <p class="tps-tip">缺口建议不超过 TDEE 的 25%，且摄入不低于 BMR，否则容易掉肌肉与代谢。</p>
      </div>

      <!-- 预估：让用户看到选择的后果 -->
      <div class="tp-preview">
        <span>调整后目标</span>
        <b class="num">{{ previewCalorie }} kcal</b>
        <i>较当前 {{ deltaText }}</i>
      </div>

      <button class="tp-save" :disabled="saving" @click="save">
        {{ saving ? '保存中…' : '保存目标' }}
      </button>

      <!-- 校准证据：让目标可信的关键 -->
      <div class="tp-evidence">
        <div class="tpe-head" @click="toggleEvidence">
          <span>上次校准依据</span>
          <AppIcon :name="evidenceOpen ? 'chevdown' : 'chevdown'" :size="15" :class="{ flip: evidenceOpen }" />
        </div>
        <div v-if="evidenceOpen" class="tpe-body">
          <template v-if="plan.fit && plan.fit.valid">
            <div class="tpe-row">
              <span>参与计算天数</span>
              <b class="num">{{ plan.fit.diet_days ?? '--' }} 天</b>
            </div>
            <div class="tpe-row">
              <span>实际平均摄入</span>
              <b class="num">{{ plan.fit.mean_intake ?? '--' }} kcal</b>
            </div>
            <div class="tpe-row">
              <span>体重变化斜率</span>
              <b class="num">{{ slopeText }}</b>
            </div>
            <div class="tpe-row">
              <span>反推真实 TDEE</span>
              <b class="num">{{ plan.fit.adaptive_tdee ?? '--' }} kcal</b>
            </div>
            <div class="tpe-row">
              <span>与公式估算差</span>
              <b class="num">{{ deltaTdeeText }}</b>
            </div>
            <div class="tpe-row">
              <span>结论可信度</span>
              <b class="num">{{ confidenceText }}</b>
            </div>
            <p class="tpe-note">
              公式：摄入 − 支出 = 体重变化 × 7700 kcal/kg。数据越连续，反推值越接近真实代谢。
            </p>
          </template>
          <p v-else class="tpe-note">
            {{ (plan.fit && plan.fit.reason) || '数据还不充分，暂未校准。' }}
          </p>
          <button class="tpe-calib" :disabled="calibrating" @click="calibrate">
            {{ calibrating ? '正在重新校准…' : '立即用最近数据校准一次' }}
          </button>
        </div>
      </div>
    </template>

    <div v-else class="tp-empty">
      暂未获取到目标方案，请稍后重试。
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { showToast } from 'vant'
import AppIcon from '@/components/icons/AppIcon.vue'
import { energyTarget, setEnergyTarget, calibrateEnergy } from '@/api/energy'

const emit = defineEmits(['saved', 'loaded'])

const plan = ref(null)
const loading = ref(false)
const saving = ref(false)
const calibrating = ref(false)
const evidenceOpen = ref(false)

const mode = ref('deficit')
const rate = ref(0.5)
const deficit = ref(400)

const etaText = computed(() => {
  const d = plan.value && plan.value.target && plan.value.target.estimated_days
  if (!d || d <= 0) return ''
  return `，距目标体重还需约 ${d} 天`
})

const slopeText = computed(() => {
  const s = plan.value && plan.value.fit && plan.value.fit.slope_kg_per_week
  if (s == null) return '--'
  return `${s > 0 ? '+' : ''}${s.toFixed(2)} kg/周`
})

// 反推值与公式估算的差：这是「你到底是不是标准代谢」的关键信号
const deltaTdeeText = computed(() => {
  const d = plan.value && plan.value.fit && plan.value.fit.delta
  if (d == null) return '--'
  return `${d > 0 ? '+' : ''}${d} kcal/天`
})

const confidenceText = computed(() => {
  const c = plan.value && plan.value.fit && plan.value.fit.confidence
  if (c == null) return '--'
  if (c >= 0.8) return `高（${Math.round(c * 100)}%）`
  if (c >= 0.5) return `中（${Math.round(c * 100)}%）`
  return `偏低（${Math.round(c * 100)}%）`
})

// 预览：前端直接按后端同一套换算规则给出预览值，避免用户点了才知道结果
const previewCalorie = computed(() => {
  if (!plan.value) return '--'
  const tdee = plan.value.base_tdee
  const d =
    mode.value === 'deficit' ? deficit.value : Math.round((rate.value * 7700) / 7)
  const intake = Math.round(Math.max(plan.value.floor_bmr || 0, tdee - d))
  return intake
})

const deltaText = computed(() => {
  if (!plan.value) return ''
  // 服务端 target_calorie 是浮点（如 1754.74），直接相减会出现 -199.7399999999999995
  const cur = Math.round(plan.value.target.target_calorie)
  const diff = Math.round(previewCalorie.value - cur)
  if (!diff) return '持平'
  return diff > 0 ? `+${diff} kcal` : `${diff} kcal`
})

async function load() {
  loading.value = true
  try {
    const data = await energyTarget({ days: 14 })
    plan.value = data
    if (data && data.target) emit('loaded', data.target)
    mode.value = (data.target && data.target.mode) || 'deficit'
    if (data.target && data.target.target_rate) rate.value = data.target.target_rate
    if (data.target && data.target.target_deficit) deficit.value = data.target.target_deficit
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}

function pickMode(m) {
  mode.value = m
}

function toggleEvidence() {
  evidenceOpen.value = !evidenceOpen.value
}

async function save() {
  saving.value = true
  try {
    const payload =
      mode.value === 'rate'
        ? { mode: 'rate', target_rate: Number(rate.value) }
        : { mode: 'deficit', target_deficit: Number(deficit.value) }
    const data = await setEnergyTarget(payload)
    // 服务端是权威：用返回值覆盖本地预览
    plan.value = { ...plan.value, using_adaptive: true }
    if (plan.value.target) {
      plan.value.target.mode = data.mode
      plan.value.target.target_calorie = data.target_calorie
      plan.value.target.deficit = data.deficit
      plan.value.target.weekly_loss_kg = data.weekly_loss_kg
      plan.value.target.estimated_days = data.estimated_days
      plan.value.target.warnings = data.warnings
    }
    showToast({ type: 'success', message: '目标已更新' })
    emit('saved', data)
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    saving.value = false
  }
}

async function calibrate() {
  calibrating.value = true
  try {
    await calibrateEnergy({ days: 14 })
    await load()
    showToast({ type: 'success', message: '已用最近数据完成校准' })
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    calibrating.value = false
  }
}

onMounted(load)

defineExpose({ load })
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.tp {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

// 结论区
.tp-conclusion {
  padding: 18px 18px 16px;
  border-radius: @r-lg;
  background: var(--lime-soft);
  border: 1px solid var(--border-2);

  .tpc-main {
    display: flex;
    align-items: baseline;
    gap: 6px;

    b {
      font-family: @font-display;
      font-size: 40px;
      line-height: 1.05;
      font-weight: 700;
      color: var(--text-1);
      letter-spacing: -0.01em;
    }
    span {
      font-size: 13px;
      color: var(--text-2);
    }
  }
  .tpc-desc {
    margin: 8px 0 0;
    font-size: 13.5px;
    line-height: 1.6;
    color: var(--text-1);

    b {
      color: var(--lime-ink);
      font-weight: 700;
    }
  }
  .tpc-source {
    margin-top: 10px;
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 12px;
    color: var(--text-2);

    .dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--text-3);

      &.on {
        background: var(--olive);
      }
    }
  }
}

// 告警
.tp-warn {
  display: flex;
  gap: 9px;
  padding: 12px 13px;
  border-radius: @r-md;
  background: var(--orange-soft);
  border: 1px solid var(--border);
  color: var(--text-1);
  font-size: 12.5px;
  line-height: 1.6;

  p {
    margin: 0;
  }
}

// 模式切换
.tp-modes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.tp-mode {
  padding: 12px 14px;
  border-radius: @r-md;
  border: 1px solid var(--border);
  background: var(--surface);
  cursor: pointer;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 3px;
  transition: border-color @dur-fast @ease-out, background @dur-fast @ease-out;

  b {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-1);
  }
  span {
    font-size: 11.5px;
    color: var(--text-3);
  }
  &:hover {
    background: var(--hover);
  }
  &.on {
    border-color: var(--lime-ink);
    background: var(--olive-soft);
  }
}

// 滑块
.tp-slider {
  .tps-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 10px;

    span {
      font-size: 13px;
      color: var(--text-2);
    }
    b {
      font-family: @font-display;
      font-size: 20px;
      font-weight: 700;
      color: var(--text-1);
    }
  }
  .tps-tip {
    margin: 8px 0 0;
    font-size: 11.5px;
    line-height: 1.6;
    color: var(--text-3);
  }
}

.range {
  width: 100%;
  height: 4px;
  border-radius: 999px;
  appearance: none;
  -webkit-appearance: none;
  background: var(--border-2);
  outline: none;

  &::-webkit-slider-thumb {
    appearance: none;
    -webkit-appearance: none;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--lime);
    border: 2px solid var(--surface);
    box-shadow: var(--shadow-1);
    cursor: pointer;
  }
  &:focus-visible::-webkit-slider-thumb {
    box-shadow: 0 0 0 3px var(--olive-soft);
  }
}

// 预览
.tp-preview {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 12px 14px;
  border-radius: @r-md;
  background: var(--surface-2);
  border: 1px solid var(--border);

  span {
    font-size: 12.5px;
    color: var(--text-2);
  }
  b {
    font-family: @font-display;
    font-size: 19px;
    font-weight: 700;
    color: var(--text-1);
  }
  i {
    font-style: normal;
    font-size: 11.5px;
    color: var(--text-3);
    margin-left: auto;
  }
}

.tp-save {
  height: 46px;
  border-radius: 999px;
  border: none;
  background: var(--lime);
  color: var(--on-lime);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--glow-lime);
  transition: transform @dur-fast @ease-out, opacity @dur-fast @ease-out;

  &:active {
    transform: scale(0.985);
  }
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

// 校准证据
.tp-evidence {
  border: 1px solid var(--border);
  border-radius: @r-md;
  overflow: hidden;

  .tpe-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 14px;
    background: var(--surface-2);
    font-size: 13px;
    font-weight: 600;
    color: var(--text-1);
    cursor: pointer;

    .flip {
      transform: rotate(180deg);
    }
  }
  .tpe-body {
    padding: 12px 14px 14px;
    display: flex;
    flex-direction: column;
    gap: 9px;
  }
  .tpe-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    font-size: 12.5px;
    color: var(--text-2);

    b {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-1);
    }
  }
  .tpe-note {
    margin: 2px 0 0;
    font-size: 11.5px;
    line-height: 1.65;
    color: var(--text-3);
  }
  .tpe-calib {
    margin-top: 4px;
    height: 38px;
    border-radius: 999px;
    border: 1px solid var(--lime-ink);
    background: transparent;
    color: var(--lime-ink);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;

    &:disabled {
      opacity: 0.6;
    }
  }
}

.tp-empty {
  padding: 26px 0;
  text-align: center;
  font-size: 13px;
  color: var(--text-3);
}

.tp-skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;

  .sk-line {
    height: 14px;
    border-radius: 999px;
    background: var(--hover);
    animation: sk 1.2s @ease infinite;

    &.short {
      width: 62%;
    }
  }
}

@keyframes sk {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.45;
  }
}
</style>
