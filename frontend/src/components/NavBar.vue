<template>
  <header class="pnav" :class="{ 'pnav--standalone': standalone }">
    <button v-if="showBack" class="back icon-btn" @click="onClickLeft" aria-label="返回">
      <AppIcon name="collapse" :size="20" />
    </button>
    <span v-else class="back placeholder" />
    <h1 class="pnav-title">{{ title }}</h1>
    <div class="right">
      <slot name="right" />
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/icons/AppIcon.vue'

const props = defineProps({
  title: { type: String, default: '' },
  showBack: { type: Boolean, default: true }
})

const route = useRoute()
const router = useRouter()

// 独立页（登录/注册/完善资料等不套 shell 的页面）才需要自己的页头；
// 其余页面处于移动端 shell 中时，标题由 shell 顶栏统一承担。
const standalone = computed(() => !!(route.meta && route.meta.hideTabBar))

function onClickLeft() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.replace('/home')
  }
}
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.pnav {
  height: 54px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  background: var(--topbar-bg);
  backdrop-filter: saturate(140%) blur(14px);
  -webkit-backdrop-filter: saturate(140%) blur(14px);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 15;
}

.icon-btn {
  width: 38px;
  height: 38px;
}
.back.placeholder {
  width: 38px;
  height: 38px;
}

.pnav-title {
  flex: 1;
  text-align: center;
  font-family: @font-display;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-1);
  letter-spacing: 0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.right {
  min-width: 38px;
  display: flex;
  justify-content: flex-end;
}

// 桌面端：由 shell 顶栏承担标题，隐藏页头
@media (min-width: 1024px) {
  .pnav {
    display: none;
  }
}
// 移动端：处于 shell 内的页面隐藏页头（标题交给 shell 顶栏），
// 仅独立页（无 shell）保留。
@media (max-width: 1023px) {
  .pnav {
    display: none;
    &.pnav--standalone {
      display: flex;
    }
  }
}
</style>
