<template>
  <div ref="chartRef" class="chart-line" :style="{ height: height }"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '300px' },
  // 开启后点击图元会派发 pick 事件（携带类目名，如日期），供外部做交叉筛选
  pickable: { type: Boolean, default: false }
})

const emit = defineEmits(['pick'])

const chartRef = ref(null)
let chart = null
let resizeObserver = null

function render() {
  if (!chart) return
  chart.setOption(props.option, true)
  // setOption(..., true) 会清掉实例上的事件吗？不会（事件绑在实例上），
  // 但重渲染会重建 series，这里统一在渲染后重新绑定，避免丢失。
  if (props.pickable) {
    chart.off('click')
    chart.on('click', (p) => {
      if (p && p.name != null) emit('pick', String(p.name))
    })
  }
}

function resize() {
  if (chart) chart.resize()
}

// 仅在容器具备有效尺寸时初始化。
// 图表若位于「未激活的 tab 面板 / 隐藏祖先」中，挂载时 clientWidth/Height 为 0，
// 此时 echarts.init 会打印 "Can't get DOM width or height" 且不渲染。
function tryInit() {
  const el = chartRef.value
  if (!el || chart) return
  if (el.clientWidth === 0 || el.clientHeight === 0) return
  chart = echarts.init(el)
  render()
  if (props.pickable) {
    // 光标提示可点
    el.style.cursor = 'pointer'
  }
}

onMounted(async () => {
  await nextTick()
  tryInit()
  // 尺寸从 0 变为有效（tab 切换 / 面板展开）时补做初始化，之后仅 resize
  resizeObserver = new ResizeObserver(() => {
    if (!chart) tryInit()
    else resize()
  })
  resizeObserver.observe(chartRef.value)
  window.addEventListener('resize', resize)
})

watch(
  () => props.option,
  () => render(),
  { deep: true }
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (resizeObserver) resizeObserver.disconnect()
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style lang="less" scoped>
.chart-line {
  width: 100%;
}
</style>
