<template>
  <header class="topbar">
    <div class="left">
      <button class="icon-btn tgl" :title="collapsed ? '展开侧栏' : '收起侧栏'" @click="emit('toggle')">
        <AppIcon :name="collapsed ? 'menu' : 'collapse'" :size="20" />
      </button>
      <div class="title-wrap">
        <span class="eyebrow">工作台 / {{ title }}</span>
        <h1 class="page-title">{{ title }}</h1>
      </div>
    </div>

    <div class="right">
      <span class="date-chip num">{{ dateStr }}</span>
      <button class="icon-btn" title="通知" @click="toast">
        <AppIcon name="bell" :size="19" />
        <span class="dot" />
      </button>
      <button class="icon-btn" :title="isDark ? '浅色模式' : '深色模式'" @click="toggleDark">
        <AppIcon :name="isDark ? 'sun' : 'moon'" :size="19" />
      </button>
      <div class="user" @click="goMine">
        <span class="avatar-box u-avatar">{{ initial }}</span>
        <span class="u-name ellipsis">{{ nickname }}</span>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/icons/AppIcon.vue'
import { titleMap } from '@/config/nav'
import { useAppStore } from '@/store/modules/app'
import { useUserStore } from '@/store/modules/user'
import { showToast } from 'vant'

const props = defineProps({
  collapsed: { type: Boolean, default: false }
})
const emit = defineEmits(['toggle'])

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()

const isDark = computed(() => appStore.isDark)
const nickname = computed(() => userStore.userInfo?.username || '瘦友')
const initial = computed(() => (nickname.value || '瘦')[0].toUpperCase())
const title = computed(() => titleMap[route.name] || '首页')

const WEEK = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
const dateStr = computed(() => {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}.${p(d.getMonth() + 1)}.${p(d.getDate())} ${WEEK[d.getDay()]}`
})

function toggleDark() {
  appStore.toggleDark()
}
function goMine() {
  router.push('/mine')
}
function toast() {
  showToast('暂无新通知')
}
</script>

<style lang="less" scoped>
@import '../../styles/variable.less';

.topbar {
  height: @topbar-h;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px 0 14px;
  background: var(--topbar-bg);
  backdrop-filter: saturate(140%) blur(14px);
  -webkit-backdrop-filter: saturate(140%) blur(14px);
  border-bottom: 1px solid var(--topbar-border);
  position: sticky;
  top: 0;
  z-index: 20;
}

.left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.tgl {
  width: 38px;
  height: 38px;
}

.title-wrap {
  display: flex;
  flex-direction: column;
  min-width: 0;

  .eyebrow {
    font-size: 10px;
    &::before {
      width: 12px;
    }
  }
  .page-title {
    font-family: @font-display;
    font-size: 18px;
    font-weight: 700;
    line-height: 1.15;
    color: var(--text-1);
    letter-spacing: 0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-btn {
  width: 38px;
  height: 38px;
  position: relative;

  .dot {
    position: absolute;
    top: 9px;
    right: 10px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--lime);
    box-shadow: 0 0 0 2px var(--topbar-bg);
  }
}

.date-chip {
  font-size: 12px;
  letter-spacing: 0.06em;
  color: var(--text-2);
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  white-space: nowrap;
}

.user {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-left: 4px;
  padding: 5px 12px 5px 5px;
  border-radius: 999px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background @dur-fast @ease-out, border-color @dur-fast @ease-out;

  &:hover {
    background: var(--hover);
    border-color: var(--border);
  }
  .u-avatar {
    width: 32px;
    height: 32px;
    font-size: 13px;
  }
  .u-name {
    font-size: 13.5px;
    font-weight: 600;
    color: var(--text-1);
    max-width: 120px;
  }
}

@media (max-width: 720px) {
  .date-chip,
  .user .u-name {
    display: none;
  }
}
</style>
