<template>
  <aside class="rail" :class="{ collapsed, drawer, open: drawer && open }">
    <div class="rail-brand" @click="goHome">
      <span class="logo"><AppIcon name="logo" :size="20" /></span>
      <div class="brand-text">
        <span class="brand-name">{{ brand.name }}</span>
        <span class="brand-sub">{{ brand.nameEn }}</span>
      </div>
    </div>

    <div class="rail-label">菜单</div>

    <nav class="rail-nav">
      <router-link
        v-for="it in navItems"
        :key="it.name"
        :to="{ name: it.name }"
        class="nav-item"
        :class="{ active: route.name === it.name }"
        @click="onNav"
      >
        <span class="nav-ico"><AppIcon :name="it.icon" :size="19" /></span>
        <span class="nav-label">{{ it.label }}</span>
      </router-link>
    </nav>

    <!-- 底部用户卡：点击进入「我的」 -->
    <div class="rail-foot">
      <button class="user-mini" :class="{ active: route.name === 'mine' }" @click="goMine">
        <span class="avatar-box u-avatar">{{ initial }}</span>
        <div class="u-meta">
          <div class="u-name ellipsis">{{ nickname }}</div>
          <div class="u-sub">减重计划进行中</div>
        </div>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/icons/AppIcon.vue'
import { navItems } from '@/config/nav'
import { BRAND as brand } from '@/config/brand'
import { useUserStore } from '@/store/modules/user'

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  drawer: { type: Boolean, default: false },
  open: { type: Boolean, default: false }
})
const emit = defineEmits(['close'])

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const nickname = computed(() => userStore.userInfo?.username || '瘦友')
const initial = computed(() => (nickname.value || '瘦')[0].toUpperCase())

function onNav() {
  if (props.drawer) emit('close')
}
function goHome() {
  router.push('/home')
  if (props.drawer) emit('close')
}
function goMine() {
  router.push('/mine')
  if (props.drawer) emit('close')
}
</script>

<style lang="less" scoped>
@import '../../styles/variable.less';

.rail {
  width: @rail-w-open;
  flex-shrink: 0;
  background: var(--rail-bg);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  transition: width @dur @ease-out;
  position: relative;
  z-index: 30;
  overflow: hidden;

  &.collapsed {
    width: @rail-w;
  }

  // 顶部品牌
  .rail-brand {
    height: @topbar-h;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 18px;
    cursor: pointer;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;

    .logo {
      width: 34px;
      height: 34px;
      border-radius: @r-md;
      background: var(--lime);
      color: var(--on-lime);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: var(--glow-lime);
      flex-shrink: 0;
    }
    .brand-text {
      display: flex;
      flex-direction: column;
      line-height: 1.1;
    }
    .brand-name {
      font-family: @font-display;
      font-size: 17px;
      font-weight: 700;
      color: var(--text-1);
      letter-spacing: 0.02em;
    }
    .brand-sub {
      font-size: 10.5px;
      letter-spacing: 0.08em;
      color: var(--text-3);
      margin-top: 3px;
    }
  }

  .rail-label {
    font-size: 11px;
    letter-spacing: 0.04em;
    color: var(--text-3);
    padding: 16px 20px 6px;
    white-space: nowrap;
  }

  .rail-nav {
    flex: 1;
    padding: 4px 12px 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    overflow-y: auto;

    &::-webkit-scrollbar {
      width: 0;
    }
  }

  .nav-item {
    position: relative;
    display: flex;
    align-items: center;
    gap: 13px;
    height: 46px;
    padding: 0 12px;
    border-radius: @r-md;
    color: var(--text-2);
    white-space: nowrap;
    transition: background @dur-fast @ease-out, color @dur-fast @ease-out;
    overflow: hidden;

    .nav-ico {
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .nav-label {
      font-size: 14px;
      font-weight: 500;
    }

    &:hover {
      background: var(--hover);
      color: var(--text-1);
    }

    &.active {
      background: var(--lime-soft);
      color: var(--text-1);

      .nav-ico {
        color: var(--lime);
      }
      .nav-label {
        font-weight: 600;
      }
      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 3px;
        height: 20px;
        border-radius: 0 3px 3px 0;
        background: var(--lime);
      }
    }
  }

  // 底部用户卡
  .rail-foot {
    padding: 12px;
    border-top: 1px solid var(--rail-border, var(--border));
  }
  .user-mini {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 8px;
    border: none;
    background: transparent;
    border-radius: @r-md;
    cursor: pointer;
    text-align: left;
    transition: background @dur-fast @ease-out;
    white-space: nowrap;

    &:hover {
      background: var(--hover);
    }
    &.active {
      background: var(--lime-soft);
    }
    .u-avatar {
      width: 36px;
      height: 36px;
      font-size: 14px;
      flex-shrink: 0;
    }
    .u-meta {
      min-width: 0;
    }
    .u-name {
      font-size: 13.5px;
      font-weight: 600;
      color: var(--text-1);
      max-width: 130px;
    }
    .u-sub {
      font-size: 11px;
      color: var(--text-3);
    }
  }

  // 折叠态：只显示图标
  &.collapsed {
    .rail-brand {
      justify-content: center;
      padding: 0;
    }
    .brand-text,
    .rail-label,
    .nav-label {
      display: none;
    }
    .nav-item {
      justify-content: center;
      padding: 0;
      gap: 0;

      &.active::before {
        left: -12px; // 折叠后贴住侧栏左缘
      }
    }
    .rail-foot {
      padding: 12px 0;
    }
    .user-mini {
      justify-content: center;
      padding: 8px 0;
    }
    .u-meta {
      display: none;
    }
  }
}

// 移动端抽屉
.rail.drawer {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  height: 100%;
  width: @rail-w-open;
  // 给底部 Tab 栏留出空间，避免用户卡被盖住
  padding-bottom: calc(60px + env(safe-area-inset-bottom, 0px));
  transform: translateX(-100%);
  transition: transform @dur @ease-out;
  box-shadow: var(--shadow-3);

  &.open {
    transform: translateX(0);
  }
}
</style>
