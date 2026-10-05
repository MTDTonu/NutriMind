<template>
  <!-- 全局氛围层 -->
  <div class="aura" />

  <!-- 离线状态条：真断网或有待同步记录时才出现 -->
  <OfflineBar v-if="isAuth" />

  <!-- 全屏认证页 -->
  <div v-if="isAuth" class="auth-stage">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>

  <!-- 桌面端：侧栏 + 顶栏 + 内容 -->
  <div v-else-if="!isMobile" class="app-shell" :class="{ collapsed }">
    <AppSidebar :collapsed="collapsed" />
    <div class="app-main-wrap">
      <AppTopbar :collapsed="collapsed" @toggle="toggleSidebar" />
      <main class="app-content" :class="{ 'app-content--flush': isFlush }">
        <div class="page-container">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>
  </div>

  <!-- 桌面端：⌘K 全局命令面板（移动端不挂载，快捷键在那里没有意义） -->
  <CommandPalette v-if="!isMobile" />

  <!-- 移动端：顶栏 + 内容 + 底部 Tab -->
  <div v-else class="app-shell-mobile">
    <header class="mtop">
      <!-- 左侧占位：仅用于让标题保持居中（导航已由底部 Tab 承担，不再需要抽屉入口） -->
      <span class="mtop-space" />
      <div class="m-title">
        <span class="m-logo" v-if="isHome"><AppIcon name="logo" :size="15" /></span>
        <span class="m-name">{{ pageTitle }}</span>
      </div>
      <button class="icon-btn" :title="isDark ? '浅色' : '深色'" @click="toggleDark">
        <AppIcon :name="isDark ? 'sun' : 'moon'" :size="19" />
      </button>
    </header>

    <main class="app-content-m" :class="{ 'app-content-m--flush': isFlush }">
      <div class="page-container">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <MobileTabBar />
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { showToast } from 'vant'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppTopbar from '@/components/layout/AppTopbar.vue'
import MobileTabBar from '@/components/layout/MobileTabBar.vue'
import CommandPalette from '@/components/layout/CommandPalette.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import OfflineBar from '@/components/OfflineBar.vue'
import service from '@/api/request'
import { startOfflineSync } from '@/utils/offline'
import { useAppStore } from '@/store/modules/app'
import { useUserStore } from '@/store/modules/user'
import { isLoggedIn } from '@/utils/auth'
import { isMobileRef, setupBreakpoint } from '@/utils/breakpoint'
import { BRAND, docTitle } from '@/config/brand'
import { startReminderScheduler, stopReminderScheduler, REMINDER_EVENT } from '@/utils/reminder'

const route = useRoute()
const appStore = useAppStore()
const userStore = useUserStore()

const isMobile = isMobileRef
const collapsed = computed(() => appStore.sidebarCollapsed)
const isDark = computed(() => appStore.isDark)
const isAuth = computed(() => route.meta && route.meta.hideTabBar === true)
const pageTitle = computed(() => (route.meta && route.meta.title) || BRAND.name)
const isHome = computed(() => route.name === 'home')
// 全幅页面（如 AI 助手）去掉内容容器的内边距与最大宽度
const isFlush = computed(() => route.name === 'ai')

function toggleSidebar() {
  appStore.toggleSidebar()
}
function toggleDark() {
  appStore.toggleDark()
}

// 浏览器标签跟着页面走：便于多标签区分与收藏夹识别
watch(
  () => route.meta && route.meta.title,
  (t) => {
    document.title = docTitle(t || BRAND.name)
  },
  { immediate: true }
)

// 提醒的应用内触达：系统通知被拒绝/不支持时，至少在页面里看得见
function onReminder(e) {
  const d = e.detail || {}
  showToast({
    message: d.title + ' · ' + (d.body || ''),
    position: 'top',
    duration: 4500
  })
}

onMounted(() => {
  setupBreakpoint()
  window.addEventListener(REMINDER_EVENT, onReminder)
  // 离线补写：进入应用即尝试同步积压记录，并监听网络恢复
  startOfflineSync(service)
  // 刷新后从服务端补齐用户信息：
  // 否则 store 里 userInfo 为空，任何局部 updateUserInfo（如 Mine 页同步 BMI）
  // 都会把「资料是否完善」误判为 false，进而把用户踢到完善资料页
  if (isLoggedIn()) {
    userStore.fetchUserInfo().catch(() => {})
    // 启动提醒调度器：未登录时没有提醒设置可拉，登录后才启
    startReminderScheduler()
  }
})

onUnmounted(() => {
  window.removeEventListener(REMINDER_EVENT, onReminder)
  stopReminderScheduler()
})
</script>

<style lang="less" scoped>
@import './styles/variable.less';

.auth-stage {
  min-height: 100vh;
}

// 移动端顶栏
.mtop {
  height: 54px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;

  // 左侧占位（原抽屉按钮位置），保证标题居中
  .mtop-space {
    width: 38px;
    height: 38px;
    flex-shrink: 0;
  }
  background: var(--topbar-bg);
  backdrop-filter: saturate(140%) blur(14px);
  -webkit-backdrop-filter: saturate(140%) blur(14px);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 20;

  .icon-btn {
    width: 40px;
    height: 40px;
  }
  .m-title {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    justify-content: center;

    .m-logo {
      width: 24px;
      height: 24px;
      border-radius: 8px;
      background: var(--lime);
      color: var(--on-lime);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .m-name {
      font-family: @font-display;
      font-size: 16px;
      font-weight: 700;
      color: var(--text-1);
      letter-spacing: 0.02em;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}
</style>
