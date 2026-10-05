<template>
  <div class="gauge">
    <svg viewBox="0 0 120 120" :width="size" :height="size" class="ring">
      <circle cx="60" cy="60" r="52" class="track" />
      <circle
        cx="60"
        cy="60"
        r="52"
        class="arc"
        :stroke="ringColor"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        transform="rotate(-90 60 60)"
      />
    </svg>
    <div class="center">
      <div class="value num">{{ Math.round(intake) }}</div>
      <div class="unit num">/ 目标 {{ recommend }} kcal</div>
      <div class="remain" :class="remainClass">{{ remainText }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  intake: { type: Number, default: 0 },
  recommend: { type: Number, default: 0 },
  size: { type: Number, default: 188 }
})

const radius = 52
const circumference = 2 * Math.PI * radius

const percent = computed(() => {
  if (!props.recommend) return 0
  return Math.min(props.intake / props.recommend, 1)
})

const dashOffset = computed(() => circumference * (1 - percent.value))

// 进度颜色：<80% 青柠，80%-100% 橙，>100% 红
const ringColor = computed(() => {
  const p = percent.value
  if (p < 0.8) return 'var(--lime)'
  if (p <= 1) return 'var(--orange)'
  return 'var(--red)'
})

const remain = computed(() => props.recommend - props.intake)
const remainText = computed(() => {
  if (remain.value >= 0) return '还可摄入 ' + Math.round(remain.value) + ' kcal'
  return '已超出 ' + Math.round(-remain.value) + ' kcal'
})
const remainClass = computed(() => (remain.value >= 0 ? 'ok' : 'over'))
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.gauge {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 0;
}

.ring {
  display: block;
  transform: rotate(0deg);
}
.track {
  fill: none;
  stroke: var(--surface-2);
  stroke-width: 9;
}
// 装饰性发光去掉：这一版层级靠留白与字号，不靠光晕
.arc {
  fill: none;
  stroke-width: 9;
  stroke-linecap: round;
  transition: stroke-dashoffset @dur-slow @ease-out, stroke @dur @ease-out;
}

.center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.value {
  font-size: 40px;
  font-weight: 800;
  line-height: 1;
  color: var(--text-1);
  letter-spacing: -0.02em;
}
.unit {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--text-3);
  margin-top: 6px;
}
.remain {
  margin-top: 8px;
  font-size: 12px;
  font-weight: 600;

  &.ok {
    color: var(--lime-ink);
  }
  &.over {
    color: var(--red);
  }
}
</style>
